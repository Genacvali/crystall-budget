import os
import logging
from logging.handlers import RotatingFileHandler


def setup_logging(app):
    """Настройка системы логирования."""
    if app.debug:
        return
        
    # Создаём директорию для логов
    log_dir = os.path.dirname(app.config['LOG_FILE'])
    os.makedirs(log_dir, exist_ok=True)
    
    # Настройка ротирующего файлового логгера
    file_handler = RotatingFileHandler(
        app.config['LOG_FILE'],
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s [%(name)s] %(message)s'
    ))
    
    # Устанавливаем уровень логирования
    log_level = getattr(logging, app.config['LOG_LEVEL'].upper(), logging.INFO)
    file_handler.setLevel(log_level)
    app.logger.setLevel(log_level)
    app.logger.addHandler(file_handler)
    
    # Логируем старт системы
    app.logger.info("Logging system initialized")
    app.logger.info(f"Log level: {app.config['LOG_LEVEL']}")
    app.logger.info(f"Log file: {app.config['LOG_FILE']}")
    
    # Отключаем избыточное логирование Werkzeug
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.setLevel(logging.WARNING)