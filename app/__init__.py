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
    from app.modules.issues import issues_bp
    from app.api.v1 import api_v1_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(budget_bp)
    app.register_blueprint(goals_bp)
    app.register_blueprint(issues_bp)
    app.register_blueprint(api_v1_bp)
    
    # Backward compatibility routes
    from flask import redirect, url_for
    
    @app.route('/set-theme', methods=['POST'])
    def set_theme_compat():
        """Backward compatibility redirect for set-theme endpoint."""
        from app.modules.auth.routes import set_theme
        return set_theme()
    
    # More backward compatibility routes
    @app.route('/update_profile', methods=['POST'])
    def update_profile_compat():
        """Backward compatibility redirect for update profile."""
        return redirect(url_for('auth.profile'))
    
    @app.route('/account_password', methods=['POST'])
    def account_password_compat():
        """Backward compatibility redirect for password change."""
        return redirect(url_for('auth.change_password'))
    
    @app.route('/add_goal', methods=['POST'])
    def add_goal_compat():
        """Backward compatibility redirect for add goal."""
        return redirect(url_for('goals.create_goal'))
    
    @app.route('/update_goal_progress/<int:goal_id>', methods=['POST'])
    def update_goal_progress_compat(goal_id):
        """Backward compatibility redirect for goal progress."""
        return redirect(url_for('goals.add_progress'))
    
    @app.route('/categories/update/<int:cat_id>', methods=['POST'])
    def categories_update_compat(cat_id):
        """Backward compatibility redirect for category update."""
        return redirect(url_for('budget.edit_category', category_id=cat_id))
    
    @app.route('/update_source_percentage/<int:cat_id>', methods=['POST'])
    def update_source_percentage_compat(cat_id):
        """Backward compatibility for source percentage update."""
        flash('Функция в разработке', 'info')
        return redirect(url_for('budget.categories'))
    
    @app.route('/remove_source_from_category/<int:cat_id>/<int:source_id>', methods=['POST'])
    def remove_source_from_category_compat(cat_id, source_id):
        """Backward compatibility for removing source from category."""
        flash('Функция в разработке', 'info')
        return redirect(url_for('budget.categories'))
    
    @app.route('/add_source_to_category/<int:cat_id>', methods=['POST'])
    def add_source_to_category_compat(cat_id):
        """Backward compatibility for adding source to category."""
        flash('Функция в разработке', 'info')
        return redirect(url_for('budget.categories'))
    
    @app.route('/toggle_multi_source/<int:cat_id>', methods=['POST'])
    def toggle_multi_source_compat(cat_id):
        """Backward compatibility for toggling multi-source mode."""
        flash('Функция в разработке', 'info')
        return redirect(url_for('budget.categories'))
    
    @app.route('/favicon.ico')
    def favicon():
        """Serve favicon from static folder."""
        return redirect(url_for('static', filename='favicon.ico'))
    
    @app.route('/healthz')
    def health_check():
        """Health check endpoint for monitoring."""
        try:
            # Проверяем подключение к БД
            from app.core.extensions import db
            from sqlalchemy import text
            with db.engine.connect() as connection:
                connection.execute(text('SELECT 1'))
            
            # Проверяем что миграции актуальны
            from flask_migrate import current, heads
            current_rev = current()
            head_rev = heads()
            
            if current_rev != head_rev:
                return {'status': 'error', 'message': 'Database migrations not up to date'}, 500
                
            return {'status': 'ok', 'message': 'Application healthy'}, 200
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}, 500
    
    # Import models for Alembic
    from app.modules.auth.models import User
    from app.modules.budget.models import Category, Expense, Income, CategoryRule, ExchangeRate, IncomeSource  
    from app.modules.goals.models import SavingsGoal, SharedBudget, SharedBudgetMember
    from app.modules.issues.models import Issue, IssueComment
    
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
    
    # Initialize asset helpers
    from app.core.assets import init_asset_helpers
    init_asset_helpers(app)
    
    # Initialize diagnostics
    from app.core.diagnostics import init_diagnostics
    init_diagnostics(app)
    
    return app