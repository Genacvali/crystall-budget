from flask import Flask, render_template
from app.core.extensions import db, migrate, login_manager, csrf, cache
from app.core.config import get_config
from app.core.config import config_by_name
from app.core.monitoring import monitor_modal_performance
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
    # SQLite-specific migration settings
    migrate.init_app(
        app,
        db,
        render_as_batch=True,  # Required for SQLite ALTER operations
        compare_type=True,  # Detect column type changes
        compare_server_default=True  # Detect default value changes
    )
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
    @monitor_modal_performance('goal_add')
    def goal_add_modal():
        """Return goal add modal content."""
        from flask_login import login_required, current_user
        from flask import session
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        return render_template('components/modals/goal_add.html', 
                             currency_symbol='₽')

    @app.route('/modals/goal/<int:goal_id>/edit')
    @monitor_modal_performance('goal_edit')
    def goal_edit_modal(goal_id):
        """Return goal edit modal content."""
        from flask_login import login_required, current_user
        from flask import session
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        user_id = current_user.id
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
        
        user_id = current_user.id
        from app.modules.goals.models import SavingsGoal
        goal = SavingsGoal.query.filter_by(id=goal_id, user_id=user_id).first_or_404()
        
        return render_template('components/modals/goal_topup.html', 
                             goal=goal,
                             currency_symbol='₽')
    
    # Modal routes for settings
    @app.route('/modals/settings/profile')
    def settings_profile_modal():
        """Return profile settings modal content."""
        from flask_login import current_user
        from flask import session
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        from app.modules.auth.models import User
        user = User.query.get(current_user.id)
        if not user:
            return redirect(url_for('auth.logout'))
        
        return render_template('components/modals/settings_profile.html', 
                             user=user)

    @app.route('/modals/settings/password')
    def settings_password_modal():
        """Return password change modal content."""
        from flask_login import current_user
        from flask import session
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        from app.modules.auth.models import User
        user = User.query.get(current_user.id)
        if not user:
            return redirect(url_for('auth.logout'))
        
        return render_template('components/modals/settings_password.html', 
                             user=user)

    @app.route('/modals/settings/interface')
    def settings_interface_modal():
        """Return interface settings modal content."""
        from flask_login import current_user
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        return render_template('components/modals/settings_interface.html')

    @app.route('/modals/settings/export')
    def settings_export_modal():
        """Return data export modal content."""
        from flask_login import current_user
        from flask import session
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        # Get user statistics
        user_id = current_user.id
        from app.core.extensions import db
        from sqlalchemy import text
        
        stats = {}
        try:
            # Get counts for user data
            result = db.session.execute(text("""
                SELECT 
                    (SELECT COUNT(*) FROM expenses WHERE user_id = :user_id) as expenses_count,
                    (SELECT COUNT(*) FROM income WHERE user_id = :user_id) as income_count,
                    (SELECT COUNT(*) FROM categories WHERE user_id = :user_id) as categories_count,
                    (SELECT COUNT(*) FROM savings_goals WHERE user_id = :user_id) as goals_count
            """), {'user_id': user_id}).fetchone()
            
            if result:
                stats = {
                    'expenses_count': result.expenses_count,
                    'income_count': result.income_count, 
                    'categories_count': result.categories_count,
                    'goals_count': result.goals_count
                }
        except Exception:
            stats = {'expenses_count': 0, 'income_count': 0, 'categories_count': 0, 'goals_count': 0}
        
        return render_template('components/modals/settings_export.html', 
                             stats=stats)

    @app.route('/modals/settings/import')
    def settings_import_modal():
        """Return data import modal content."""
        from flask_login import current_user
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        return render_template('components/modals/settings_import.html')

    @app.route('/modals/settings/clear-data')
    def settings_clear_data_modal():
        """Return clear data modal content."""
        from flask_login import current_user
        from flask import session
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        # Get user statistics
        user_id = current_user.id
        from app.core.extensions import db
        from sqlalchemy import text
        
        stats = {}
        try:
            result = db.session.execute(text("""
                SELECT 
                    (SELECT COUNT(*) FROM expenses WHERE user_id = :user_id) as expenses_count,
                    (SELECT COUNT(*) FROM income WHERE user_id = :user_id) as income_count,
                    (SELECT COUNT(*) FROM categories WHERE user_id = :user_id) as categories_count,
                    (SELECT COUNT(*) FROM savings_goals WHERE user_id = :user_id) as goals_count
            """), {'user_id': user_id}).fetchone()
            
            if result:
                stats = {
                    'expenses_count': result.expenses_count,
                    'income_count': result.income_count,
                    'categories_count': result.categories_count,
                    'goals_count': result.goals_count
                }
        except Exception:
            stats = {'expenses_count': 0, 'income_count': 0, 'categories_count': 0, 'goals_count': 0}
        
        return render_template('components/modals/settings_clear_data.html', 
                             stats=stats)

    @app.route('/modals/settings/delete-account')
    def settings_delete_account_modal():
        """Return delete account modal content."""
        from flask_login import current_user
        from flask import session
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        from app.modules.auth.models import User
        user = User.query.get(current_user.id)
        if not user:
            return redirect(url_for('auth.logout'))
        
        # Get user statistics
        user_id = current_user.id
        from app.core.extensions import db
        from sqlalchemy import text
        
        stats = {}
        try:
            result = db.session.execute(text("""
                SELECT 
                    (SELECT COUNT(*) FROM expenses WHERE user_id = :user_id) as expenses_count,
                    (SELECT COUNT(*) FROM income WHERE user_id = :user_id) as income_count,
                    (SELECT COUNT(*) FROM categories WHERE user_id = :user_id) as categories_count,
                    (SELECT COUNT(*) FROM savings_goals WHERE user_id = :user_id) as goals_count
            """), {'user_id': user_id}).fetchone()
            
            if result:
                stats = {
                    'expenses_count': result.expenses_count,
                    'income_count': result.income_count,
                    'categories_count': result.categories_count,
                    'goals_count': result.goals_count
                }
        except Exception:
            stats = {'expenses_count': 0, 'income_count': 0, 'categories_count': 0, 'goals_count': 0}
        
        return render_template('components/modals/settings_delete_account.html', 
                             user=user,
                             stats=stats)
    
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
    
    @app.route('/modal-test')
    def modal_test():
        """Modal testing page for QA."""
        return render_template('modal_test.html')
    
    @app.route('/qa-modal-test')
    def qa_modal_test():
        """QA testing page for unified modal system."""
        return render_template('modal_qa_test.html')
    
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
    
    @app.route('/monitoring/modal-system')
    def monitoring_dashboard():
        """Modal system monitoring dashboard."""
        from flask_login import current_user
        from app.core.monitoring import create_monitoring_dashboard_data, log_bundle_usage
        
        # Only accessible to authenticated users
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        # Log this bundle usage
        log_bundle_usage()
        
        dashboard_data = create_monitoring_dashboard_data()
        return render_template('monitoring/modal_dashboard.html', 
                             data=dashboard_data)
    
    @app.route('/monitoring/modal-system/api')
    def monitoring_api():
        """JSON API for modal system monitoring."""
        from flask_login import current_user
        from flask import jsonify
        from app.core.monitoring import create_monitoring_dashboard_data
        
        # Only accessible to authenticated users  
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
            
        return jsonify(create_monitoring_dashboard_data())
    
    @app.route('/api/telemetry/modal', methods=['POST'])
    def modal_telemetry_api():
        """API endpoint for modal telemetry collection."""
        from flask_login import current_user
        from flask import jsonify, request
        from app.core.telemetry import ModalTelemetry
        
        # Only for authenticated users
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        
        try:
            data = request.get_json()
            if not data or 'event_type' not in data or 'modal_name' not in data:
                return jsonify({'error': 'Missing required fields'}), 400
            
            ModalTelemetry.record_modal_event(
                event_type=data['event_type'],
                modal_name=data['modal_name'],
                data=data.get('data', {}),
                user_id=session.get('user_id')
            )
            
            return jsonify({'status': 'success'})
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
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
    
    # Register template context processors  
    from app.core.features import modal_system_config
    from app.core.bundles import bundle_config
    from app.core.monitoring import log_bundle_usage
    
    @app.context_processor
    def inject_feature_flags():
        # Log bundle usage for monitoring
        try:
            log_bundle_usage()
        except Exception:
            pass  # Don't break page rendering for monitoring failures

        return {
            'modal_system_config': modal_system_config,
            'bundle_config': bundle_config
        }

    @app.context_processor
    def inject_user_currency():
        """Inject user currency into template context."""
        from flask import session
        from flask_login import current_user

        # Get currency from session or user object
        currency = session.get('currency', 'RUB')

        # If logged in, try to get from current_user
        if current_user and current_user.is_authenticated:
            try:
                if hasattr(current_user, 'default_currency') and current_user.default_currency:
                    currency = current_user.default_currency
            except:
                pass

        # Currency symbol mapping
        currency_symbols = {
            'RUB': '₽',
            'USD': '$',
            'EUR': '€',
            'KZT': '₸',
            'BYN': 'Br',
            'AMD': '֏',
            'GEL': '₾'
        }

        return {
            'user_currency': currency,
            'currency_symbol': currency_symbols.get(currency, currency)
        }
    
    # Initialize asset helpers
    from app.core.assets import init_asset_helpers
    init_asset_helpers(app)
    
    # Initialize diagnostics
    from app.core.diagnostics import init_diagnostics
    init_diagnostics(app)
    
    return app

