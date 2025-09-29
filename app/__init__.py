from flask import Flask
from app.core.extensions import db, migrate, login_manager, csrf, cache
from app.core.config import get_config
from app.core.config import config_by_name
import os
from typing import Optional


def create_app(config_name: Optional[str] = None):
    """Application factory pattern."""
    import os
    import logging
    from logging.handlers import RotatingFileHandler
    
    if config_name is None:
        config_name = os.getenv("APP_CONFIG", "production")
    
    # Set template and static folders relative to project root
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
    static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))
    logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'logs'))
    
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    
    # Load configuration
    app.config.from_object(config_by_name[config_name])
    
    # Setup logging to files
    if not app.debug and not app.testing:
        # Create logs directory if it doesn't exist
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
        
        # Main application log
        file_handler = RotatingFileHandler(
            os.path.join(logs_dir, 'crystalbudget.log'),
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        # Error log
        error_handler = RotatingFileHandler(
            os.path.join(logs_dir, 'errors.log'),
            maxBytes=10240000,
            backupCount=5
        )
        error_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        error_handler.setLevel(logging.ERROR)
        app.logger.addHandler(error_handler)
        
        # Set log level from config
        log_level = app.config.get('LOG_LEVEL', 'INFO')
        app.logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        
        app.logger.info(f'CrystalBudget startup - Config: {config_name}')
    
    # For self-checking (temporary)
    app.logger.warning(
        f"Config={config_name} TESTING={app.config.get('TESTING')} "
        f"CSRF={app.config.get('WTF_CSRF_ENABLED')}"
    )
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    cache.init_app(app)
    
    # Configure login manager (skip for testing)
    if not app.config.get('LOGIN_DISABLED', False):
        login_manager.login_view = 'auth.login'
        login_manager.login_message = 'Пожалуйста, войдите в систему'
        login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.modules.auth.models import User
        return User.query.get(int(user_id))
    
    # Test mode user loader override
    if app.config.get('TESTING', False):
        @login_manager.request_loader
        def load_user_from_request(request):
            """Auto-authenticate in testing mode."""
            from app.modules.auth.models import User
            # Return a mock test user (create if doesn't exist)
            test_user = User.query.filter_by(telegram_id=12345).first()
            if not test_user:
                test_user = User(
                    name='Test User',
                    telegram_id=12345,
                    auth_type='telegram',
                    currency='RUB'
                )
                db.session.add(test_user)
                try:
                    db.session.commit()
                except:
                    db.session.rollback()
            return test_user
    
    # Register blueprints
    from app.modules.auth import auth_bp
    from app.modules.budget import budget_bp
    from app.modules.goals import goals_bp
    from app.modules.issues import issues_bp
    from app.api.v1 import api_v1_bp
    
    # Exempt API from CSRF protection
    csrf.exempt(api_v1_bp)
    
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
    
    # Modal routes for goals
    @app.route('/modals/goal/add')
    def goal_add_modal():
        """Return goal add modal content."""
        from flask_login import login_required, current_user
        from flask import session
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        return render_template('components/modals/goal_add.html', 
                             currency_symbol='₽')

    @app.route('/modals/goal/<int:goal_id>/edit')
    def goal_edit_modal(goal_id):
        """Return goal edit modal content."""
        from flask_login import login_required, current_user
        from flask import session
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        user_id = session['user_id']
        from app.modules.goals.models import SavingsGoal
        goal = SavingsGoal.query.filter_by(id=goal_id, user_id=user_id).first_or_404()
        
        return render_template('components/modals/goal_edit.html', 
                             goal=goal,
                             currency_symbol='₽')

    @app.route('/modals/goal/<int:goal_id>/topup')
    def goal_topup_modal(goal_id):
        """Return goal topup modal content."""
        from flask_login import login_required, current_user
        from flask import session
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        user_id = session['user_id']
        from app.modules.goals.models import SavingsGoal
        goal = SavingsGoal.query.filter_by(id=goal_id, user_id=user_id).first_or_404()
        
        return render_template('components/modals/goal_topup.html', 
                             goal=goal,
                             currency_symbol='₽')
    
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

