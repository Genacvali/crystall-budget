"""Goals module schemas and forms."""
from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, TextAreaField, DateField, SelectField, HiddenField
from wtforms.validators import DataRequired, NumberRange, Length, Optional
from datetime import datetime, date
from app.core.money import SUPPORTED_CURRENCIES


class SavingsGoalForm(FlaskForm):
    """Savings goal creation/edit form."""
    title = StringField('Название цели', validators=[
        DataRequired(message='Название обязательно'),
        Length(min=2, max=200, message='Название должно быть от 2 до 200 символов')
    ])
    description = TextAreaField('Описание', validators=[
        Optional(),
        Length(max=1000, message='Описание не должно превышать 1000 символов')
    ])
    target_amount = DecimalField('Целевая сумма', validators=[
        DataRequired(message='Целевая сумма обязательна'),
        NumberRange(min=0.01, message='Сумма должна быть больше 0')
    ])
    target_date = DateField('Целевая дата', validators=[Optional()])
    currency = SelectField('Валюта', choices=[
        (curr, curr) for curr in SUPPORTED_CURRENCIES
    ], default='RUB', validators=[Optional()])


class GoalProgressForm(FlaskForm):
    """Goal progress update form."""
    goal_id = HiddenField(validators=[DataRequired()])
    amount = DecimalField('Сумма', validators=[
        DataRequired(message='Сумма обязательна'),
        NumberRange(min=0.01, message='Сумма должна быть больше 0')
    ])


class SharedBudgetForm(FlaskForm):
    """Shared budget creation form."""
    name = StringField('Название бюджета', validators=[
        DataRequired(message='Название обязательно'),
        Length(min=2, max=200, message='Название должно быть от 2 до 200 символов')
    ])
    description = TextAreaField('Описание', validators=[
        Optional(),
        Length(max=1000, message='Описание не должно превышать 1000 символов')
    ])


class JoinBudgetForm(FlaskForm):
    """Join shared budget form."""
    invitation_code = StringField('Код приглашения', validators=[
        DataRequired(message='Код приглашения обязателен'),
        Length(min=8, max=8, message='Код должен содержать 8 символов')
    ])


class MemberRoleForm(FlaskForm):
    """Update member role form."""
    role = SelectField('Роль', choices=[
        ('member', 'Участник'),
        ('viewer', 'Наблюдатель')
    ], validators=[DataRequired(message='Выберите роль')])


# Data validation schemas
class SavingsGoalData:
    """Savings goal data validation schema."""
    
    @staticmethod
    def validate(data: dict) -> dict:
        """Validate and clean savings goal data."""
        cleaned = {}
        
        # Required fields
        if 'title' not in data:
            raise ValueError('Goal title is required')
        
        title = str(data['title']).strip()
        if not (2 <= len(title) <= 200):
            raise ValueError('Goal title must be 2-200 characters')
        cleaned['title'] = title
        
        if 'target_amount' not in data:
            raise ValueError('Target amount is required')
        
        try:
            target_amount = float(data['target_amount'])
            if target_amount <= 0:
                raise ValueError('Target amount must be positive')
            cleaned['target_amount'] = target_amount
        except (ValueError, TypeError):
            raise ValueError('Invalid target amount')
        
        # Optional fields
        if 'description' in data:
            desc = str(data['description']).strip()
            if len(desc) <= 1000:
                cleaned['description'] = desc
        
        if 'target_date' in data and data['target_date']:
            if isinstance(data['target_date'], str):
                try:
                    cleaned['target_date'] = datetime.strptime(data['target_date'], '%Y-%m-%d').date()
                except ValueError:
                    raise ValueError('Invalid target date format (use YYYY-MM-DD)')
            elif isinstance(data['target_date'], date):
                cleaned['target_date'] = data['target_date']
        
        if 'currency' in data and data['currency'] in SUPPORTED_CURRENCIES:
            cleaned['currency'] = data['currency']
        else:
            cleaned['currency'] = 'RUB'
        
        return cleaned


class GoalProgressData:
    """Goal progress data validation schema."""
    
    @staticmethod
    def validate(data: dict) -> dict:
        """Validate and clean goal progress data."""
        cleaned = {}
        
        # Required fields
        if 'goal_id' not in data:
            raise ValueError('Goal ID is required')
        
        try:
            cleaned['goal_id'] = int(data['goal_id'])
        except (ValueError, TypeError):
            raise ValueError('Invalid goal ID')
        
        if 'amount' not in data:
            raise ValueError('Progress amount is required')
        
        try:
            amount = float(data['amount'])
            if amount <= 0:
                raise ValueError('Progress amount must be positive')
            cleaned['amount'] = amount
        except (ValueError, TypeError):
            raise ValueError('Invalid progress amount')
        
        return cleaned


class SharedBudgetData:
    """Shared budget data validation schema."""
    
    @staticmethod
    def validate(data: dict) -> dict:
        """Validate and clean shared budget data."""
        cleaned = {}
        
        # Required fields
        if 'name' not in data:
            raise ValueError('Budget name is required')
        
        name = str(data['name']).strip()
        if not (2 <= len(name) <= 200):
            raise ValueError('Budget name must be 2-200 characters')
        cleaned['name'] = name
        
        # Optional fields
        if 'description' in data:
            desc = str(data['description']).strip()
            if len(desc) <= 1000:
                cleaned['description'] = desc
        
        return cleaned


class InvitationCodeData:
    """Invitation code validation schema."""
    
    @staticmethod
    def validate(data: dict) -> dict:
        """Validate and clean invitation code data."""
        cleaned = {}
        
        if 'invitation_code' not in data:
            raise ValueError('Invitation code is required')
        
        code = str(data['invitation_code']).strip().upper()
        if len(code) != 8:
            raise ValueError('Invitation code must be 8 characters')
        
        # Only allow alphanumeric characters
        if not code.isalnum():
            raise ValueError('Invalid invitation code format')
        
        cleaned['invitation_code'] = code
        return cleaned


class MemberRoleData:
    """Member role validation schema."""
    
    VALID_ROLES = ['member', 'viewer']
    
    @staticmethod
    def validate(data: dict) -> dict:
        """Validate and clean member role data."""
        cleaned = {}
        
        if 'role' not in data:
            raise ValueError('Role is required')
        
        role = str(data['role']).strip().lower()
        if role not in MemberRoleData.VALID_ROLES:
            raise ValueError('Invalid role')
        
        cleaned['role'] = role
        return cleaned