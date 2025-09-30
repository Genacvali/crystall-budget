"""Asset bundle management - Stage 6: Unified bundle only (with kill-switch)."""
from app.core.features import is_modal_system_enabled


# Standard bundle (unified modal system is default)
STANDARD_BUNDLE = {
    'css': [
        'css/clean-theme.css',
        'css/app.css',
        'css/accessibility.css',
        'css/theme-ff-light.css',
        'css/nav-ff.css',
        'css/design-tokens.css',
        'css/components/modal.css',
        'css/modals.css',  # New unified modal styles
    ],
    'js': [
        'js/app.js',
        'js/accessibility.js',
        'js/nav-ff.js',
        'js/modals.js',
    ]
}

# Emergency fallback bundle (if modal system is disabled)
FALLBACK_BUNDLE = {
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
}


def get_css_bundle():
    """Get CSS files for the current bundle."""
    if is_modal_system_enabled():
        return STANDARD_BUNDLE['css']
    return FALLBACK_BUNDLE['css']


def get_js_bundle():
    """Get JS files for the current bundle."""
    if is_modal_system_enabled():
        return STANDARD_BUNDLE['js']
    return FALLBACK_BUNDLE['js']


def bundle_config():
    """Template helper for bundle information."""
    modal_enabled = is_modal_system_enabled()
    return {
        'css': get_css_bundle(),
        'js': get_js_bundle(),
        'modal_enabled': modal_enabled
    }