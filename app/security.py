"""Security headers and CSP policies."""

from flask import current_app, request


def set_security_headers(response):
    """Set security headers for all responses."""
    # Basic security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Referrer policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Content Security Policy
    if hasattr(current_app.config, 'csp_policy'):
        csp_policy = current_app.config.csp_policy
        if isinstance(csp_policy, list):
            response.headers['Content-Security-Policy'] = '; '.join(csp_policy)
        else:
            response.headers['Content-Security-Policy'] = csp_policy
    
    # HSTS for production HTTPS
    if current_app.config.get('HTTPS_MODE'):
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # Log security-relevant requests
    if request.path.startswith('/auth/') or request.path.startswith('/api/'):
        current_app.logger.info(
            f'{request.method} request to {request.path.replace("/auth/", "")} from {request.remote_addr}'
        )
    
    return response