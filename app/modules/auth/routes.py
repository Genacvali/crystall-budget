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
            return redirect(next_page or url_for('budget.dashboard'))
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
            # Add theme column if it doesn't exist
            try:
                from sqlalchemy import text
                db.session.execute(text("ALTER TABLE users ADD COLUMN theme VARCHAR(20)"))
                db.session.commit()
            except Exception:
                pass  # Column likely already exists
            
            # Update user theme
            user.theme = theme
            db.session.commit()
    except Exception:
        pass  # Continue even if DB update fails
    
    return jsonify({"ok": True})