"""Budget module schemas and forms."""
from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, SelectField, TextAreaField, DateField, HiddenField
from wtforms.validators import DataRequired, NumberRange, Length, Optional
from datetime import datetime
from decimal import Decimal, InvalidOperation
from app.core.money import SUPPORTED_CURRENCIES


class RUDecimalField(DecimalField):
    """DecimalField с поддержкой русской локали (запятые → точки)."""
    
    def process_formdata(self, valuelist):
        if valuelist:
            try:
                # Нормализуем запятые в точки
                normalized_value = str(valuelist[0]).replace(',', '.')
                self.data = Decimal(normalized_value)
            except (ValueError, InvalidOperation):
                self.data = None
                raise ValueError(self.gettext('Not a valid decimal value.'))
        else:
            self.data = None


class CategoryForm(FlaskForm):
    """Category creation/edit form."""
    name = StringField('Название', validators=[
        DataRequired(message='Название обязательно'),
        Length(min=2, max=100, message='Название должно быть от 2 до 100 символов')
    ])
    limit_type = SelectField('Тип лимита', choices=[
        ('fixed', 'Фиксированная сумма'),
        ('percent', 'Процент от дохода')
    ], validators=[DataRequired(message='Выберите тип лимита')])
    value = RUDecimalField('Значение', validators=[
        DataRequired(message='Значение обязательно'),
        NumberRange(min=0, message='Значение должно быть положительным')
    ])


class ExpenseForm(FlaskForm):
    """Expense creation/edit form."""
    category_id = SelectField('Категория', coerce=int, validators=[
        DataRequired(message='Выберите категорию')
    ])
    amount = RUDecimalField('Сумма', validators=[
        DataRequired(message='Сумма обязательна'),
        NumberRange(min=0.01, message='Сумма должна быть больше 0')
    ])
    description = TextAreaField('Описание', validators=[
        Optional(),
        Length(max=500, message='Описание не должно превышать 500 символов')
    ])
    date = DateField('Дата', default=datetime.utcnow, validators=[
        DataRequired(message='Дата обязательна')
    ])
    currency = SelectField('Валюта', choices=[
        (curr, curr) for curr in SUPPORTED_CURRENCIES
    ], default='RUB', validators=[Optional()])


class IncomeForm(FlaskForm):
    """Income creation/edit form."""
    source_name = StringField('Источник дохода', validators=[
        DataRequired(message='Название источника обязательно'),
        Length(min=2, max=100, message='Название должно быть от 2 до 100 символов')
    ])
    amount = RUDecimalField('Сумма', validators=[
        DataRequired(message='Сумма обязательна'),
        NumberRange(min=0.01, message='Сумма должна быть больше 0')
    ])
    year = SelectField('Год', coerce=int, validators=[
        DataRequired(message='Выберите год')
    ])
    month = SelectField('Месяц', coerce=int, choices=[
        (1, 'Январь'), (2, 'Февраль'), (3, 'Март'), (4, 'Апрель'),
        (5, 'Май'), (6, 'Июнь'), (7, 'Июль'), (8, 'Август'),
        (9, 'Сентябрь'), (10, 'Октябрь'), (11, 'Ноябрь'), (12, 'Декабрь')
    ], validators=[DataRequired(message='Выберите месяц')])
    currency = SelectField('Валюта', choices=[
        (curr, curr) for curr in SUPPORTED_CURRENCIES
    ], default='RUB', validators=[Optional()])
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate year choices (current year ± 2)
        current_year = datetime.now().year
        self.year.choices = [
            (year, str(year)) for year in range(current_year - 2, current_year + 3)
        ]


class QuickExpenseForm(FlaskForm):
    """Quick expense form for dashboard."""
    category_id = HiddenField(validators=[DataRequired()])
    amount = RUDecimalField('Сумма', validators=[
        DataRequired(message='Сумма обязательна'),
        NumberRange(min=0.01, message='Сумма должна быть больше 0')
    ])
    description = StringField('Описание', validators=[
        Optional(),
        Length(max=200, message='Описание не должно превышать 200 символов')
    ])


class BudgetFilterForm(FlaskForm):
    """Budget filtering form."""
    year_month = StringField('Месяц (YYYY-MM)', validators=[
        Optional(),
        Length(min=7, max=7, message='Формат: YYYY-MM')
    ])
    category_id = SelectField('Категория', coerce=int, validators=[Optional()])
    
    def __init__(self, categories=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if categories:
            choices = [('', 'Все категории')]
            choices.extend([(cat.id, cat.name) for cat in categories])
            self.category_id.choices = choices


# Data validation schemas
class ExpenseData:
    """Expense data validation schema."""
    
    @staticmethod
    def validate(data: dict) -> dict:
        """Validate and clean expense data."""
        cleaned = {}
        
        # Required fields
        required_fields = ['category_id', 'amount']
        for field in required_fields:
            if field not in data:
                raise ValueError(f'Field {field} is required')
            cleaned[field] = data[field]
        
        # Validate amount
        try:
            amount = float(data['amount'])
            if amount <= 0:
                raise ValueError('Amount must be positive')
            cleaned['amount'] = amount
        except (ValueError, TypeError):
            raise ValueError('Invalid amount format')
        
        # Validate category_id
        try:
            cleaned['category_id'] = int(data['category_id'])
        except (ValueError, TypeError):
            raise ValueError('Invalid category ID')
        
        # Optional fields
        # Accept both 'description' and legacy 'note' from frontend
        if 'description' in data and data['description'] is not None:
            desc = str(data['description']).strip()
            if len(desc) <= 500:
                cleaned['description'] = desc
        elif 'note' in data and data['note'] is not None:
            note = str(data['note']).strip()
            if len(note) <= 500:
                cleaned['description'] = note
        
        if 'currency' in data and data['currency'] in SUPPORTED_CURRENCIES:
            cleaned['currency'] = data['currency']
        else:
            cleaned['currency'] = 'RUB'
        
        # Date validation
        if 'date' in data:
            if isinstance(data['date'], str):
                try:
                    cleaned['date'] = datetime.strptime(data['date'], '%Y-%m-%d').date()
                except ValueError:
                    raise ValueError('Invalid date format (use YYYY-MM-DD)')
            else:
                cleaned['date'] = data['date']
        else:
            cleaned['date'] = datetime.utcnow().date()
        
        return cleaned


class CategoryData:
    """Category data validation schema."""
    
    VALID_LIMIT_TYPES = ['fixed', 'percent']
    
    @staticmethod
    def validate(data: dict) -> dict:
        """Validate and clean category data."""
        cleaned = {}
        
        # Required fields
        if 'name' not in data:
            raise ValueError('Category name is required')
        
        name = str(data['name']).strip()
        if not (2 <= len(name) <= 100):
            raise ValueError('Category name must be 2-100 characters')
        cleaned['name'] = name
        
        if 'limit_type' not in data:
            raise ValueError('Limit type is required')
        
        if data['limit_type'] not in CategoryData.VALID_LIMIT_TYPES:
            raise ValueError('Invalid limit type')
        cleaned['limit_type'] = data['limit_type']
        
        if 'value' not in data:
            raise ValueError('Limit value is required')
        
        try:
            value = float(data['value'])
            if value < 0:
                raise ValueError('Limit value must be non-negative')
            
            # Additional validation for percentage
            if data['limit_type'] == 'percent' and value > 100:
                raise ValueError('Percentage cannot exceed 100%')
            
            cleaned['value'] = value
        except (ValueError, TypeError):
            raise ValueError('Invalid limit value')
        
        return cleaned


class IncomeData:
    """Income data validation schema."""
    
    @staticmethod
    def validate(data: dict) -> dict:
        """Validate and clean income data."""
        cleaned = {}
        
        # Required fields
        required_fields = ['source_name', 'amount', 'year', 'month']
        for field in required_fields:
            if field not in data:
                raise ValueError(f'Field {field} is required')
        
        # Validate source name
        source_name = str(data['source_name']).strip()
        if not (2 <= len(source_name) <= 100):
            raise ValueError('Source name must be 2-100 characters')
        cleaned['source_name'] = source_name
        
        # Validate amount
        try:
            amount = float(data['amount'])
            if amount <= 0:
                raise ValueError('Amount must be positive')
            cleaned['amount'] = amount
        except (ValueError, TypeError):
            raise ValueError('Invalid amount format')
        
        # Validate year/month
        try:
            year = int(data['year'])
            month = int(data['month'])
            
            if not (2020 <= year <= 2030):
                raise ValueError('Year must be between 2020 and 2030')
            
            if not (1 <= month <= 12):
                raise ValueError('Month must be between 1 and 12')
            
            cleaned['year'] = year
            cleaned['month'] = month
        except (ValueError, TypeError):
            raise ValueError('Invalid year or month')
        
        # Currency
        if 'currency' in data and data['currency'] in SUPPORTED_CURRENCIES:
            cleaned['currency'] = data['currency']
        else:
            cleaned['currency'] = 'RUB'
        
        return cleaned