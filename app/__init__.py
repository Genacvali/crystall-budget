from flask import Flask
from app.core.extensions import db, migrate, login_manager, csrf, cache
from app.core.config import get_config


def create_app(config_name=None):
    """Application factory pattern."""
    import os
    # Set template and static folders relative to project root
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
    static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    
    # Load configuration
    config = get_config(config_name)
    app.config.from_object(config)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    cache.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Пожалуйста, войдите в систему'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.modules.auth.models import User
        return User.query.get(int(user_id))
    
    # Register blueprints
    from app.modules.auth import auth_bp
    from app.modules.budget import budget_bp
    from app.modules.goals import goals_bp
    from app.api.v1 import api_v1_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(budget_bp)
    app.register_blueprint(goals_bp)
    app.register_blueprint(api_v1_bp)
    
    # Backward compatibility routes
    from flask import redirect, url_for
    
    @app.route('/set-theme', methods=['POST'])
    def set_theme_compat():
        """Backward compatibility redirect for set-theme endpoint."""
        from app.modules.auth.routes import set_theme
        return set_theme()
    
    # Import models for Alembic
    from app.modules.auth.models import User
    from app.modules.budget.models import Category, Expense, Income, CategoryRule, ExchangeRate  
    from app.modules.goals.models import SavingsGoal, SharedBudget, SharedBudgetMember
    
    # Register error handlers
    from app.core.errors import register_error_handlers
    register_error_handlers(app)
    
    # Register event handlers
    from app.core.events import register_default_handlers
    register_default_handlers()
    
    # Register CLI commands
    from app.core.cli import register_cli_commands
    register_cli_commands(app)
    
    # Register template filters
    from app.core.filters import register_filters
    register_filters(app)
    
    return app