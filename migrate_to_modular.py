#!/usr/bin/env python3
"""
Скрипт миграции базы данных для модульной архитектуры CrystalBudget.
Добавляет недостающие колонки и таблицы.
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.environ.get("BUDGET_DB", "budget.db")


def get_db():
    """Получить соединение с БД."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def check_column_exists(conn, table, column):
    """Проверить существует ли колонка в таблице."""
    cursor = conn.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns


def check_table_exists(conn, table):
    """Проверить существует ли таблица."""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    return cursor.fetchone() is not None


def migrate_profile_columns():
    """Добавить колонки профиля в таблицу users."""
    print("🔄 Миграция колонок профиля...")
    conn = get_db()
    
    profile_columns = [
        ("timezone", "TEXT DEFAULT 'UTC'"),
        ("locale", "TEXT DEFAULT 'ru'"),
        ("default_currency", "TEXT DEFAULT 'RUB'"),
        ("theme", "TEXT DEFAULT 'light'"),
        ("avatar_path", "TEXT"),
    ]
    
    for column, definition in profile_columns:
        if not check_column_exists(conn, "users", column):
            try:
                conn.execute(f"ALTER TABLE users ADD COLUMN {column} {definition}")
                print(f"✅ Добавлена колонка users.{column}")
            except sqlite3.OperationalError as e:
                print(f"❌ Ошибка добавления users.{column}: {e}")
    
    conn.commit()
    conn.close()


def migrate_currency_columns():
    """Добавить колонки currency в expenses и income_daily."""
    print("🔄 Миграция валютных колонок...")
    conn = get_db()
    
    tables = ["expenses", "income_daily"]
    
    for table in tables:
        if check_table_exists(conn, table) and not check_column_exists(conn, table, "currency"):
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN currency TEXT DEFAULT 'RUB'")
                print(f"✅ Добавлена колонка {table}.currency")
            except sqlite3.OperationalError as e:
                print(f"❌ Ошибка добавления {table}.currency: {e}")
    
    conn.commit()
    conn.close()


def create_new_tables():
    """Создать новые таблицы для дополнительного функционала."""
    print("🔄 Создание новых таблиц...")
    conn = get_db()
    
    tables = {
        "savings_goals": """
        CREATE TABLE IF NOT EXISTS savings_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            target_amount DECIMAL(10,2) NOT NULL,
            current_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
            target_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        "shared_budgets": """
        CREATE TABLE IF NOT EXISTS shared_budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            creator_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            invite_code TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        "shared_budget_members": """
        CREATE TABLE IF NOT EXISTS shared_budget_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            budget_id INTEGER NOT NULL REFERENCES shared_budgets(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role TEXT NOT NULL DEFAULT 'member' CHECK(role IN ('admin', 'member')),
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(budget_id, user_id)
        )
        """,
        
        "exchange_rates": """
        CREATE TABLE IF NOT EXISTS exchange_rates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_currency TEXT NOT NULL,
            to_currency TEXT NOT NULL,
            rate DECIMAL(10,6) NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(from_currency, to_currency)
        )
        """,
        
        "income_sources": """
        CREATE TABLE IF NOT EXISTS income_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            is_default INTEGER NOT NULL DEFAULT 0,
            UNIQUE(user_id, name)
        )
        """,
        
        "source_category_rules": """
        CREATE TABLE IF NOT EXISTS source_category_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            source_id INTEGER NOT NULL REFERENCES income_sources(id) ON DELETE CASCADE,
            category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
            priority INTEGER NOT NULL DEFAULT 100,
            UNIQUE(user_id, category_id)
        )
        """
    }
    
    for table_name, create_sql in tables.items():
        if not check_table_exists(conn, table_name):
            try:
                conn.execute(create_sql)
                print(f"✅ Создана таблица {table_name}")
            except sqlite3.OperationalError as e:
                print(f"❌ Ошибка создания таблицы {table_name}: {e}")
        else:
            print(f"ℹ️  Таблица {table_name} уже существует")
    
    conn.commit()
    conn.close()


def add_missing_columns():
    """Добавить недостающие колонки в существующие таблицы."""
    print("🔄 Проверка недостающих колонок...")
    conn = get_db()
    
    # Проверяем income_daily.source_id
    if check_table_exists(conn, "income_daily") and not check_column_exists(conn, "income_daily", "source_id"):
        try:
            conn.execute("ALTER TABLE income_daily ADD COLUMN source_id INTEGER REFERENCES income_sources(id)")
            print("✅ Добавлена колонка income_daily.source_id")
        except sqlite3.OperationalError as e:
            print(f"❌ Ошибка добавления income_daily.source_id: {e}")
    
    # Проверяем categories.limit_type
    if check_table_exists(conn, "categories") and not check_column_exists(conn, "categories", "limit_type"):
        try:
            conn.execute("ALTER TABLE categories ADD COLUMN limit_type TEXT DEFAULT 'fixed' CHECK(limit_type IN ('fixed','percent'))")
            print("✅ Добавлена колонка categories.limit_type")
        except sqlite3.OperationalError as e:
            print(f"❌ Ошибка добавления categories.limit_type: {e}")
    
    # Проверяем categories.category_type
    if check_table_exists(conn, "categories") and not check_column_exists(conn, "categories", "category_type"):
        try:
            conn.execute("ALTER TABLE categories ADD COLUMN category_type TEXT DEFAULT 'expense' CHECK(category_type IN ('expense','income'))")
            print("✅ Добавлена колонка categories.category_type")
        except sqlite3.OperationalError as e:
            print(f"❌ Ошибка добавления categories.category_type: {e}")
    
    conn.commit()
    conn.close()


def create_backup():
    """Создать резервную копию БД."""
    if not os.path.exists(DB_PATH):
        print("⚠️  База данных не найдена, пропускаем резервное копирование")
        return
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{DB_PATH}.backup_{timestamp}"
    
    try:
        # Простое копирование файла
        import shutil
        shutil.copy2(DB_PATH, backup_path)
        print(f"✅ Создана резервная копия: {backup_path}")
    except Exception as e:
        print(f"❌ Ошибка создания резервной копии: {e}")
        response = input("Продолжить без резервной копии? (y/N): ")
        if response.lower() != 'y':
            print("Миграция отменена")
            exit(1)


def main():
    """Главная функция миграции."""
    print("🚀 Начало миграции базы данных CrystalBudget")
    print(f"📍 Файл БД: {DB_PATH}")
    
    # Создаем резервную копию
    create_backup()
    
    # Выполняем миграции
    try:
        migrate_profile_columns()
        migrate_currency_columns()
        create_new_tables()
        add_missing_columns()
        
        print("\n✅ Миграция успешно завершена!")
        print("🎉 База данных готова для работы с модульной архитектурой")
        
    except Exception as e:
        print(f"\n❌ Ошибка миграции: {e}")
        print("🔄 Проверьте резервную копию и попробуйте снова")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())