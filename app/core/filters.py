"""Jinja2 template filters."""
from decimal import Decimal
from datetime import datetime, date
import calendar
from flask import Flask


def format_amount(value):
    """Format amount for display."""
    if value is None:
        return "0,00"
    
    if isinstance(value, (int, float)):
        value = Decimal(str(value))
    elif not isinstance(value, Decimal):
        try:
            value = Decimal(str(value))
        except:
            return "0,00"
    
    # Round to 2 decimal places
    rounded = value.quantize(Decimal('0.01'))
    
    # Format with thousand separators
    formatted = f"{rounded:,.2f}".replace(',', ' ')
    return formatted


def format_currency(value, currency='RUB'):
    """Format amount with currency symbol."""
    formatted = format_amount(value)
    
    if currency == 'RUB':
        return f"{formatted} ₽"
    elif currency == 'USD':
        return f"${formatted}"
    elif currency == 'EUR':
        return f"{formatted} €"
    elif currency == 'AMD':
        return f"{formatted} ֏"
    elif currency == 'GEL':
        return f"{formatted} ₾"
    else:
        return f"{formatted} {currency}"


def percentage(value):
    """Format percentage."""
    if value is None:
        return "0%"
    
    try:
        percent = float(value)
        return f"{percent:.1f}%"
    except:
        return "0%"


def format_date_with_day(value):
    """Format date with day in DD.MM.YYYY format."""
    if value is None:
        return ""
    
    try:
        if isinstance(value, str):
            dt = datetime.strptime(value, "%Y-%m-%d")
        elif hasattr(value, 'strftime'):  # datetime object
            dt = value
        else:
            return str(value)
        
        return dt.strftime("%d.%m.%Y")
    except Exception:
        return str(value)


RU_MONTHS = {
    1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
    5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
    9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь",
}


def format_month_ru(value):
    """`value` может быть ('2025', '09') или (2025, 9) или date."""
    if isinstance(value, tuple) and len(value) == 2:
        y, m = value
        y = int(y); m = int(m)
    elif isinstance(value, date):
        y, m = value.year, value.month
    else:
        # '2025-09' / '2025-9'
        parts = str(value).split("-")
        y = int(parts[0]); m = int(parts[1])
    return f"{RU_MONTHS.get(m, calendar.month_name[m])} {y}"


def format_month_with_day(income_obj):
    """Форматирует месяц с днем из объекта Income."""
    try:
        # Приоритет: поле date, затем year/month
        if hasattr(income_obj, 'date') and income_obj.date:
            dt = income_obj.date
            day = dt.day
            month_name = RU_MONTHS.get(dt.month, calendar.month_name[dt.month])
            return f"{day} {month_name} {dt.year}"
        elif hasattr(income_obj, 'year') and hasattr(income_obj, 'month') and income_obj.year and income_obj.month:
            # Для legacy записей показываем 1-е число
            month_name = RU_MONTHS.get(income_obj.month, calendar.month_name[income_obj.month])
            return f"1 {month_name} {income_obj.year}"
        else:
            return "Не указано"
    except Exception as e:
        return "Ошибка отображения"


def register_filters(app: Flask):
    """Register custom filters with Flask app."""
    app.jinja_env.filters['format_amount'] = format_amount
    app.jinja_env.filters['format_currency'] = format_currency
    app.jinja_env.filters['percentage'] = percentage
    app.jinja_env.filters['format_date_with_day'] = format_date_with_day
    app.jinja_env.filters['format_month_ru'] = format_month_ru
    app.jinja_env.filters['format_month_with_day'] = format_month_with_day

    # Add built-in Python functions to Jinja2 globals
    app.jinja_env.globals['abs'] = abs
    app.jinja_env.globals['min'] = min
    app.jinja_env.globals['max'] = max