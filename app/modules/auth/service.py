"""Auth service layer."""
import hashlib
import hmac
import time
import secrets
from typing import Optional, Dict, Any
from flask import current_app, session, flash
from flask_login import login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User
from app.core.extensions import db


class AuthService:
    """Authentication service."""
    
    @staticmethod
    def verify_telegram_auth(args: dict, bot_token: str, max_age_sec: int = 600) -> bool:
        """Verify Telegram authentication data."""
        if not bot_token:
            return False
            
        tg_hash = args.get("hash")
        if not tg_hash:
            return False
        
        # Check auth_date
        auth_date = args.get("auth_date")
        if auth_date:
            try:
                auth_timestamp = int(auth_date)
                current_timestamp = int(time.time())
                if current_timestamp - auth_timestamp > max_age_sec:
                    current_app.logger.warning(f"Telegram auth expired: {current_timestamp - auth_timestamp}s old")
                    return False
            except ValueError:
                current_app.logger.warning(f"Invalid auth_date format: {auth_date}")
                return False
        
        # Build data string for verification
        tg_keys = ("auth_date", "first_name", "id", "last_name", "photo_url", "username")
        data_check_arr = []
        
        for key in tg_keys:
            if key in args and args[key]:
                data_check_arr.append(f"{key}={args[key]}")
        
        data_check_arr.sort()
        data_check_string = "\n".join(data_check_arr)
        
        # Calculate secret key
        secret_key = hashlib.sha256(bot_token.encode()).digest()
        
        # Calculate hash
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(calculated_hash, tg_hash)
    
    @staticmethod
    def login_user(user: User) -> None:
        """Set user session."""
        # Use Flask-Login to manage user session
        login_user(user, remember=True)
        
        # Set additional session data for compatibility
        session['user_id'] = user.id
        session['user_name'] = user.display_name
        session['theme'] = user.theme or 'light'
        session['currency'] = user.currency or 'RUB'
        session['auth_type'] = user.auth_type
        
        if user.is_telegram_user:
            session['telegram_id'] = user.telegram_id
        
        # Make session permanent (30 days from config)
        session.permanent = True
    
    @staticmethod
    def logout_user() -> None:
        """Clear user session."""
        logout_user()
        session.clear()
    
    @staticmethod
    def authenticate_telegram(telegram_data: dict, bot_token: str) -> Optional[User]:
        """Authenticate or register user via Telegram."""
        # Verify Telegram data
        if bot_token and not AuthService.verify_telegram_auth(telegram_data, bot_token):
            current_app.logger.warning(f'Invalid Telegram auth hash for ID: {telegram_data.get("id")}')
            return None
        
        telegram_id = telegram_data['id']
        current_app.logger.info(f'Telegram auth attempt for ID: {telegram_id}')
        
        # Try to find existing user
        user = User.find_by_telegram_id(telegram_id)
        
        if user:
            # Update user's Telegram data
            user.update_telegram_data(telegram_data)
            current_app.logger.info(f'Existing Telegram user logged in: {telegram_id} (ID: {user.id})')
            return user
        else:
            # Check if user has current session and merge accounts
            current_user_id = session.get('user_id')
            if current_user_id:
                current_user = User.query.get(current_user_id)
                if current_user and not current_user.telegram_id:
                    # Merge accounts
                    current_user.telegram_id = telegram_id
                    current_user.update_telegram_data(telegram_data)
                    current_app.logger.info(f'Merged Telegram account with existing user: {current_user_id}')
                    return current_user
            
            # Create new Telegram user
            user = User.create_telegram_user(telegram_data)
            current_app.logger.info(f'Created new Telegram user: {telegram_id} (ID: {user.id})')
            return user
    
    @staticmethod
    def authenticate_email(email: str, password: str) -> Optional[User]:
        """Authenticate user via email/password."""
        user = User.find_by_email(email)
        
        if user and user.check_password(password):
            current_app.logger.info(f'Successful email login: {email} (ID: {user.id})')
            return user
        
        current_app.logger.warning(f'Failed email login: {email}')
        return None
    
    @staticmethod
    def register_email(email: str, name: str, password: str) -> Optional[User]:
        """Register new user via email."""
        # Check if user already exists
        if User.find_by_email(email):
            flash("Пользователь с таким email уже существует", "error")
            return None
        
        try:
            user = User(
                email=email,
                name=name,
                auth_type='email'
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            current_app.logger.info(f'Successful email registration: {email} (ID: {user.id})')
            return user
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Database error during email registration for {email}: {e}')
            flash("Ошибка сервера. Попробуйте позже", "error")
            return None
    
    @staticmethod
    def change_password(user: User, old_password: str, new_password: str) -> bool:
        """Change user password."""
        if not user.check_password(old_password):
            flash("Неверный текущий пароль", "error")
            return False
        
        try:
            user.set_password(new_password)
            db.session.commit()
            current_app.logger.info(f'Password changed for user ID: {user.id}')
            return True
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error changing password for user {user.id}: {e}')
            flash("Ошибка при изменении пароля", "error")
            return False
    
    @staticmethod
    def update_user_preferences(user: User, preferences: dict) -> bool:
        """Update user preferences."""
        try:
            for key, value in preferences.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            
            db.session.commit()
            
            # Update session if needed
            if 'theme' in preferences:
                session['theme'] = preferences['theme']
            if 'currency' in preferences:
                session['currency'] = preferences['currency']
            
            current_app.logger.info(f'Updated preferences for user ID: {user.id}')
            return True
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error updating preferences for user {user.id}: {e}')
            return False