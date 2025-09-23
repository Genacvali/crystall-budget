"""Auth module schemas and forms."""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional


class LoginForm(FlaskForm):
    """Email login form (disabled - only Telegram auth)."""
    email = StringField('Email', validators=[
        DataRequired(message='Email обязателен')
    ])
    password = PasswordField('Пароль', validators=[
        DataRequired(message='Пароль обязателен')
    ])
    remember_me = BooleanField('Запомнить меня')


class RegisterForm(FlaskForm):
    """Email registration form (disabled - only Telegram auth)."""
    name = StringField('Имя', validators=[
        DataRequired(message='Имя обязательно'),
        Length(min=2, max=100, message='Имя должно быть от 2 до 100 символов')
    ])
    email = StringField('Email', validators=[
        DataRequired(message='Email обязателен')
    ])
    password = PasswordField('Пароль', validators=[
        DataRequired(message='Пароль обязателен'),
        Length(min=6, message='Пароль должен быть не менее 6 символов')
    ])
    password_confirm = PasswordField('Подтвердите пароль', validators=[
        DataRequired(message='Подтверждение пароля обязательно'),
        EqualTo('password', message='Пароли не совпадают')
    ])


class ChangePasswordForm(FlaskForm):
    """Change password form."""
    current_password = PasswordField('Текущий пароль', validators=[
        DataRequired(message='Текущий пароль обязателен')
    ])
    new_password = PasswordField('Новый пароль', validators=[
        DataRequired(message='Новый пароль обязателен'),
        Length(min=6, message='Пароль должен быть не менее 6 символов')
    ])
    new_password_confirm = PasswordField('Подтвердите новый пароль', validators=[
        DataRequired(message='Подтверждение нового пароля обязательно'),
        EqualTo('new_password', message='Пароли не совпадают')
    ])


class ProfileForm(FlaskForm):
    """User profile form."""
    name = StringField('Имя', validators=[
        DataRequired(message='Имя обязательно'),
        Length(min=2, max=100, message='Имя должно быть от 2 до 100 символов')
    ])
    theme = SelectField('Тема', choices=[
        ('light', 'Светлая'),
        ('dark', 'Темная')
    ], validators=[Optional()])
    currency = SelectField('Валюта', choices=[
        ('RUB', 'Рубль (₽)'),
        ('USD', 'Доллар ($)'),
        ('EUR', 'Евро (€)'),
        ('AMD', 'Драм (֏)'),
        ('GEL', 'Лари (₾)')
    ], validators=[Optional()])
    timezone = SelectField('Часовой пояс', choices=[
        ('UTC', 'UTC'),
        ('Europe/Moscow', 'Москва'),
        ('Europe/Kiev', 'Киев'),
        ('Asia/Yerevan', 'Ереван'),
        ('Asia/Tbilisi', 'Тбилиси')
    ], validators=[Optional()])


# Data schemas for validation
class TelegramAuthData:
    """Telegram authentication data schema."""
    
    @staticmethod
    def validate(data: dict) -> bool:
        """Validate Telegram auth data."""
        required_fields = ['id', 'auth_date']
        
        for field in required_fields:
            if field not in data:
                return False
        
        # Validate ID is integer
        try:
            int(data['id'])
        except (ValueError, TypeError):
            return False
        
        # Validate auth_date is integer timestamp
        try:
            int(data['auth_date'])
        except (ValueError, TypeError):
            return False
        
        return True


class UserPreferencesData:
    """User preferences data schema."""
    
    ALLOWED_THEMES = ['light', 'dark']
    ALLOWED_CURRENCIES = ['RUB', 'USD', 'EUR', 'AMD', 'GEL']
    ALLOWED_TIMEZONES = ['UTC', 'Europe/Moscow', 'Europe/Kiev', 'Asia/Yerevan', 'Asia/Tbilisi']
    
    @staticmethod
    def validate(data: dict) -> dict:
        """Validate and clean preferences data."""
        cleaned = {}
        
        if 'theme' in data and data['theme'] in UserPreferencesData.ALLOWED_THEMES:
            cleaned['theme'] = data['theme']
        
        if 'currency' in data and data['currency'] in UserPreferencesData.ALLOWED_CURRENCIES:
            cleaned['currency'] = data['currency']
            # Also set default_currency for compatibility
            cleaned['default_currency'] = data['currency']
        
        if 'timezone' in data and data['timezone'] in UserPreferencesData.ALLOWED_TIMEZONES:
            cleaned['timezone'] = data['timezone']
        
        if 'name' in data and isinstance(data['name'], str) and 2 <= len(data['name']) <= 100:
            cleaned['name'] = data['name'].strip()
        
        return cleaned