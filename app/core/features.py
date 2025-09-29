"""Feature flag utilities for safe rollouts."""
import hashlib
from flask import current_app, session


def is_modal_system_enabled():
    """Check if unified modal system is enabled for current user."""
    if not current_app.config.get('MODAL_SYSTEM_ENABLED', True):
        return False
    
    # Full rollout (100%)
    canary_pct = current_app.config.get('MODAL_SYSTEM_CANARY_PCT', 100)
    if canary_pct >= 100:
        return True
    
    # Canary testing based on user ID hash
    user_id = session.get('user_id')
    if not user_id:
        return False  # Anonymous users get legacy system
        
    # Deterministic hash-based canary selection  
    user_hash = hashlib.md5(str(user_id).encode()).hexdigest()
    user_bucket = int(user_hash[:2], 16) % 100  # 0-99
    
    return user_bucket < canary_pct


def is_modal_system_debug_enabled():
    """Check if modal system debug logging is enabled."""
    return current_app.config.get('MODAL_SYSTEM_DEBUG', False)


# Template helper
def modal_system_config():
    """Return modal system config for templates."""
    return {
        'enabled': is_modal_system_enabled(),
        'debug': is_modal_system_debug_enabled()
    }