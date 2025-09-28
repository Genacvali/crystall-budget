"""Time handling utilities."""
from datetime import datetime, date
from typing import NamedTuple, Iterator
import calendar


class YearMonth(NamedTuple):
    """Immutable year-month pair for budget periods."""
    year: int
    month: int
    
    def __str__(self) -> str:
        return f"{self.year}-{self.month:02d}"
    
    def to_string(self) -> str:
        """Convert to string format."""
        return str(self)
    
    @classmethod
    def current(cls) -> 'YearMonth':
        """Get current year-month."""
        now = datetime.utcnow()
        return cls(now.year, now.month)
    
    @classmethod
    def from_date(cls, d: date) -> 'YearMonth':
        """Create from date object."""
        return cls(d.year, d.month)
    
    @classmethod
    def from_string(cls, s: str) -> 'YearMonth':
        """Parse from string like '2025-01' or '2025-1'."""
        parts = s.split('-')
        if len(parts) != 2:
            raise ValueError(f"Invalid year-month format: {s}")
        
        try:
            year = int(parts[0])
            month = int(parts[1])
            if not (1 <= month <= 12):
                raise ValueError(f"Month must be 1-12, got {month}")
            return cls(year, month)
        except ValueError as e:
            raise ValueError(f"Invalid year-month format: {s}") from e
    
    def to_date(self) -> date:
        """Convert to first day of the month."""
        return date(self.year, self.month, 1)
    
    def last_day(self) -> date:
        """Get last day of the month."""
        last_day = calendar.monthrange(self.year, self.month)[1]
        return date(self.year, self.month, last_day)
    
    def next_month(self) -> 'YearMonth':
        """Get next month."""
        if self.month == 12:
            return YearMonth(self.year + 1, 1)
        return YearMonth(self.year, self.month + 1)
    
    def prev_month(self) -> 'YearMonth':
        """Get previous month."""
        if self.month == 1:
            return YearMonth(self.year - 1, 12)
        return YearMonth(self.year, self.month - 1)
    
    def months_between(self, other: 'YearMonth') -> int:
        """Calculate months between two year-months."""
        return (other.year - self.year) * 12 + (other.month - self.month)
    
    def range_to(self, end: 'YearMonth') -> Iterator['YearMonth']:
        """Generate range of months from self to end (inclusive)."""
        current = self
        while current <= end:
            yield current
            current = current.next_month()
    
    def format_ru(self) -> str:
        """Format in Russian."""
        months_ru = [
            'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
            'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
        ]
        return f"{months_ru[self.month - 1]} {self.year}"
    
    def format_short_ru(self) -> str:
        """Format short in Russian."""
        months_short_ru = [
            'янв', 'фев', 'мар', 'апр', 'май', 'июн',
            'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'
        ]
        return f"{months_short_ru[self.month - 1]} {self.year}"


def parse_year_month(value: str) -> YearMonth:
    """Parse year-month from various formats."""
    if not value:
        return YearMonth.current()
    
    # Try standard format first
    try:
        return YearMonth.from_string(value)
    except ValueError:
        pass
    
    # Try parsing as date
    try:
        parsed_date = datetime.strptime(value, '%Y-%m-%d').date()
        return YearMonth.from_date(parsed_date)
    except ValueError:
        pass
    
    raise ValueError(f"Cannot parse year-month: {value}")