"""Asset bundle management for feature flag rollouts."""
from flask import current_app
from app.core.features import is_modal_system_enabled


# Bundle definitions
BUNDLES = {
    'legacy': {
        'css': [
            'css/clean-theme.css',
            'css/app.css',
            'css/accessibility.css',
            'css/theme-ff-light.css',
            'css/nav-ff.css',
            'css/design-tokens.css',
        ],
        'js': [
            'js/app.js',
            'js/accessibility.js', 
            'js/nav-ff.js',
        ]
    },
    'unified': {
        'css': [
            'css/clean-theme.css',
            'css/app.css',
            'css/accessibility.css',
            'css/theme-ff-light.css',
            'css/nav-ff.css',
            'css/design-tokens.css',
            'css/components/modal.css',
        ],
        'js': [
            'js/app.js',
            'js/accessibility.js',
            'js/nav-ff.js',
            'js/modals.js',
        ]
    }
}


def get_bundle_name():
    """Get the appropriate bundle name based on feature flags."""
    if is_modal_system_enabled():
        return 'unified'
    return 'legacy'


def get_css_bundle():
    """Get CSS files for the current bundle."""
    bundle_name = get_bundle_name()
    return BUNDLES[bundle_name]['css']


def get_js_bundle():
    """Get JS files for the current bundle."""
    bundle_name = get_bundle_name()
    return BUNDLES[bundle_name]['js']


def bundle_config():
    """Template helper for bundle information."""
    bundle_name = get_bundle_name()
    return {
        'name': bundle_name,
        'css': get_css_bundle(),
        'js': get_js_bundle(),
        'modal_enabled': bundle_name == 'unified'
    }