"""Budget service layer."""
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from datetime import datetime, date
from sqlalchemy import func, extract, text
from flask import current_app
from app.core.extensions import db
from app.core.money import Money, SUPPORTED_CURRENCIES, get_user_currency
from app.core.time import YearMonth
from app.core.caching import cached_per_user_month, CacheManager
from .models import Category, Expense, Income, CategoryRule, ExchangeRate, IncomeSource


class BudgetService:
    """Budget business logic service."""
    
    @staticmethod
    def get_user_categories(user_id: int) -> List[Category]:
        """Get all categories for user."""
        return Category.query.filter_by(user_id=user_id).order_by(Category.name).all()
    
    @staticmethod
    def get_user_income_sources(user_id: int) -> List[IncomeSource]:
        """Get all income sources for user."""
        return IncomeSource.query.filter_by(user_id=user_id).order_by(IncomeSource.name).all()
    
    @staticmethod
    def create_category(user_id: int, name: str, limit_type: str, value: Decimal) -> Category:
        """Create new category."""
        category = Category(
            user_id=user_id,
            name=name,
            limit_type=limit_type,
            value=value
        )
        db.session.add(category)
        db.session.commit()
        
        # Invalidate cache
        CacheManager.invalidate_budget_cache(user_id)
        
        current_app.logger.info(f'Created category {name} for user {user_id}')
        return category
    
    @staticmethod
    def update_category(category_id: int, user_id: int, **kwargs) -> Optional[Category]:
        """Update category."""
        category = Category.query.filter_by(id=category_id, user_id=user_id).first()
        if not category:
            return None
        
        for key, value in kwargs.items():
            if hasattr(category, key):
                setattr(category, key, value)
        
        db.session.commit()
        
        # Invalidate cache
        CacheManager.invalidate_budget_cache(user_id)
        
        current_app.logger.info(f'Updated category {category_id} for user {user_id}')
        return category
    
    @staticmethod
    def delete_category(category_id: int, user_id: int) -> bool:
        """Delete category and all related expenses."""
        category = Category.query.filter_by(id=category_id, user_id=user_id).first()
        if not category:
            return False
        
        db.session.delete(category)
        db.session.commit()
        
        # Invalidate cache
        CacheManager.invalidate_budget_cache(user_id)
        
        current_app.logger.info(f'Deleted category {category_id} for user {user_id}')
        return True
    
    @staticmethod
    def add_expense(user_id: int, category_id: int, amount: Decimal,
                   description: str = None, date_val: date = None, currency: str = None,
                   transaction_type: str = 'expense', carryover_from_month: str = None) -> Expense:
        """Add new expense with backward-compatibility for legacy schemas.

        Some existing SQLite databases still have a NOT NULL 'month' column on the 'expenses' table
        (legacy monolith). Our current ORM model does not include that column. To avoid 500 errors
        like 'NOT NULL constraint failed: expenses.month', we introspect the table schema and
        perform a raw INSERT that includes exactly the columns present in the database. This works
        both for the new schema (no 'month' column) and for legacy schemas (with 'month', and
        possibly without 'transaction_type' or 'carryover_from_month').
        """
        if date_val is None:
            date_val = datetime.utcnow().date()

        # Get currency with fallback for outside request context
        if currency is None:
            try:
                currency = get_user_currency()
            except RuntimeError:
                currency = 'RUB'

        # Introspect current 'expenses' table columns
        def _get_expenses_columns() -> set:
            try:
                rows = db.session.execute(text("PRAGMA table_info(expenses)")).fetchall()
                return {row[1] for row in rows}  # row[1] is 'name'
            except Exception as e:
                current_app.logger.warning(f"Could not introspect expenses table schema: {e}")
                # Fallback: assume modern columns
                return {
                    'id', 'user_id', 'category_id', 'amount', 'description',
                    'date', 'currency', 'transaction_type', 'carryover_from_month', 'created_at'
                }

        columns = _get_expenses_columns()

        # Build insert payload
        year_month = YearMonth.from_date(date_val)
        month_string = year_month.to_string()

        base_values = {
            'user_id': user_id,
            'category_id': category_id,
            'amount': amount,
            'description': description,
            'date': date_val,
            'currency': currency,
            'transaction_type': transaction_type,
            'carryover_from_month': carryover_from_month,
            'created_at': datetime.utcnow(),
            'month': month_string,  # only used if column exists
        }

        # Determine which columns we will insert (intersection with actual table)
        preferred_order = [
            'user_id', 'category_id', 'amount', 'description', 'date', 'currency',
            'transaction_type', 'carryover_from_month', 'created_at', 'month'
        ]
        insert_cols = [c for c in preferred_order if c in columns]
        insert_params = {c: base_values[c] for c in insert_cols}

        try:
            # Use raw INSERT to satisfy legacy constraints if needed
            placeholders = ", ".join(f":{c}" for c in insert_cols)
            col_list = ", ".join(insert_cols)
            db.session.execute(
                text(f"INSERT INTO expenses ({col_list}) VALUES ({placeholders})"),
                insert_params
            )
            db.session.commit()

            # Retrieve last inserted id (SQLite)
            try:
                new_id = db.session.execute(text("SELECT last_insert_rowid()")).scalar()
            except Exception:
                # Generic fallback if last_insert_rowid is not available
                new_id = db.session.execute(text("SELECT id FROM expenses ORDER BY id DESC LIMIT 1")).scalar()

            expense = Expense.query.filter_by(id=new_id, user_id=user_id).first()
            if not expense:
                # As a final fallback, refresh session and try again
                db.session.expire_all()
                expense = Expense.query.filter_by(id=new_id, user_id=user_id).first()

        except Exception as raw_insert_error:
            # If raw path fails for any reason, try ORM insert as a fallback
            db.session.rollback()
            current_app.logger.warning(f"Raw INSERT path failed, fallback to ORM insert: {raw_insert_error}")

            expense = Expense(
                user_id=user_id,
                category_id=category_id,
                amount=amount,
                description=description,
                date=date_val,
                currency=currency,
                month=month_string,
                transaction_type=transaction_type,
                carryover_from_month=carryover_from_month
            )
            db.session.add(expense)
            db.session.commit()

        # Invalidate cache for that month
        CacheManager.invalidate_budget_cache(user_id, year_month)

        current_app.logger.info(f'Added expense {amount} {currency} for user {user_id}')
        return expense
    
    @staticmethod
    def get_expenses_for_month(user_id: int, year_month: YearMonth, 
                             limit: Optional[int] = None, offset: int = 0,
                             category_id: Optional[int] = None) -> List[Expense]:
        """Get expenses for user in given month with optional pagination and filtering."""
        start_date = year_month.to_date()
        end_date = year_month.last_day()
        
        query = Expense.query.filter(
            Expense.user_id == user_id,
            Expense.date >= start_date,
            Expense.date <= end_date,
            Expense.transaction_type == 'expense'  # Only real expenses, not carryover
        )

        # Optional category filter
        if category_id:
            query = query.filter(Expense.category_id == category_id)
        
        query = query.order_by(Expense.date.desc())
        
        # Optional pagination
        if limit:
            query = query.offset(offset).limit(limit)
        
        return query.all()
    
    @staticmethod
    def update_expense(expense_id: int, user_id: int, **kwargs) -> Optional[Expense]:
        """Update expense."""
        expense = Expense.query.filter_by(id=expense_id, user_id=user_id).first()
        if not expense:
            return None
        
        old_date = expense.date
        
        for key, value in kwargs.items():
            if hasattr(expense, key):
                setattr(expense, key, value)
        
        db.session.commit()
        
        # Invalidate cache for both old and new months
        old_year_month = YearMonth.from_date(old_date)
        CacheManager.invalidate_budget_cache(user_id, old_year_month)
        
        if expense.date != old_date:
            new_year_month = YearMonth.from_date(expense.date)
            CacheManager.invalidate_budget_cache(user_id, new_year_month)
        
        current_app.logger.info(f'Updated expense {expense_id} for user {user_id}')
        return expense
    
    @staticmethod
    def delete_expense(expense_id: int, user_id: int) -> bool:
        """Delete expense."""
        expense = Expense.query.filter_by(id=expense_id, user_id=user_id).first()
        if not expense:
            return False
        
        year_month = YearMonth.from_date(expense.date)
        
        db.session.delete(expense)
        db.session.commit()
        
        # Invalidate cache
        CacheManager.invalidate_budget_cache(user_id, year_month)
        
        current_app.logger.info(f'Deleted expense {expense_id} for user {user_id}')
        return True
    
    @staticmethod
    def add_income(user_id: int, source_name: str, amount: Decimal, 
                   date: date = None, year: int = None, month: int = None, currency: str = 'RUB') -> Income:
        """Add income with date support (backward compatible with year/month)."""
        # Ensure income source exists
        source = IncomeSource.query.filter_by(user_id=user_id, name=source_name).first()
        if not source:
            source = IncomeSource(user_id=user_id, name=source_name)
            db.session.add(source)
            db.session.flush()  # Get ID without committing
        
        # Handle date parameter
        if date is not None:
            year = date.year
            month = date.month
        elif year is None or month is None:
            # Default to current date if neither date nor year/month provided
            current_date = datetime.utcnow().date()
            date = current_date
            year = current_date.year
            month = current_date.month
        else:
            # Construct date from year/month (legacy compatibility)
            from datetime import date as date_class
            date = date_class(year, month, 1)
        
        # Try to find existing income
        income = Income.query.filter_by(
            user_id=user_id,
            source_name=source_name,
            year=year,
            month=month
        ).first()
        
        if income:
            income.amount = amount
            income.currency = currency
            income.date = date  # Update date field
        else:
            income = Income(
                user_id=user_id,
                source_name=source_name,
                amount=amount,
                currency=currency,
                date=date,
                year=year,
                month=month
            )
            db.session.add(income)
        
        db.session.commit()
        
        # Invalidate cache
        year_month = YearMonth(year, month)
        CacheManager.invalidate_budget_cache(user_id, year_month)
        
        current_app.logger.info(f'Added income {amount} {currency} for user {user_id}')
        return income

    @staticmethod
    def update_income(income_id: int, user_id: int, source_name: str, amount: Decimal, 
                     date: date = None, year: int = None, month: int = None, currency: str = 'RUB') -> Optional[Income]:
        """Update income with date support (backward compatible with year/month)."""
        income = Income.query.filter_by(id=income_id, user_id=user_id).first()
        if not income:
            return None
        
        # Handle date parameter
        if date is not None:
            year = date.year
            month = date.month
        elif year is not None and month is not None:
            # Construct date from year/month (legacy compatibility)
            from datetime import date as date_class
            date = date_class(year, month, 1)
        else:
            # Keep existing date if no new date info provided
            date = income.date or date_class(income.year, income.month, 1)
            year = date.year
            month = date.month
        
        old_year_month = YearMonth(income.year, income.month) if income.year and income.month else None
        
        # Update fields
        income.source_name = source_name
        income.amount = amount
        income.date = date
        income.year = year
        income.month = month
        income.currency = currency
        
        db.session.commit()
        
        # Invalidate cache for both old and new months
        if old_year_month:
            CacheManager.invalidate_budget_cache(user_id, old_year_month)
        
        if year != (old_year_month.year if old_year_month else None) or \
           month != (old_year_month.month if old_year_month else None):
            new_year_month = YearMonth(year, month)
            CacheManager.invalidate_budget_cache(user_id, new_year_month)
        
        current_app.logger.info(f'Updated income {income_id} for user {user_id}')
        return income

    @staticmethod
    def delete_income(income_id: int, user_id: int) -> bool:
        """Delete income."""
        income = Income.query.filter_by(id=income_id, user_id=user_id).first()
        if not income:
            return False

        # Store source name to check if we need to delete the source
        source_name = income.source_name

        # Use date field if available, fallback to year/month for backward compatibility
        if income.date:
            year_month = YearMonth.from_date(income.date)
        elif income.year and income.month:
            year_month = YearMonth(income.year, income.month)
        else:
            # If we can't determine the date, skip cache invalidation
            year_month = None

        db.session.delete(income)
        db.session.commit()

        # Check if this was the last income with this source
        remaining_incomes = Income.query.filter_by(
            user_id=user_id,
            source_name=source_name
        ).count()

        if remaining_incomes == 0:
            # Delete the income source if no other incomes use it
            from .models import IncomeSource, CategoryRule
            source = IncomeSource.query.filter_by(
                user_id=user_id,
                name=source_name
            ).first()

            if source:
                # Delete related category rules
                CategoryRule.query.filter_by(source_name=source_name).delete()

                # Delete the source
                db.session.delete(source)
                db.session.commit()
                current_app.logger.info(f'Auto-deleted income source "{source_name}" (no more incomes using it)')

        # Invalidate cache if we have date info
        if year_month:
            CacheManager.invalidate_budget_cache(user_id, year_month)

        current_app.logger.info(f'Deleted income {income_id} for user {user_id}')
        return True
    
    @staticmethod
    def get_income_for_month(user_id: int, year_month: YearMonth, 
                           limit: Optional[int] = None, offset: int = 0) -> List[Income]:
        """Get income for user in given month with optional pagination."""
        from sqlalchemy import or_, extract
        
        # Query using both date field and legacy year/month fields for compatibility
        start_date = year_month.to_date()
        end_date = year_month.last_day()
        
        query = Income.query.filter(
            Income.user_id == user_id,
            or_(
                # Use date field if available
                Income.date.between(start_date, end_date),
                # Fallback to year/month for legacy records
                Income.date.is_(None) & 
                (Income.year == year_month.year) & 
                (Income.month == year_month.month)
            )
        ).order_by(Income.created_at.desc())
        
        # Optional pagination
        if limit:
            query = query.offset(offset).limit(limit)
        
        return query.all()
    
    @staticmethod
    def get_total_income_for_month(user_id: int, year_month: YearMonth) -> Money:
        """Get total income for month."""
        incomes = BudgetService.get_income_for_month(user_id, year_month)
        total = sum(income.money_amount.amount for income in incomes)
        
        # Use RUB as default currency for calculations outside of request context
        currency = 'RUB'
        try:
            currency = get_user_currency()
        except RuntimeError:
            # We're outside request context, use RUB as fallback
            pass
            
        return Money(total, currency)
    
    @staticmethod
    def get_category_spending_summary(user_id: int, year_month: YearMonth) -> Dict[int, Decimal]:
        """Get category spending summary with SQL GROUP BY."""
        start_date = year_month.to_date()
        end_date = year_month.last_day()
        
        # SQL aggregate query - much faster than Python grouping
        spending_data = db.session.query(
            Expense.category_id,
            func.sum(Expense.amount).label('total_amount')
        ).filter(
            Expense.user_id == user_id,
            Expense.date >= start_date,
            Expense.date <= end_date,
            Expense.transaction_type == 'expense'  # Only real expenses
        ).group_by(Expense.category_id).all()
        
        # Return as dict for O(1) lookup
        return {cat_id: total for cat_id, total in spending_data}
    
    @staticmethod
    # @cached_per_user_month(timeout=300)  # Temporarily disabled for stabilization
    def calculate_month_snapshot(user_id: int, year_month: YearMonth) -> Dict:
        """Calculate complete budget snapshot for month."""
        categories = BudgetService.get_user_categories(user_id)
        total_income = BudgetService.get_total_income_for_month(user_id, year_month)
        
        # Get category spending summary with SQL GROUP BY
        spending_by_category = BudgetService.get_category_spending_summary(user_id, year_month)
        
        # Calculate category summaries
        category_summaries = []
        
        # Get currency for calculations (fallback to RUB outside request context)
        currency = 'RUB'
        try:
            currency = get_user_currency()
        except RuntimeError:
            pass
            
        total_spent = Money.zero(currency)
        total_limits = Money.zero(currency)

        for category in categories:
            spent_amount = spending_by_category.get(category.id, Decimal('0'))
            spent_money = Money(spent_amount, currency)

            # Calculate limit
            if category.is_multi_source:
                # Calculate limit from multiple sources
                limit = BudgetService.calculate_multi_source_limit(user_id, category.id, year_month)
            elif category.limit_type == 'fixed':
                limit = Money(category.value, currency)
            else:  # percentage
                limit = Money(total_income.amount * (category.value / 100), currency)

            # Get carryover amounts for this category
            carryover_info = BudgetService.get_category_carryover_info(user_id, category.id, year_month)
            
            # Adjust limit with carryover
            effective_limit = limit + Money(carryover_info['amount'], currency)
            
            remaining = effective_limit - spent_money
            is_overspent = remaining.amount < 0
            
            category_summaries.append({
                'category': category,
                'spent': spent_money,
                'limit': limit,
                'effective_limit': effective_limit,
                'carryover': carryover_info,
                'remaining': remaining,
                'is_overspent': is_overspent,
                'percentage_used': (spent_money.amount / effective_limit.amount * 100) if effective_limit.amount > 0 else 0
            })
            
            total_spent += spent_money
            total_limits += effective_limit
        
        total_remaining = total_income - total_spent
        
        return {
            'year_month': year_month,
            'total_income': total_income,
            'total_spent': total_spent,
            'total_limits': total_limits,
            'total_remaining': total_remaining,
            'categories': category_summaries
        }

    @staticmethod
    def calculate_multi_source_limit(user_id: int, category_id: int, year_month: YearMonth) -> Money:
        """Calculate limit for multi-source category based on CategoryRule."""
        from .models import CategoryRule, IncomeSource, Income

        # Get currency
        currency = 'RUB'
        try:
            currency = get_user_currency()
        except RuntimeError:
            pass

        # Get all rules for this category
        rules = (db.session.query(CategoryRule, IncomeSource)
                .join(IncomeSource,
                      db.and_(CategoryRule.source_name == IncomeSource.name,
                             IncomeSource.user_id == user_id))
                .filter(CategoryRule.category_id == category_id)
                .all())

        if not rules:
            return Money.zero(currency)

        total_limit = Decimal('0')

        for rule, source in rules:
            # Get income for this source in this month
            income_record = Income.query.filter_by(
                user_id=user_id,
                source_name=source.name,
                year=year_month.year,
                month=year_month.month
            ).first()

            if income_record:
                if rule.is_fixed:
                    # Fixed amount
                    total_limit += rule.percentage  # percentage field stores fixed amount
                else:
                    # Percentage of source income
                    total_limit += income_record.amount * (rule.percentage / 100)

        return Money(total_limit, currency)

    @staticmethod
    def get_multi_source_links(category_id: int):
        """Get multi-source links for a category."""
        from .models import CategoryRule, IncomeSource, Category
        
        # First get the category to get user_id
        category = Category.query.get(category_id)
        if not category:
            return []
            
        rules = (db.session.query(CategoryRule, IncomeSource)
                .join(IncomeSource, 
                      db.and_(CategoryRule.source_name == IncomeSource.name,
                             IncomeSource.user_id == category.user_id))
                .filter(CategoryRule.category_id == category_id)
                .all())
        
        return [
            {
                'source_id': income_source.id,
                'source_name': income_source.name,
                'percentage': float(rule.percentage)
            }
            for rule, income_source in rules
        ]
    
    @staticmethod
    def get_category_single_source(category_id: int):
        """Get single income source link for a category."""
        from .models import CategoryIncomeSource, IncomeSource

        link = (db.session.query(CategoryIncomeSource)
                .join(IncomeSource, CategoryIncomeSource.source_id == IncomeSource.id)
                .filter(CategoryIncomeSource.category_id == category_id)
                .first())

        return link if link else None

    @staticmethod
    def get_category_carryover_info(user_id: int, category_id: int, year_month: YearMonth) -> Dict:
        """Get carryover information for a category in given month."""
        start_date = year_month.to_date()
        end_date = year_month.last_day()
        
        # Get carryover transactions for this category in this month
        carryovers = Expense.query.filter(
            Expense.user_id == user_id,
            Expense.category_id == category_id,
            Expense.date >= start_date,
            Expense.date <= end_date,
            Expense.transaction_type == 'carryover'
        ).all()
        
        total_amount = Decimal('0')
        details = []
        
        for carryover in carryovers:
            total_amount += carryover.amount
            details.append({
                'amount': carryover.amount,
                'from_month': carryover.carryover_from_month,
                'type': 'remaining' if carryover.amount > 0 else 'overspent'
            })
        
        return {
            'amount': total_amount,
            'has_carryover': len(details) > 0,
            'details': details
        }


class CurrencyService:
    """Currency exchange service."""
    
    @staticmethod
    def get_exchange_rate(from_currency: str, to_currency: str, date_val: date = None) -> Optional[Decimal]:
        """Get exchange rate for currencies."""
        if from_currency == to_currency:
            return Decimal('1.0')
        
        if date_val is None:
            date_val = datetime.utcnow().date()
        
        # Try to get from cache
        rate = ExchangeRate.query.filter_by(
            from_currency=from_currency,
            to_currency=to_currency,
            date=date_val
        ).first()
        
        if rate:
            return rate.rate
        
        # TODO: Fetch from external API and cache
        current_app.logger.warning(f'No exchange rate found for {from_currency}/{to_currency}')
        return None
    
    @staticmethod
    def convert_money(money: Money, to_currency: str, date_val: date = None) -> Optional[Money]:
        """Convert money to different currency."""
        if money.currency == to_currency:
            return money
        
        rate = CurrencyService.get_exchange_rate(money.currency, to_currency, date_val)
        if rate is None:
            return None
        
        converted_amount = money.amount * rate
        return Money(converted_amount, to_currency)


class DashboardService:
    """Dashboard summary service."""
    
    @staticmethod
    def get_income_tiles(user_id: int, year_month: YearMonth) -> List[Dict]:
        """Get dashboard tiles grouped by income sources with debt/surplus tracking."""
        from .models import CategoryRule

        # Get all income for the month
        incomes = BudgetService.get_income_for_month(user_id, year_month)

        # Get categories and spending
        categories = BudgetService.get_user_categories(user_id)
        spending_by_category = BudgetService.get_category_spending_summary(user_id, year_month)

        # Get currency
        currency = 'RUB'
        try:
            currency = get_user_currency()
        except RuntimeError:
            pass

        # Group incomes by source
        income_by_source = {}
        for income in incomes:
            source = income.source_name
            if source not in income_by_source:
                income_by_source[source] = Money.zero(currency)
            income_by_source[source] += Money(income.amount, currency)

        # Create tiles for each source
        tiles = []
        for source_name, income_amount in income_by_source.items():
            # Calculate limits and spending for categories linked to this source
            source_limits = Money.zero(currency)
            source_spent = Money.zero(currency)
            source_debt = Money.zero(currency)  # Accumulated debt for this source

            for category in categories:
                spent_amount = spending_by_category.get(category.id, Decimal('0'))
                spent_money = Money(spent_amount, currency)

                # Calculate this source's contribution to the category limit
                category_limit_from_source = Money.zero(currency)

                if category.is_multi_source:
                    # Get rule for this specific source
                    rule = CategoryRule.query.filter_by(
                        category_id=category.id,
                        source_name=source_name
                    ).first()

                    if rule:
                        # This source contributes to this multi-source category
                        if rule.is_fixed:
                            category_limit_from_source = Money(rule.percentage, currency)  # 'percentage' stores fixed amount
                        else:
                            category_limit_from_source = Money(income_amount.amount * (rule.percentage / 100), currency)

                        # Calculate this source's share of spending (proportional to its limit contribution)
                        if category_limit_from_source.amount > 0:
                            # Get total limit for this category from all sources
                            total_category_limit = BudgetService.calculate_multi_source_limit(user_id, category.id, year_month)

                            if total_category_limit.amount > 0:
                                # Proportional share of spending
                                source_share_ratio = category_limit_from_source.amount / total_category_limit.amount
                                source_spent += spent_money * source_share_ratio

                else:
                    # Single-source category: check if it's linked to this source
                    single_link = BudgetService.get_category_single_source(category.id)
                    if single_link:
                        # Get the IncomeSource to compare with source_name
                        from .models import IncomeSource
                        income_source = IncomeSource.query.get(single_link.source_id)
                        if income_source and income_source.name == source_name:
                            # This category is linked to this source
                            if category.limit_type == 'fixed':
                                category_limit_from_source = Money(category.value, currency)
                            else:  # percentage
                                category_limit_from_source = Money(income_amount.amount * (category.value / 100), currency)

                            source_spent += spent_money

                source_limits += category_limit_from_source

                # Calculate debt/surplus for this category from this source
                # Get carryover info to see if there's debt
                carryover_info = BudgetService.get_category_carryover_info(user_id, category.id, year_month)
                if carryover_info['has_carryover']:
                    for detail in carryover_info['details']:
                        if detail['type'] == 'overspent':  # This is debt
                            # Attribute debt proportionally to this source
                            if category.is_multi_source:
                                rule = CategoryRule.query.filter_by(
                                    category_id=category.id,
                                    source_name=source_name
                                ).first()
                                if rule:
                                    # Proportional debt based on this source's contribution
                                    total_cat_limit = BudgetService.calculate_multi_source_limit(user_id, category.id, year_month)
                                    if total_cat_limit.amount > 0:
                                        if rule.is_fixed:
                                            source_limit_contrib = rule.percentage
                                        else:
                                            source_limit_contrib = income_amount.amount * (rule.percentage / 100)
                                        debt_ratio = source_limit_contrib / total_cat_limit.amount
                                        source_debt += Money(abs(detail['amount']) * debt_ratio, currency)
                            else:
                                # Single source - full debt attribution
                                single_link = BudgetService.get_category_single_source(category.id)
                                if single_link:
                                    from .models import IncomeSource
                                    income_source = IncomeSource.query.get(single_link.source_id)
                                    if income_source and income_source.name == source_name:
                                        source_debt += Money(abs(detail['amount']), currency)

            # Calculate remaining and balance
            remaining = source_limits - source_spent
            balance = income_amount - source_spent

            tiles.append({
                'title': source_name,
                'income': income_amount,
                'limits': source_limits,
                'spent': source_spent,
                'remaining': remaining,
                'debt': source_debt,
                'balance': balance
            })

        return tiles
    
    @staticmethod
    def delete_income_source(source_id: int, user_id: int) -> bool:
        """Delete income source and all related data."""
        source = IncomeSource.query.filter_by(id=source_id, user_id=user_id).first()
        if not source:
            return False
        
        # Delete related category rules
        from .models import CategoryRule
        CategoryRule.query.filter_by(source_name=source.name).delete()
        
        # Delete related income records
        Income.query.filter_by(user_id=user_id, source_name=source.name).delete()
        
        # Delete the source itself
        db.session.delete(source)
        db.session.commit()
        
        # Invalidate cache
        CacheManager.invalidate_budget_cache(user_id)
        
        current_app.logger.info(f'Deleted income source {source.name} for user {user_id}')
        return True
    
    @staticmethod
    def create_carryover(user_id: int, category_id: int, amount: Decimal,
                        from_month: YearMonth, to_month: YearMonth, currency: str = 'RUB') -> Expense:
        """Create a carryover pseudo-transaction.

        Args:
            amount: Positive for surplus (remaining), negative for debt (overspent)
        """
        if amount > 0:
            carryover_description = f"Остаток с {from_month.to_string()}"
        else:
            carryover_description = f"Долг с {from_month.to_string()}"

        return BudgetService.add_expense(
            user_id=user_id,
            category_id=category_id,
            amount=amount,  # Keep the sign: positive = surplus, negative = debt
            description=carryover_description,
            date_val=to_month.to_date(),
            currency=currency,
            transaction_type='carryover',
            carryover_from_month=from_month.to_string()
        )
    
    @staticmethod
    def calculate_category_carryover(user_id: int, category_id: int, year_month: YearMonth) -> Decimal:
        """Calculate carryover amount for a category in given month.

        Returns:
            Positive value = remaining (surplus to carry forward)
            Negative value = overspent (debt to carry forward)
        """
        categories = BudgetService.get_user_categories(user_id)
        category = next((c for c in categories if c.id == category_id), None)
        if not category:
            return Decimal('0')

        # Get currency
        currency = 'RUB'
        try:
            currency = get_user_currency()
        except RuntimeError:
            pass

        # Calculate limit based on category type
        if category.is_multi_source:
            # Calculate limit from multiple sources
            limit = BudgetService.calculate_multi_source_limit(user_id, category.id, year_month)
        elif category.limit_type == 'fixed':
            limit = Money(category.value, currency)
        else:  # percentage
            total_income = BudgetService.get_total_income_for_month(user_id, year_month)
            limit = Money(total_income.amount * (category.value / 100), currency)

        # Get spending summary (excluding carryovers to avoid double counting)
        start_date = year_month.to_date()
        end_date = year_month.last_day()

        total_spent = db.session.query(func.sum(Expense.amount)).filter(
            Expense.user_id == user_id,
            Expense.category_id == category_id,
            Expense.date >= start_date,
            Expense.date <= end_date,
            Expense.transaction_type == 'expense'  # Exclude carryovers
        ).scalar() or Decimal('0')

        # Get existing carryover for this month to include it in balance calculation
        carryover_info = BudgetService.get_category_carryover_info(user_id, category_id, year_month)
        existing_carryover = carryover_info['amount']

        # Calculate balance: positive = remaining, negative = overspent
        # effective_limit = base_limit + existing_carryover
        effective_limit = limit.amount + existing_carryover
        balance = effective_limit - total_spent

        return balance
    
    @staticmethod
    def process_month_carryovers(user_id: int, from_month: YearMonth, to_month: YearMonth):
        """Process carryovers when switching from one month to another.

        Creates carryover transactions for each category:
        - Positive amount = surplus (remaining budget)
        - Negative amount = debt (overspent budget)
        """
        categories = BudgetService.get_user_categories(user_id)

        # First, remove any existing carryovers for the target month
        DashboardService.clear_carryovers_for_month(user_id, to_month)

        for category in categories:
            # Check if category was actually used in from_month (had expenses or existing carryover)
            start_date = from_month.to_date()
            end_date = from_month.last_day()

            had_expenses = db.session.query(Expense).filter(
                Expense.user_id == user_id,
                Expense.category_id == category.id,
                Expense.date >= start_date,
                Expense.date <= end_date,
                Expense.transaction_type == 'expense'
            ).count() > 0

            had_carryover = db.session.query(Expense).filter(
                Expense.user_id == user_id,
                Expense.category_id == category.id,
                Expense.date >= start_date,
                Expense.date <= end_date,
                Expense.transaction_type == 'carryover'
            ).count() > 0

            # Only process carryover if category was used
            if had_expenses or had_carryover:
                balance = DashboardService.calculate_category_carryover(user_id, category.id, from_month)

                if balance != 0:  # Only create carryover if there's a balance (surplus or debt)
                    DashboardService.create_carryover(
                        user_id=user_id,
                        category_id=category.id,
                        amount=balance,  # Keep the sign: positive = surplus, negative = debt
                        from_month=from_month,
                        to_month=to_month
                    )

        current_app.logger.info(f'Processed carryovers from {from_month} to {to_month} for user {user_id}')
    
    @staticmethod
    def clear_carryovers_for_month(user_id: int, year_month: YearMonth):
        """Clear all carryover transactions for a specific month."""
        start_date = year_month.to_date()
        end_date = year_month.last_day()
        
        carryovers = Expense.query.filter(
            Expense.user_id == user_id,
            Expense.date >= start_date,
            Expense.date <= end_date,
            Expense.transaction_type == 'carryover'
        ).all()
        
        for carryover in carryovers:
            db.session.delete(carryover)
        
        db.session.commit()
        
        # Invalidate cache
        CacheManager.invalidate_budget_cache(user_id, year_month)
    

    @staticmethod
    def delete_income_source_new(source_id: int, user_id: int) -> bool:
        """Delete income source and all related data."""
        source = IncomeSource.query.filter_by(id=source_id, user_id=user_id).first()
        if not source:
            return False
        
        # Delete related category rules
        from .models import CategoryRule
        CategoryRule.query.filter_by(source_name=source.name).delete()
        
        # Delete related income records
        Income.query.filter_by(user_id=user_id, source_name=source.name).delete()
        
        # Delete the source itself
        db.session.delete(source)
        db.session.commit()
        
        # Invalidate cache
        CacheManager.invalidate_budget_cache(user_id)
        
        current_app.logger.info(f'Deleted income source {source.name} for user {user_id}')
        return True