import os
from datetime import timedelta


class Config:
    """Базовая конфигурация."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-only-insecure-key-change-in-production')
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    
    # Database
    DB_PATH = os.environ.get("BUDGET_DB", "budget.db")
    
    # Uploads
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2 MB
    AVATAR_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'avatars')
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'crystalbudget.log')
    
    # Currency
    EXR_CACHE_TTL_SECONDS = int(os.environ.get("EXR_CACHE_TTL_SECONDS", str(12 * 3600)))  # 12 часов
    EXR_BRIDGE = os.environ.get("EXR_BRIDGE", "USD").upper()
    
    # Security
    HTTPS_MODE = os.environ.get('HTTPS_MODE', 'False').lower() == 'true'
    
    @property
    def session_cookie_secure(self):
        return self.HTTPS_MODE
    
    @property
    def session_cookie_httponly(self):
        return True
    
    @property
    def session_cookie_samesite(self):
        return 'Lax'


class DevelopmentConfig(Config):
    """Конфигурация для разработки."""
    DEBUG = True
    SESSION_COOKIE_NAME = 'session'
    
    @property
    def csp_policy(self):
        return [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net",
            "font-src 'self' data: https://fonts.gstatic.com https://cdn.jsdelivr.net",
            "img-src 'self' data:",
            "connect-src 'self' https://api.exchangerate.host"
        ]


class ProductionConfig(Config):
    """Конфигурация для продакшена."""
    DEBUG = False
    SESSION_COOKIE_NAME = 'cbsid'  # скрываем Flask
    
    @property
    def csp_policy(self):
        return [
            "default-src 'self'",
            "script-src 'self' https://cdn.jsdelivr.net",
            "style-src 'self' https://fonts.googleapis.com https://cdn.jsdelivr.net",
            "font-src 'self' data: https://fonts.gstatic.com https://cdn.jsdelivr.net", 
            "img-src 'self' data:",
            "connect-src 'self' https://api.exchangerate.host"
        ]


class TestConfig(Config):
    """Конфигурация для тестов."""
    TESTING = True
    DB_PATH = ':memory:'


config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestConfig,
    'default': DevelopmentConfig
}