#!/usr/bin/env python3
"""
Скрипт миграции для создания новых таблиц в CrystalBudget
Запускать этот скрипт на сервере для обновления базы данных
"""

import os
import sqlite3
import sys

def get_db_path():
    """Получить путь к базе данных из переменных окружения или использовать по умолчанию."""
    return os.environ.get("BUDGET_DB", "budget.db")

def ensure_new_tables():
    """Создаем новые таблицы если их нет (миграция)."""
    db_path = get_db_path()
    
    print(f"🔄 Запуск миграции базы данных: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"❌ Файл базы данных не найден: {db_path}")
        sys.exit(1)
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        
        tables_created = 0
        
        # Проверяем существование таблиц
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='savings_goals'")
        if not cursor.fetchone():
            # Таблица для целей накоплений
            conn.execute("""
            CREATE TABLE savings_goals (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              name TEXT NOT NULL,
              target_amount DECIMAL(10,2) NOT NULL,
              current_amount DECIMAL(10,2) DEFAULT 0,
              target_date DATE,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              completed_at TIMESTAMP NULL,
              description TEXT
            )
            """)
            print("✅ Создана таблица: savings_goals")
            tables_created += 1
        else:
            print("⏭️  Таблица savings_goals уже существует")
        
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='shared_budgets'")
        if not cursor.fetchone():
            # Таблица для shared budgets
            conn.execute("""
            CREATE TABLE shared_budgets (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              creator_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              invite_code TEXT UNIQUE NOT NULL,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            print("✅ Создана таблица: shared_budgets")
            tables_created += 1
        else:
            print("⏭️  Таблица shared_budgets уже существует")
        
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='shared_budget_members'")
        if not cursor.fetchone():
            # Участники shared budgets
            conn.execute("""
            CREATE TABLE shared_budget_members (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              shared_budget_id INTEGER NOT NULL REFERENCES shared_budgets(id) ON DELETE CASCADE,
              user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              role TEXT DEFAULT 'member',
              joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              UNIQUE(shared_budget_id, user_id)
            )
            """)
            print("✅ Создана таблица: shared_budget_members")
            tables_created += 1
        else:
            print("⏭️  Таблица shared_budget_members уже существует")
        
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='exchange_rates'")
        if not cursor.fetchone():
            # Курсы валют (для кэширования)
            conn.execute("""
            CREATE TABLE exchange_rates (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              from_currency TEXT NOT NULL,
              to_currency TEXT NOT NULL,
              rate DECIMAL(10,6) NOT NULL,
              updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              UNIQUE(from_currency, to_currency)
            )
            """)
            print("✅ Создана таблица: exchange_rates")
            tables_created += 1
        else:
            print("⏭️  Таблица exchange_rates уже существует")
            
        conn.commit()
        conn.close()
        
        if tables_created > 0:
            print(f"🎉 Миграция завершена успешно! Создано таблиц: {tables_created}")
        else:
            print("✅ Все таблицы уже существуют, миграция не требуется")
        
    except Exception as e:
        print(f"❌ Ошибка при выполнении миграции: {e}")
        if 'conn' in locals():
            conn.close()
        sys.exit(1)

if __name__ == "__main__":
    ensure_new_tables()