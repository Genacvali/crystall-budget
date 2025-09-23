"""Caching utilities."""
from functools import wraps
from flask import request
from flask_login import current_user
from app.core.extensions import cache
from app.core.time import YearMonth


def make_cache_key(*args, **kwargs):
    """Create cache key from arguments."""
    key_parts = []
    
    # Add user context if available
    if current_user and current_user.is_authenticated:
        key_parts.append(f"user:{current_user.id}")
    
    # Add URL context for view functions
    if request:
        key_parts.append(f"url:{request.endpoint}")
    
    # Add provided arguments
    for arg in args:
        if isinstance(arg, YearMonth):
            key_parts.append(f"ym:{arg}")
        else:
            key_parts.append(str(arg))
    
    for key, value in kwargs.items():
        key_parts.append(f"{key}:{value}")
    
    return ":".join(key_parts)


def cached_per_user(timeout=300):
    """Cache decorator that includes user ID in cache key."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user or not current_user.is_authenticated:
                return f(*args, **kwargs)
            
            cache_key = make_cache_key(f.__name__, *args, **kwargs)
            result = cache.get(cache_key)
            
            if result is None:
                result = f(*args, **kwargs)
                cache.set(cache_key, result, timeout=timeout)
            
            return result
        return decorated_function
    return decorator


def cached_per_user_month(timeout=300):
    """Cache decorator for user+month specific data."""
    def decorator(f):
        @wraps(f)
        def decorated_function(user_id, year_month, *args, **kwargs):
            cache_key = make_cache_key(f.__name__, f"user:{user_id}", f"ym:{year_month}", *args, **kwargs)
            result = cache.get(cache_key)
            
            if result is None:
                result = f(user_id, year_month, *args, **kwargs)
                cache.set(cache_key, result, timeout=timeout)
            
            return result
        return decorated_function
    return decorator


def invalidate_user_cache(user_id, year_month=None):
    """Invalidate cache for specific user and optionally specific month."""
    # Note: SimpleCache doesn't support pattern-based deletion
    # For production, consider Redis with pattern deletion
    cache.clear()  # For now, clear entire cache


class CacheManager:
    """Centralized cache management."""
    
    @staticmethod
    def invalidate_budget_cache(user_id, year_month=None):
        """Invalidate budget-related cache for user."""
        invalidate_user_cache(user_id, year_month)
    
    @staticmethod
    def invalidate_goals_cache(user_id):
        """Invalidate goals-related cache for user.""" 
        invalidate_user_cache(user_id)
    
    @staticmethod
    def get_month_snapshot_key(user_id, year_month):
        """Get cache key for month snapshot."""
        return make_cache_key("month_snapshot", f"user:{user_id}", f"ym:{year_month}")
    
    @staticmethod
    def set_month_snapshot(user_id, year_month, data, timeout=300):
        """Cache month snapshot."""
        key = CacheManager.get_month_snapshot_key(user_id, year_month)
        cache.set(key, data, timeout=timeout)
    
    @staticmethod
    def get_month_snapshot(user_id, year_month):
        """Get cached month snapshot."""
        key = CacheManager.get_month_snapshot_key(user_id, year_month)
        return cache.get(key)