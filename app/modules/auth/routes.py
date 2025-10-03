"""Auth module routes."""
from flask import render_template, request, redirect, url_for, flash, session, current_app, abort, jsonify
from flask_login import login_required, current_user
from app.core.extensions import db
from .service import AuthService
from .schemas import LoginForm, RegisterForm, ChangePasswordForm, ProfileForm, TelegramAuthData
from .models import User
from . import auth_bp


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page."""
    if request.method == 'GET':
        # Check for Telegram auth data
        telegram_data = {}
        for key in ['id', 'first_name', 'last_name', 'username', 'photo_url', 'auth_date', 'hash']:
            if key in request.args:
                telegram_data[key] = request.args[key]
        
        if telegram_data.get('id'):
            # Telegram login attempt
            bot_token = current_app.config.get('TELEGRAM_BOT_TOKEN')
            if not bot_token:
                flash("Telegram авторизация не настроена", "error")
                return render_template('auth/login.html', form=LoginForm())
            
            user = AuthService.authenticate_telegram(telegram_data, bot_token)
            if user:
                AuthService.login_user(user)
                return redirect(url_for('budget.dashboard'))
            else:
                flash("Ошибка авторизации Telegram. Попробуйте еще раз", "error")
    
    # Email login
    form = LoginForm()
    if form.validate_on_submit():
        user = AuthService.authenticate_email(form.email.data, form.password.data)
        if user:
            AuthService.login_user(user)
            next_page = request.args.get('next')
            # Validate next_page to prevent open redirect attacks
            if next_page and next_page.startswith('/') and not next_page.startswith('//'):
                return redirect(next_page)
            return redirect(url_for('budget.dashboard'))
        else:
            flash('Неверный email или пароль', 'error')
    
    return render_template('auth/login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])  
def register():
    """Registration page."""
    if request.method == 'GET':
        # Check for Telegram registration
        telegram_data = {}
        for key in ['id', 'first_name', 'last_name', 'username', 'photo_url', 'auth_date', 'hash']:
            if key in request.args:
                telegram_data[key] = request.args[key]
        
        if telegram_data.get('id'):
            # Telegram registration attempt
            bot_token = current_app.config.get('TELEGRAM_BOT_TOKEN')
            if not bot_token:
                flash("Telegram авторизация не настроена", "error")
                return render_template('auth/register.html', form=RegisterForm())
            
            user = AuthService.authenticate_telegram(telegram_data, bot_token)
            if user:
                AuthService.login_user(user)
                return redirect(url_for('budget.dashboard'))
            else:
                flash("Ошибка авторизации Telegram. Попробуйте еще раз", "error")
    
    # Email registration
    form = RegisterForm()
    if form.validate_on_submit():
        user = AuthService.register_email(
            form.email.data,
            form.name.data,
            form.password.data
        )
        if user:
            AuthService.login_user(user)
            flash('Регистрация успешна!', 'success')
            return redirect(url_for('budget.dashboard'))
    
    return render_template('auth/register.html', form=form)


@auth_bp.route('/logout')
def logout():
    """Logout user."""
    AuthService.logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/telegram')
def telegram_auth():
    """Telegram Widget authentication endpoint."""
    args = request.args
    
    # Validate required parameters
    if not args.get('id') or not args.get('auth_date'):
        current_app.logger.warning('Telegram auth missing required parameters')
        abort(403)
    
    bot_token = current_app.config.get('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        current_app.logger.error('TELEGRAM_BOT_TOKEN not configured')
        abort(403)
    
    # Convert args to dict for processing
    telegram_data = dict(args)
    
    user = AuthService.authenticate_telegram(telegram_data, bot_token)
    if user:
        AuthService.login_user(user)
        return redirect(url_for('budget.dashboard'))
    else:
        flash("Ошибка авторизации Telegram", "error")
        return redirect(url_for('auth.login'))


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page."""
    user = User.query.get(session['user_id'])
    if not user:
        flash('Пользователь не найден', 'error')
        return redirect(url_for('auth.logout'))
    
    form = ProfileForm(obj=user)
    
    if form.validate_on_submit():
        preferences = {
            'name': form.name.data,
            'theme': form.theme.data,
            'currency': form.currency.data,
            'timezone': form.timezone.data
        }
        
        if AuthService.update_user_preferences(user, preferences):
            flash('Профиль обновлен', 'success')
            return redirect(url_for('auth.profile'))
    
    return render_template('auth/profile.html', form=form, user=user)


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change password page."""
    user = User.query.get(session['user_id'])
    if not user or user.is_telegram_user:
        flash('Изменение пароля недоступно для Telegram пользователей', 'error')
        return redirect(url_for('auth.profile'))
    
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        if AuthService.change_password(user, form.current_password.data, form.new_password.data):
            flash('Пароль изменен', 'success')
            return redirect(url_for('auth.profile'))
    
    return render_template('auth/change_password.html', form=form)


@auth_bp.route('/set-theme', methods=['POST'])
@login_required
def set_theme():
    """Set user theme preference."""
    data = request.get_json(silent=True) or {}
    theme = (data.get("theme") or "").lower()
    if theme not in ("light", "dark"):
        return jsonify({"ok": False, "error": "bad theme"}), 400
    session["theme"] = theme
    
    # Save to database if user exists
    try:
        user = User.query.get(session['user_id'])
        if user:
            # Update user theme (assumes theme column exists via migration)
            user.theme = theme
            db.session.commit()
    except Exception:
        pass  # Continue even if DB update fails
    
    return jsonify({"ok": True})


# Settings processing routes
@auth_bp.route('/settings/profile', methods=['POST'])
@login_required
def settings_save_profile():
    """Save profile settings from modal."""
    try:
        user = User.query.get(session['user_id'])
        if not user:
            flash('Пользователь не найден', 'error')
            return redirect(url_for('auth.logout'))

        # Get form data
        name = request.form.get('name', '').strip()
        currency = request.form.get('currency', 'RUB')
        timezone = request.form.get('timezone', 'UTC')

        # Validate name
        if not name or len(name) < 2:
            flash('Имя должно быть не менее 2 символов', 'error')
            return redirect(url_for('auth.settings'))

        # Validate currency
        allowed_currencies = ['RUB', 'USD', 'EUR', 'KZT', 'BYN', 'AMD', 'GEL']
        if currency not in allowed_currencies:
            currency = 'RUB'

        # Update user data
        user.name = name
        user.default_currency = currency
        user.timezone = timezone

        db.session.commit()

        # Update session
        session['user_name'] = name
        session['currency'] = currency

        current_app.logger.info(f'Profile updated for user ID: {user.id} - currency: {currency}')
        flash('Профиль успешно обновлен', 'success')
        return redirect(url_for('auth.settings'))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving profile settings: {e}")
        flash('Ошибка сохранения профиля', 'error')
        return redirect(url_for('auth.settings'))


@auth_bp.route('/settings/interface', methods=['POST'])
@login_required
def settings_save_interface():
    """Save interface settings."""
    try:
        user = User.query.get(session['user_id'])
        if not user:
            flash('Пользователь не найден', 'error')
            return redirect(url_for('auth.logout'))

        # Get form data
        theme = request.form.get('theme', 'light')
        language = request.form.get('language', 'ru')
        density = request.form.get('density', 'normal')

        # Save theme to session and database
        if theme in ['light', 'dark', 'auto']:
            session['theme'] = theme
            user.theme = theme

        # Save other preferences (would need user preferences table/fields)
        # For now just save theme
        db.session.commit()

        flash('Настройки интерфейса сохранены', 'success')
        return redirect(url_for('auth.settings'))

    except Exception as e:
        current_app.logger.error(f"Error saving interface settings: {e}")
        flash('Ошибка сохранения настроек', 'error')
        return redirect(url_for('auth.settings'))


@auth_bp.route('/settings/export', methods=['POST'])
@login_required  
def settings_export_data():
    """Export user data."""
    try:
        user_id = session['user_id']
        export_format = request.form.get('format', 'json')
        
        # This is a placeholder - would need actual export implementation
        flash('Экспорт данных в разработке', 'info')
        return redirect(url_for('auth.settings'))
        
    except Exception as e:
        current_app.logger.error(f"Error exporting data: {e}")
        flash('Ошибка экспорта данных', 'error')
        return redirect(url_for('auth.settings'))


@auth_bp.route('/settings/import', methods=['POST'])
@login_required
def settings_import_data():
    """Import user data."""
    try:
        # This is a placeholder - would need actual import implementation
        flash('Импорт данных в разработке', 'info')
        return redirect(url_for('auth.settings'))
        
    except Exception as e:
        current_app.logger.error(f"Error importing data: {e}")
        flash('Ошибка импорта данных', 'error')
        return redirect(url_for('auth.settings'))


@auth_bp.route('/settings/clear-data', methods=['POST'])
@login_required
def settings_clear_data():
    """Clear user data."""
    try:
        user_id = session['user_id']
        confirmation = request.form.get('confirmation', '')
        
        if confirmation != 'УДАЛИТЬ':
            flash('Неверное подтверждение', 'error')
            return redirect(url_for('auth.settings'))
        
        # This is a placeholder - would need actual data clearing implementation
        flash('Очистка данных в разработке', 'info')
        return redirect(url_for('auth.settings'))
        
    except Exception as e:
        current_app.logger.error(f"Error clearing data: {e}")
        flash('Ошибка очистки данных', 'error')
        return redirect(url_for('auth.settings'))


@auth_bp.route('/settings/delete-account', methods=['POST'])
@login_required
def settings_delete_account():
    """Delete user account."""
    try:
        user = User.query.get(session['user_id'])
        if not user:
            flash('Пользователь не найден', 'error')
            return redirect(url_for('auth.logout'))
        
        # Validate confirmations
        name_confirmation = request.form.get('name_confirmation', '')
        deletion_confirmation = request.form.get('deletion_confirmation', '')
        
        if name_confirmation != user.name:
            flash('Неверное подтверждение имени', 'error')
            return redirect(url_for('auth.settings'))
            
        if deletion_confirmation != 'УДАЛИТЬ АККАУНТ':
            flash('Неверное подтверждение удаления', 'error')
            return redirect(url_for('auth.settings'))
        
        # For email users, check password
        if user.auth_type == 'email':
            password_confirmation = request.form.get('password_confirmation', '')
            if not AuthService.verify_password(user, password_confirmation):
                flash('Неверный пароль', 'error')
                return redirect(url_for('auth.settings'))
        
        # This is a placeholder - would need actual account deletion implementation
        flash('Удаление аккаунта в разработке', 'info')
        return redirect(url_for('auth.settings'))
        
    except Exception as e:
        current_app.logger.error(f"Error deleting account: {e}")
        flash('Ошибка удаления аккаунта', 'error')
        return redirect(url_for('auth.settings'))


# Add settings page route
@auth_bp.route('/settings')
@login_required
def settings():
    """Settings page."""
    user = User.query.get(session['user_id'])
    if not user:
        flash('Пользователь не найден', 'error')
        return redirect(url_for('auth.logout'))

    return render_template('settings.html', user=user)


# Family access routes
@auth_bp.route('/profile/family')
@login_required
def family_settings():
    """Family access settings page."""
    from .family_service import FamilyService

    user_id = session['user_id']
    family_info = FamilyService.get_family_info(user_id)

    return render_template('auth/family_settings.html', family_info=family_info)


@auth_bp.route('/profile/family/create', methods=['POST'])
@login_required
def create_family_access():
    """Create family access."""
    from .family_service import FamilyService

    user_id = session['user_id']
    name = request.form.get('name', '').strip()

    try:
        shared_budget = FamilyService.create_family_access(user_id, name)
        flash(f'Семейный доступ создан! Код приглашения: {shared_budget.invitation_code}', 'success')
    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        current_app.logger.error(f"Error creating family access: {e}")
        flash('Ошибка при создании семейного доступа', 'error')

    return redirect(url_for('auth.family_settings'))


@auth_bp.route('/profile/family/join', methods=['POST'])
@login_required
def join_family():
    """Join family by invitation code."""
    from .family_service import FamilyService

    user_id = session['user_id']
    invitation_code = request.form.get('invitation_code', '').strip().upper()

    if not invitation_code:
        flash('Введите код приглашения', 'error')
        return redirect(url_for('auth.family_settings'))

    try:
        shared_budget = FamilyService.join_family(user_id, invitation_code)
        if shared_budget:
            flash(f'Вы присоединились к семье "{shared_budget.name}"!', 'success')
        else:
            flash('Неверный код приглашения', 'error')
    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        current_app.logger.error(f"Error joining family: {e}")
        flash('Ошибка при присоединении к семье', 'error')

    return redirect(url_for('auth.family_settings'))


@auth_bp.route('/profile/family/leave', methods=['POST'])
@login_required
def leave_family():
    """Leave family access."""
    from .family_service import FamilyService

    user_id = session['user_id']

    try:
        if FamilyService.leave_family(user_id):
            flash('Вы покинули семейный доступ', 'info')
        else:
            flash('Вы не состоите в семейном доступе', 'error')
    except Exception as e:
        current_app.logger.error(f"Error leaving family: {e}")
        flash('Ошибка при выходе из семейного доступа', 'error')

    return redirect(url_for('auth.family_settings'))