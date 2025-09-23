"""Auth module models."""
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from app.core.extensions import db


class User(UserMixin, db.Model):
    """User model with email and Telegram authentication support."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Email auth fields
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Telegram auth fields
    telegram_id = db.Column(db.BigInteger, unique=True, nullable=True)
    telegram_username = db.Column(db.String(100), nullable=True)
    telegram_first_name = db.Column(db.String(100), nullable=True)
    telegram_last_name = db.Column(db.String(100), nullable=True)
    telegram_photo_url = db.Column(db.String(500), nullable=True)
    
    # User preferences
    auth_type = db.Column(db.String(20), nullable=False, default='email')
    theme = db.Column(db.String(20), default='light')
    currency = db.Column(db.String(3), default='RUB')
    timezone = db.Column(db.String(50), default='UTC')
    locale = db.Column(db.String(10), default='ru')
    default_currency = db.Column(db.String(3), default='RUB')
    avatar_path = db.Column(db.String(255), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<User {self.name}>'
    
    def set_password(self, password):
        """Set password hash."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash."""
        return check_password_hash(self.password_hash, password)
    
    @property
    def is_telegram_user(self):
        """Check if user uses Telegram authentication."""
        return self.auth_type == 'telegram' and self.telegram_id is not None
    
    @property
    def display_name(self):
        """Get display name for user."""
        if self.is_telegram_user:
            # Build name from Telegram data
            parts = []
            if self.telegram_first_name:
                parts.append(self.telegram_first_name)
            if self.telegram_last_name:
                parts.append(self.telegram_last_name)
            
            if parts:
                return " ".join(parts)
            elif self.telegram_username:
                return self.telegram_username
            else:
                return f"User{self.telegram_id}"
        
        return self.name
    
    def to_dict(self):
        """Convert user to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'email': self.email,
            'auth_type': self.auth_type,
            'theme': self.theme,
            'currency': self.currency,
            'timezone': self.timezone,
            'locale': self.locale,
            'avatar_path': self.avatar_path,
            'is_telegram_user': self.is_telegram_user,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def find_by_email(cls, email):
        """Find user by email."""
        return cls.query.filter_by(email=email).first()
    
    @classmethod
    def find_by_telegram_id(cls, telegram_id):
        """Find user by Telegram ID."""
        return cls.query.filter_by(telegram_id=telegram_id).first()
    
    @classmethod
    def create_telegram_user(cls, telegram_data):
        """Create new user from Telegram data."""
        telegram_id = telegram_data['id']
        username = telegram_data.get('username', '')
        first_name = telegram_data.get('first_name', '')
        last_name = telegram_data.get('last_name', '')
        photo_url = telegram_data.get('photo_url', '')
        
        # Build display name
        display_name = ""
        if first_name:
            display_name = first_name
        if last_name:
            display_name += f" {last_name}"
        if not display_name.strip():
            display_name = username or f"User{telegram_id}"
        
        # Generate fake email and password for compatibility
        fake_email = f"tg{telegram_id}@telegram.local"
        fake_password = generate_password_hash(f"telegram_user_{telegram_id}")
        
        user = cls(
            email=fake_email,
            name=display_name,
            password_hash=fake_password,
            auth_type='telegram',
            telegram_id=telegram_id,
            telegram_username=username,
            telegram_first_name=first_name,
            telegram_last_name=last_name,
            telegram_photo_url=photo_url
        )
        
        db.session.add(user)
        db.session.commit()
        
        return user
    
    def update_telegram_data(self, telegram_data):
        """Update user's Telegram data."""
        self.telegram_username = telegram_data.get('username', '')
        self.telegram_first_name = telegram_data.get('first_name', '')
        self.telegram_last_name = telegram_data.get('last_name', '')
        self.telegram_photo_url = telegram_data.get('photo_url', '')
        
        # Update display name
        display_name = ""
        if self.telegram_first_name:
            display_name = self.telegram_first_name
        if self.telegram_last_name:
            display_name += f" {self.telegram_last_name}"
        if not display_name.strip():
            display_name = self.telegram_username or f"User{self.telegram_id}"
        
        self.name = display_name
        self.auth_type = 'telegram'
        
        db.session.commit()