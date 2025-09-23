"""Jinja2 template filters."""
from decimal import Decimal
from datetime import datetime
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


def register_filters(app: Flask):
    """Register custom filters with Flask app."""
    app.jinja_env.filters['format_amount'] = format_amount
    app.jinja_env.filters['format_currency'] = format_currency
    app.jinja_env.filters['percentage'] = percentage
    app.jinja_env.filters['format_date_with_day'] = format_date_with_day