"""Money handling utilities."""
from decimal import Decimal, ROUND_HALF_UP


class Money:
    """Immutable money value with currency."""
    
    def __init__(self, amount, currency='RUB'):
        """Initialize Money with automatic Decimal conversion."""
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        self._amount = amount
        self._currency = currency
    
    @property
    def amount(self) -> Decimal:
        return self._amount
    
    @property
    def currency(self) -> str:
        return self._currency
    
    def __str__(self) -> str:
        return self.format()
    
    def format(self, show_currency: bool = True) -> str:
        """Format money for display."""
        # Round to 2 decimal places for display
        rounded = self.amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        if self.currency == 'RUB':
            formatted = f"{rounded:,.2f}".replace(',', ' ')
            return f"{formatted} ₽" if show_currency else formatted
        elif self.currency == 'USD':
            formatted = f"{rounded:,.2f}"
            return f"${formatted}" if show_currency else formatted
        elif self.currency == 'EUR':
            formatted = f"{rounded:,.2f}".replace(',', ' ')
            return f"{formatted} €" if show_currency else formatted
        else:
            formatted = f"{rounded:,.2f}"
            return f"{formatted} {self.currency}" if show_currency else formatted
    
    def __add__(self, other):
        """Add two money values (must be same currency)."""
        if isinstance(other, Money):
            if self.currency != other.currency:
                raise ValueError(f"Cannot add {self.currency} and {other.currency}")
            return Money(self.amount + other.amount, self.currency)
        elif isinstance(other, (int, float, Decimal)):
            return Money(self.amount + Decimal(str(other)), self.currency)
        return NotImplemented
    
    def __sub__(self, other):
        """Subtract two money values (must be same currency)."""
        if isinstance(other, Money):
            if self.currency != other.currency:
                raise ValueError(f"Cannot subtract {other.currency} from {self.currency}")
            return Money(self.amount - other.amount, self.currency)
        elif isinstance(other, (int, float, Decimal)):
            return Money(self.amount - Decimal(str(other)), self.currency)
        return NotImplemented
    
    def __mul__(self, other):
        """Multiply money by a number."""
        if isinstance(other, (int, float, Decimal)):
            return Money(self.amount * Decimal(str(other)), self.currency)
        return NotImplemented
    
    def __truediv__(self, other):
        """Divide money by a number."""
        if isinstance(other, (int, float, Decimal)):
            return Money(self.amount / Decimal(str(other)), self.currency)
        return NotImplemented
    
    def __neg__(self):
        """Negate money value."""
        return Money(-self.amount, self.currency)
    
    def __abs__(self):
        """Absolute value of money."""
        return Money(abs(self.amount), self.currency)
    
    @classmethod
    def zero(cls, currency: str = 'RUB') -> 'Money':
        """Create zero money value."""
        return cls(Decimal('0'), currency)
    
    @classmethod
    def from_float(cls, amount: float, currency: str = 'RUB') -> 'Money':
        """Create money from float (use with caution)."""
        return cls(Decimal(str(amount)), currency)
    
    @classmethod
    def from_string(cls, amount: str, currency: str = 'RUB') -> 'Money':
        """Create money from string."""
        return cls(Decimal(amount), currency)


def parse_money(value: str, currency: str = 'RUB') -> Money:
    """Parse money from user input string."""
    if not value:
        return Money.zero(currency)
    
    # Remove common formatting
    cleaned = value.replace(' ', '').replace(',', '.')
    
    try:
        return Money(Decimal(cleaned), currency)
    except:
        raise ValueError(f"Invalid money value: {value}")


# Common currency codes supported
SUPPORTED_CURRENCIES = ['RUB', 'USD', 'EUR', 'AMD', 'GEL']