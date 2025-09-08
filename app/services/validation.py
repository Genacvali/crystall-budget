"""Validation utilities."""

from datetime import datetime


def validate_amount(amount_str):
    """Validate and return amount as float, or None if invalid."""
    if not amount_str or not amount_str.strip():
        return None
    try:
        amount = float(amount_str.strip())
        return amount if amount > 0 else None
    except (ValueError, TypeError):
        return None


def validate_date(date_str):
    """Validate and return date string in YYYY-MM-DD format, or None if invalid."""
    if not date_str or not date_str.strip():
        return None
    try:
        datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return date_str.strip()
    except ValueError:
        return None


def sanitize_string(s, max_length=255):
    """Sanitize and limit string length."""
    if not s:
        return ""
    return str(s).strip()[:max_length]