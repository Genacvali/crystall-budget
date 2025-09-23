"""Domain events system."""
from typing import Dict, List, Callable, Any
from datetime import datetime
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class DomainEvent(ABC):
    """Base domain event class."""
    
    def __init__(self):
        self.timestamp = datetime.utcnow()
        self.event_id = id(self)
    
    @property
    @abstractmethod
    def event_type(self) -> str:
        """Event type identifier."""
        pass
    
    def to_dict(self) -> Dict:
        """Convert event to dictionary."""
        return {
            'event_type': self.event_type,
            'event_id': self.event_id,
            'timestamp': self.timestamp.isoformat(),
            'data': self._get_data()
        }
    
    @abstractmethod
    def _get_data(self) -> Dict:
        """Get event-specific data."""
        pass


# Budget Events
class ExpenseCreated(DomainEvent):
    """Event fired when expense is created."""
    
    def __init__(self, user_id: int, expense_id: int, category_id: int, amount: float, currency: str):
        super().__init__()
        self.user_id = user_id
        self.expense_id = expense_id
        self.category_id = category_id
        self.amount = amount
        self.currency = currency
    
    @property
    def event_type(self) -> str:
        return 'expense.created'
    
    def _get_data(self) -> Dict:
        return {
            'user_id': self.user_id,
            'expense_id': self.expense_id,
            'category_id': self.category_id,
            'amount': self.amount,
            'currency': self.currency
        }


class IncomeUpdated(DomainEvent):
    """Event fired when income is updated."""
    
    def __init__(self, user_id: int, income_id: int, source_name: str, amount: float, year: int, month: int):
        super().__init__()
        self.user_id = user_id
        self.income_id = income_id
        self.source_name = source_name
        self.amount = amount
        self.year = year
        self.month = month
    
    @property
    def event_type(self) -> str:
        return 'income.updated'
    
    def _get_data(self) -> Dict:
        return {
            'user_id': self.user_id,
            'income_id': self.income_id,
            'source_name': self.source_name,
            'amount': self.amount,
            'year': self.year,
            'month': self.month
        }


class CategoryCreated(DomainEvent):
    """Event fired when category is created."""
    
    def __init__(self, user_id: int, category_id: int, name: str, limit_type: str, value: float):
        super().__init__()
        self.user_id = user_id
        self.category_id = category_id
        self.name = name
        self.limit_type = limit_type
        self.value = value
    
    @property
    def event_type(self) -> str:
        return 'category.created'
    
    def _get_data(self) -> Dict:
        return {
            'user_id': self.user_id,
            'category_id': self.category_id,
            'name': self.name,
            'limit_type': self.limit_type,
            'value': self.value
        }


# Goals Events
class GoalCompleted(DomainEvent):
    """Event fired when savings goal is completed."""
    
    def __init__(self, user_id: int, goal_id: int, title: str, target_amount: float, currency: str):
        super().__init__()
        self.user_id = user_id
        self.goal_id = goal_id
        self.title = title
        self.target_amount = target_amount
        self.currency = currency
    
    @property
    def event_type(self) -> str:
        return 'goal.completed'
    
    def _get_data(self) -> Dict:
        return {
            'user_id': self.user_id,
            'goal_id': self.goal_id,
            'title': self.title,
            'target_amount': self.target_amount,
            'currency': self.currency
        }


class GoalProgressAdded(DomainEvent):
    """Event fired when progress is added to goal."""
    
    def __init__(self, user_id: int, goal_id: int, amount: float, new_total: float):
        super().__init__()
        self.user_id = user_id
        self.goal_id = goal_id
        self.amount = amount
        self.new_total = new_total
    
    @property
    def event_type(self) -> str:
        return 'goal.progress_added'
    
    def _get_data(self) -> Dict:
        return {
            'user_id': self.user_id,
            'goal_id': self.goal_id,
            'amount': self.amount,
            'new_total': self.new_total
        }


# Event Bus
class EventBus:
    """Simple synchronous event bus."""
    
    def __init__(self):
        self._handlers: Dict[str, List[Callable[[DomainEvent], None]]] = {}
    
    def subscribe(self, event_type: str, handler: Callable[[DomainEvent], None]) -> None:
        """Subscribe handler to event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.info(f"Subscribed handler {handler.__name__} to event {event_type}")
    
    def publish(self, event: DomainEvent) -> None:
        """Publish event to all subscribed handlers."""
        event_type = event.event_type
        
        if event_type not in self._handlers:
            logger.debug(f"No handlers for event {event_type}")
            return
        
        logger.info(f"Publishing event {event_type} (ID: {event.event_id})")
        
        for handler in self._handlers[event_type]:
            try:
                handler(event)
                logger.debug(f"Handler {handler.__name__} processed event {event_type}")
            except Exception as e:
                logger.error(f"Error in handler {handler.__name__} for event {event_type}: {e}")
    
    def get_handlers(self, event_type: str) -> List[Callable]:
        """Get handlers for event type."""
        return self._handlers.get(event_type, [])
    
    def clear_handlers(self, event_type: str = None) -> None:
        """Clear handlers for specific event type or all."""
        if event_type:
            self._handlers.pop(event_type, None)
            logger.info(f"Cleared handlers for event {event_type}")
        else:
            self._handlers.clear()
            logger.info("Cleared all event handlers")


# Global event bus instance
event_bus = EventBus()


# Event Handlers
def handle_cache_invalidation(event: DomainEvent) -> None:
    """Handle cache invalidation for budget events."""
    from app.core.caching import CacheManager
    
    event_data = event._get_data()
    user_id = event_data.get('user_id')
    
    if not user_id:
        return
    
    if event.event_type in ['expense.created', 'expense.updated', 'expense.deleted']:
        # Invalidate budget cache for current month
        from app.core.time import YearMonth
        current_month = YearMonth.current()
        CacheManager.invalidate_budget_cache(user_id, current_month)
        logger.info(f"Invalidated budget cache for user {user_id} due to {event.event_type}")
    
    elif event.event_type in ['income.updated', 'category.created', 'category.updated']:
        # Invalidate all budget cache for user
        CacheManager.invalidate_budget_cache(user_id)
        logger.info(f"Invalidated all budget cache for user {user_id} due to {event.event_type}")
    
    elif event.event_type in ['goal.completed', 'goal.progress_added']:
        # Invalidate goals cache
        CacheManager.invalidate_goals_cache(user_id)
        logger.info(f"Invalidated goals cache for user {user_id} due to {event.event_type}")


def handle_goal_completion_notification(event: GoalCompleted) -> None:
    """Handle goal completion notifications."""
    logger.info(f"🎉 Goal '{event.title}' completed by user {event.user_id}!")
    # TODO: Send actual notification (email, push, etc.)


def handle_budget_limit_warning(event: ExpenseCreated) -> None:
    """Handle budget limit warnings."""
    # TODO: Check if expense pushes category over limit and send warning
    logger.debug(f"Checking budget limits for user {event.user_id} after expense {event.expense_id}")


# Register default event handlers
def register_default_handlers():
    """Register default event handlers."""
    # Cache invalidation
    event_bus.subscribe('expense.created', handle_cache_invalidation)
    event_bus.subscribe('expense.updated', handle_cache_invalidation)
    event_bus.subscribe('expense.deleted', handle_cache_invalidation)
    event_bus.subscribe('income.updated', handle_cache_invalidation)
    event_bus.subscribe('category.created', handle_cache_invalidation)
    event_bus.subscribe('category.updated', handle_cache_invalidation)
    event_bus.subscribe('goal.completed', handle_cache_invalidation)
    event_bus.subscribe('goal.progress_added', handle_cache_invalidation)
    
    # Goal completion notifications
    event_bus.subscribe('goal.completed', handle_goal_completion_notification)
    
    # Budget warnings
    event_bus.subscribe('expense.created', handle_budget_limit_warning)