"""Template filters for the application."""

from decimal import Decimal
from datetime import datetime
from flask import session

from .services.currency import convert_currency


def format_amount(value, from_currency=None):
    """Число с пробелами для тысяч, автоматическая конвертация валют."""
    try:
        # Автоматическая конвертация если указана исходная валюта
        if from_currency and 'currency' in session:
            target_currency = session['currency']
            if from_currency != target_currency:
                value = convert_currency(value, from_currency, target_currency)
        
        d = Decimal(str(value))
        # Убираем лишние нули после точки
        formatted = f"{d:.2f}".rstrip('0').rstrip('.')
        # Добавляем пробелы
        if '.' in formatted:
            integer, decimal = formatted.split('.')
            integer_with_spaces = f"{int(integer):,}".replace(',', ' ')
            return f"{integer_with_spaces}.{decimal}"
        else:
            return f"{int(formatted):,}".replace(',', ' ')
    except Exception:
        return str(value)


def format_percent(value):
    """Проценты без лишних хвостов, максимум 2 знака после точки."""
    try:
        v = float(value)
        # целые без .0, иначе до 2 знаков
        return f"{int(v)}" if abs(v - int(v)) < 1e-9 else f"{v:.2f}".rstrip('0').rstrip('.')
    except:
        return str(value)


def format_date_with_day(value):
    """Format date with day."""
    try:
        dt = datetime.strptime(value, "%Y-%m-%d")
        return dt.strftime("%d.%m.%Y")
    except Exception:
        return value


def register_filters(app):
    """Register all template filters with the app."""
    app.template_filter("format_amount")(format_amount)
    app.template_filter("format_percent")(format_percent)
    app.template_filter("format_date_with_day")(format_date_with_day)