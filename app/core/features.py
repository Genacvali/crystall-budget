"""Feature flag utilities - Stage 6: Simplified kill-switch only."""
from flask import current_app


def is_modal_system_enabled():
    """Check if unified modal system is enabled (kill-switch only after 100% rollout)."""
    return current_app.config.get('MODAL_SYSTEM_ENABLED', True)


# Template helper
def modal_system_config():
    """Return modal system config for templates."""
    return {
        'enabled': is_modal_system_enabled()
    }