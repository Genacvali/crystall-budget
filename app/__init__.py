"""Crystal Budget Flask Application Factory."""

import os
from datetime import timedelta
from flask import Flask, session

from .config import config_map
from .extensions import setup_logging
from .security import set_security_headers
from .db import (init_db, ensure_new_tables, migrate_income_to_daily_if_needed,
                 ensure_income_sources_tables, add_source_id_column_if_missing,
                 add_category_type_column_if_missing, add_currency_columns_if_missing,
                 add_profile_columns_if_missing)
from .services.currency import inject_currency


def create_app(config_name=None):
    """Application factory."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app = Flask(__name__, 
                static_folder="../static", 
                template_folder="templates")
    
    # Load configuration
    config_class = config_map.get(config_name, config_map['default'])
    app.config.from_object(config_class)
    
    # Create upload directory
    os.makedirs(app.config['AVATAR_DIR'], exist_ok=True)
    
    # Setup session configuration
    app.permanent_session_lifetime = app.config['PERMANENT_SESSION_LIFETIME']
    
    if app.config['HTTPS_MODE']:
        app.config['SESSION_COOKIE_SECURE'] = True
        app.config['SESSION_COOKIE_NAME'] = 'cbsid'  # Hide Flask usage in production
    else:
        app.config['SESSION_COOKIE_NAME'] = 'session'
    
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    # Setup logging
    setup_logging(app)
    
    # Security headers
    app.after_request(set_security_headers)
    
    # Make sessions permanent by default
    @app.before_request
    def make_session_permanent():
        session.permanent = True
    
    # Register blueprints
    from .blueprints.auth.routes import bp as auth_bp
    from .blueprints.dashboard.routes import bp as dashboard_bp
    from .blueprints.expenses.routes import bp as expenses_bp
    from .blueprints.income.routes import bp as income_bp
    from .blueprints.categories.routes import bp as categories_bp
    from .blueprints.sources.routes import bp as sources_bp
    from .blueprints.goals.routes import bp as goals_bp
    from .blueprints.shared.routes import bp as shared_bp
    from .api.exchange import bp as api_exchange_bp
    from .api.analytics import bp as api_analytics_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(expenses_bp, url_prefix='/expenses')
    app.register_blueprint(income_bp, url_prefix='/income')
    app.register_blueprint(categories_bp, url_prefix='/categories')
    app.register_blueprint(sources_bp, url_prefix='/sources')
    app.register_blueprint(goals_bp, url_prefix='/goals')
    app.register_blueprint(shared_bp, url_prefix='/shared')
    app.register_blueprint(api_exchange_bp, url_prefix='/api')
    app.register_blueprint(api_analytics_bp, url_prefix='/api')
    
    # Root redirect
    @app.route('/')
    def root():
        from flask import redirect, url_for
        if session.get('user_id'):
            return redirect(url_for('dashboard.index'))
        return redirect(url_for('auth.login'))
    
    # Currency context processor
    app.context_processor(inject_currency)
    
    # Register template filters
    from .filters import register_filters
    register_filters(app)
    
    # Database initialization (idempotent)
    with app.app_context():
        init_db()
        ensure_new_tables()
        ensure_income_sources_tables()
        migrate_income_to_daily_if_needed()
        add_source_id_column_if_missing()
        add_category_type_column_if_missing()
        add_currency_columns_if_missing()
        add_profile_columns_if_missing()
    
    return app