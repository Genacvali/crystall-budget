"""Application configuration."""
import os
import secrets
from datetime import timedelta


class BaseConfig:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    SQLALCHEMY_DATABASE_URI = os.environ.get('BUDGET_DB', 'sqlite:////opt/crystall-budget/instance/budget.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_timeout': 20,
        'pool_recycle': -1,
        'pool_pre_ping': True
    }
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Cache configuration
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Telegram
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    TELEGRAM_LOGIN_ENABLED = os.environ.get('TELEGRAM_LOGIN_ENABLED', 'true').lower() == 'true'

    # Diagnostics
    DIAGNOSTICS_ENABLED = os.environ.get('DIAGNOSTICS_ENABLED', 'false').lower() == 'true'
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    # Feature Flags
    # Modal System Configuration (Stage 6: Simplified to kill-switch only)
    MODAL_SYSTEM_ENABLED = os.environ.get('MODAL_SYSTEM_ENABLED', 'true').lower() == 'true'


class DevelopmentConfig(BaseConfig):
    """Development configuration."""
    DEBUG = True
    TESTING = False
    TEMPLATES_AUTO_RELOAD = True


class ProductionConfig(BaseConfig):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = os.environ.get('HTTPS_MODE', 'false').lower() == 'true'
    
    def __init__(self):
        """Validate production configuration."""
        super().__init__()
        if not os.environ.get('SECRET_KEY'):
            raise RuntimeError(
                "SECRET_KEY environment variable must be set in production. "
                "Generate one with: python -c 'import secrets; print(secrets.token_hex(32))'"
            )


class TestingConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False          # CSRF отключён только в тестах
    LOGIN_DISABLED = True             # Flask-Login не требует логин
    SQLALCHEMY_DATABASE_URI = os.getenv("BUDGET_DB", "sqlite:///test_local.db")
    SQLALCHEMY_ECHO = False


config_by_name = {
    "production": ProductionConfig,
    "development": DevelopmentConfig,
    "testing": TestingConfig,
}

def get_config(config_name=None):
    """Get configuration based on environment."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    config_map = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig
    }
    
    return config_map.get(config_name, DevelopmentConfig)