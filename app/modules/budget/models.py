"""Budget module models."""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import func
from app.core.extensions import db
from app.core.money import Money
from app.core.time import YearMonth


class Category(db.Model):
    """Budget category model."""
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    limit_type = db.Column(db.String(20), nullable=False)  # 'fixed' or 'percent'
    value = db.Column(db.Numeric(10, 2), nullable=False)
    is_multi_source = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    expenses = db.relationship('Expense', backref='category', cascade='all, delete-orphan')
    rules = db.relationship('CategoryRule', backref='category', cascade='all, delete-orphan')
    
    __table_args__ = (db.UniqueConstraint('user_id', 'name'),)
    
    def __repr__(self):
        return f'<Category {self.name}>'
    
    @property
    def limit_value(self):
        """Get limit as Money object."""
        return Money(self.value, 'RUB')  # TODO: use user's currency
    
    def get_spent_for_month(self, year_month: YearMonth) -> Money:
        """Get total spent for this category in given month."""
        start_date = year_month.to_date()
        end_date = year_month.last_day()
        
        total = db.session.query(func.sum(Expense.amount)).filter(
            Expense.category_id == self.id,
            Expense.date >= start_date,
            Expense.date <= end_date,
            Expense.transaction_type == 'expense'  # Only real expenses
        ).scalar() or Decimal('0')
        
        return Money(total, 'RUB')  # TODO: use user's currency


class Expense(db.Model):
    """Expense model."""
    __tablename__ = 'expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.Text)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    currency = db.Column(db.String(3), default='RUB')
    month = db.Column(db.String(7), nullable=False, default='2024-01')  # YYYY-MM format for legacy compatibility
    transaction_type = db.Column(db.String(20), default='expense')  # 'expense', 'carryover'
    carryover_from_month = db.Column(db.String(7), nullable=True)  # YYYY-MM format for carryover tracking
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Expense {self.amount} {self.currency}>'
    
    @property
    def money_amount(self):
        """Get amount as Money object."""
        return Money(self.amount, self.currency)
    
    @property
    def is_carryover(self):
        """Check if this is a carryover transaction."""
        return self.transaction_type == 'carryover'
    
    @property
    def is_expense(self):
        """Check if this is a regular expense."""
        return self.transaction_type == 'expense'


class Income(db.Model):
    """Income model."""
    __tablename__ = 'income'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    source_name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default='RUB')
    # New date field - will replace year/month eventually
    date = db.Column(db.Date, nullable=True)  # Initially nullable for migration
    # Legacy fields - kept for backward compatibility during migration
    year = db.Column(db.Integer, nullable=True)  # Made nullable for migration
    month = db.Column(db.Integer, nullable=True)  # Made nullable for migration
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'source_name', 'year', 'month'),)
    
    def __repr__(self):
        return f'<Income {self.amount} {self.currency}>'
    
    @property
    def money_amount(self):
        """Get amount as Money object."""
        return Money(self.amount, self.currency)
    
    @property
    def year_month(self):
        """Get as YearMonth object."""
        return YearMonth(self.year, self.month)


class CategoryRule(db.Model):
    """Category to income source mapping."""
    __tablename__ = 'category_rules'

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='CASCADE'), nullable=False)
    source_name = db.Column(db.String(100), nullable=False)
    percentage = db.Column(db.Numeric(5, 2), default=100.0)  # For multi-source categories
    is_fixed = db.Column(db.Boolean, default=False)  # True if percentage is fixed amount in rubles
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('category_id', 'source_name'),)
    
    def __repr__(self):
        return f'<CategoryRule {self.source_name} -> {self.category.name}>'


class ExchangeRate(db.Model):
    """Currency exchange rates cache."""
    __tablename__ = 'exchange_rates'
    
    id = db.Column(db.Integer, primary_key=True)
    from_currency = db.Column(db.String(3), nullable=False)
    to_currency = db.Column(db.String(3), nullable=False)
    rate = db.Column(db.Numeric(10, 6), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('from_currency', 'to_currency', 'date'),)
    
    def __repr__(self):
        return f'<ExchangeRate {self.from_currency}/{self.to_currency} = {self.rate}>'


class IncomeSource(db.Model):
    """Income source model."""
    __tablename__ = 'income_sources'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'name'),)
    
    def __repr__(self):
        return f'<IncomeSource {self.name}>'


class CategoryIncomeSource(db.Model):
    """Category to income source mapping for multi-source categories."""
    __tablename__ = 'category_income_sources'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='CASCADE'), nullable=False)
    source_id = db.Column(db.Integer, db.ForeignKey('income_sources.id', ondelete='CASCADE'), nullable=False)
    
    # Limit configuration - either percentage OR fixed amount
    limit_type = db.Column(db.String(10), nullable=False, default='percent')  # 'percent' or 'fixed'
    percentage = db.Column(db.Numeric(5, 2), nullable=True)  # For percentage-based limits
    fixed_amount = db.Column(db.Numeric(10, 2), nullable=True)  # For fixed limits
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('category_id', 'source_id'),
        db.CheckConstraint('limit_type IN ("percent", "fixed")'),
        db.CheckConstraint(
            '(limit_type = "percent" AND percentage IS NOT NULL AND fixed_amount IS NULL) OR '
            '(limit_type = "fixed" AND fixed_amount IS NOT NULL AND percentage IS NULL)'
        )
    )
    
    # Relationships
    category = db.relationship('Category', backref=db.backref('income_source_links', cascade='all, delete-orphan'))
    source = db.relationship('IncomeSource', backref='category_links')
    
    def __repr__(self):
        if self.limit_type == 'percent':
            return f'<CategoryIncomeSource {self.category.name} <- {self.source.name} ({self.percentage}%)>'
        else:
            return f'<CategoryIncomeSource {self.category.name} <- {self.source.name} ({self.fixed_amount} RUB)>'
    
    @property
    def display_value(self):
        """Get display value for the limit."""
        if self.limit_type == 'percent':
            return f"{self.percentage}%"
        else:
            return f"{self.fixed_amount} ₽"