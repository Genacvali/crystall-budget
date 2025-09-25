"""Budget service layer."""
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from datetime import datetime, date
from sqlalchemy import func, extract
from flask import current_app
from app.core.extensions import db
from app.core.money import Money, SUPPORTED_CURRENCIES, get_user_currency
from app.core.time import YearMonth
from app.core.caching import cached_per_user_month, CacheManager
from .models import Category, Expense, Income, CategoryRule, ExchangeRate


class BudgetService:
    """Budget business logic service."""
    
    @staticmethod
    def get_user_categories(user_id: int) -> List[Category]:
        """Get all categories for user."""
        return Category.query.filter_by(user_id=user_id).order_by(Category.name).all()
    
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
                   description: str = None, date_val: date = None, currency: str = None) -> Expense:
        """Add new expense."""
        if date_val is None:
            date_val = datetime.utcnow().date()
        
        # Get currency with fallback for outside request context
        if currency is None:
            try:
                currency = get_user_currency()
            except RuntimeError:
                currency = 'RUB'
        
        expense = Expense(
            user_id=user_id,
            category_id=category_id,
            amount=amount,
            description=description,
            date=date_val,
            currency=currency
        )
        db.session.add(expense)
        db.session.commit()
        
        # Invalidate cache for that month
        year_month = YearMonth.from_date(date_val)
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
            Expense.date <= end_date
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
                   year: int, month: int, currency: str = 'RUB') -> Income:
        """Add or update income for month."""
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
        else:
            income = Income(
                user_id=user_id,
                source_name=source_name,
                amount=amount,
                currency=currency,
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
                     year: int, month: int, currency: str = 'RUB') -> Optional[Income]:
        """Update income."""
        income = Income.query.filter_by(id=income_id, user_id=user_id).first()
        if not income:
            return None
        
        old_year_month = YearMonth(income.year, income.month)
        
        # Update fields
        income.source_name = source_name
        income.amount = amount
        income.year = year
        income.month = month
        income.currency = currency
        
        db.session.commit()
        
        # Invalidate cache for both old and new months
        CacheManager.invalidate_budget_cache(user_id, old_year_month)
        
        if income.year != old_year_month.year or income.month != old_year_month.month:
            new_year_month = YearMonth(income.year, income.month)
            CacheManager.invalidate_budget_cache(user_id, new_year_month)
        
        current_app.logger.info(f'Updated income {income_id} for user {user_id}')
        return income

    @staticmethod
    def delete_income(income_id: int, user_id: int) -> bool:
        """Delete income."""
        income = Income.query.filter_by(id=income_id, user_id=user_id).first()
        if not income:
            return False
        
        year_month = YearMonth(income.year, income.month)
        
        db.session.delete(income)
        db.session.commit()
        
        # Invalidate cache
        CacheManager.invalidate_budget_cache(user_id, year_month)
        
        current_app.logger.info(f'Deleted income {income_id} for user {user_id}')
        return True
    
    @staticmethod
    def get_income_for_month(user_id: int, year_month: YearMonth, 
                           limit: Optional[int] = None, offset: int = 0) -> List[Income]:
        """Get income for user in given month with optional pagination."""
        query = Income.query.filter_by(
            user_id=user_id,
            year=year_month.year,
            month=year_month.month
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
            Expense.date <= end_date
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
            if category.limit_type == 'fixed':
                limit = Money(category.value, currency)
            else:  # percentage
                limit = Money(total_income.amount * (category.value / 100), currency)
            
            remaining = limit - spent_money
            is_overspent = remaining.amount < 0
            
            category_summaries.append({
                'category': category,
                'spent': spent_money,
                'limit': limit,
                'remaining': remaining,
                'is_overspent': is_overspent,
                'percentage_used': (spent_money.amount / limit.amount * 100) if limit.amount > 0 else 0
            })
            
            total_spent += spent_money
            total_limits += limit
        
        total_remaining = total_income - total_spent
        
        return {
            'year_month': year_month,
            'total_income': total_income,
            'total_spent': total_spent,
            'total_limits': total_limits,
            'total_remaining': total_remaining,
            'categories': category_summaries
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