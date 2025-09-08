#!/usr/bin/env python3
"""
Утилита управления CrystalBudget.
Команды: init-db, migrate, seed, run
"""

import os
import sys
import sqlite3
from datetime import datetime


def init_db():
    """Инициализировать базу данных."""
    print("🔄 Инициализация базы данных...")
    from app import create_app
    
    app = create_app()
    with app.app_context():
        from app.db import init_db
        init_db()
        print("✅ База данных инициализирована")


def migrate():
    """Запустить миграции."""
    print("🔄 Запуск миграций...")
    os.system("python3 migrate_to_modular.py")


def seed():
    """Заполнить БД тестовыми данными."""
    print("🔄 Заполнение тестовыми данными...")
    
    db_path = os.environ.get("BUDGET_DB", "budget.db")
    conn = sqlite3.connect(db_path)
    
    # Проверяем есть ли уже пользователи
    cursor = conn.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] > 0:
        print("ℹ️  Пользователи уже существуют, пропускаем seed")
        return
    
    from werkzeug.security import generate_password_hash
    
    # Создаем тестового пользователя
    conn.execute("""
    INSERT INTO users (name, email, password_hash, default_currency, theme) 
    VALUES (?, ?, ?, ?, ?)
    """, ("Тест Пользователь", "test@example.com", generate_password_hash("password"), "RUB", "light"))
    
    user_id = conn.lastrowid
    
    # Создаем тестовые категории
    categories = [
        ("Продукты", 15000, "fixed"),
        ("Транспорт", 8000, "fixed"),
        ("Развлечения", 10, "percent"),
        ("Коммунальные", 5000, "fixed"),
    ]
    
    for name, value, limit_type in categories:
        conn.execute("""
        INSERT INTO categories (user_id, name, value, limit_type) 
        VALUES (?, ?, ?, ?)
        """, (user_id, name, value, limit_type))
    
    # Создаем источник дохода
    conn.execute("""
    INSERT INTO income_sources (user_id, name, is_default) 
    VALUES (?, ?, ?)
    """, (user_id, "Основная работа", 1))
    
    conn.commit()
    conn.close()
    
    print("✅ Тестовые данные добавлены")
    print("👤 Пользователь: test@example.com / password")


def run():
    """Запустить приложение."""
    print("🚀 Запуск CrystalBudget...")
    os.system("python3 wsgi.py")


def show_help():
    """Показать справку."""
    print("""
🎯 CrystalBudget Management Utility

Команды:
  init-db    Инициализировать базу данных
  migrate    Запустить миграции  
  seed       Заполнить тестовыми данными
  run        Запустить приложение
  help       Показать эту справку

Примеры:
  python3 manage.py init-db
  python3 manage.py migrate
  python3 manage.py seed
  python3 manage.py run
  
Переменные окружения:
  BUDGET_DB=/path/to/budget.db
  SECRET_KEY=your-secret-key
  FLASK_ENV=development|production
  PORT=5000
    """)


def main():
    """Главная функция."""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1]
    
    if command == "init-db":
        init_db()
    elif command == "migrate":
        migrate()
    elif command == "seed":
        seed()
    elif command == "run":
        run()
    elif command == "help":
        show_help()
    else:
        print(f"❌ Неизвестная команда: {command}")
        show_help()


if __name__ == "__main__":
    main()