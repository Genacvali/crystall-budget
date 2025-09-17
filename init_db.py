#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт инициализации базы данных для CrystalBudget

Создает все необходимые таблицы и добавляет начальные данные.
Можно запускать повторно - скрипт безопасен благодаря IF NOT EXISTS.
"""

import sqlite3
import sys
import os
from datetime import datetime

# Путь к БД (можно переопределить через переменную окружения)
DB_PATH = os.environ.get("BUDGET_DB", "budget.db")

def create_database():
    """Создает все таблицы базы данных"""
    print(f"🗄️  Инициализация базы данных: {DB_PATH}")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.executescript("""
            PRAGMA foreign_keys = ON;
            
            -- Таблица пользователей
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                timezone TEXT DEFAULT 'UTC',
                locale TEXT DEFAULT 'ru',
                default_currency TEXT DEFAULT 'RUB',
                currency TEXT DEFAULT 'RUB',
                theme TEXT DEFAULT 'light',
                avatar_path TEXT
            );

            -- Таблица категорий бюджета
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                limit_type TEXT NOT NULL CHECK(limit_type IN ('fixed','percent')),
                value REAL NOT NULL,
                currency TEXT DEFAULT 'RUB',
                category_type TEXT DEFAULT 'expense' CHECK(category_type IN ('expense','income')),
                multi_source INTEGER NOT NULL DEFAULT 0
            );

            -- Таблица ежедневных доходов
            CREATE TABLE IF NOT EXISTS income_daily (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                source_id INTEGER REFERENCES income_sources(id),
                currency TEXT DEFAULT 'RUB'
            );

            -- Старая таблица доходов (для совместимости)
            CREATE TABLE IF NOT EXISTS income (
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                month TEXT NOT NULL,
                amount REAL NOT NULL
            );

            -- Таблица расходов
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                date TEXT NOT NULL,
                month TEXT NOT NULL,
                category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
                amount REAL NOT NULL,
                note TEXT,
                currency TEXT DEFAULT 'RUB'
            );

            -- Таблица источников дохода
            CREATE TABLE IF NOT EXISTS income_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                is_default INTEGER NOT NULL DEFAULT 0,
                UNIQUE(user_id, name)
            );

            -- Таблица правил для автоматического распределения дохода по категориям
            CREATE TABLE IF NOT EXISTS source_category_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                source_id INTEGER NOT NULL REFERENCES income_sources(id) ON DELETE CASCADE,
                category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
                priority INTEGER NOT NULL DEFAULT 100,
                allocation_percent REAL NOT NULL DEFAULT 0.0,
                UNIQUE(user_id, source_id, category_id)
            );

            -- Таблица связей категорий с источниками доходов (для многоисточниковых категорий)
            CREATE TABLE IF NOT EXISTS category_income_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
                source_id INTEGER NOT NULL REFERENCES income_sources(id) ON DELETE CASCADE,
                percentage REAL NOT NULL CHECK(percentage > 0 AND percentage <= 100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(category_id, source_id)
            );

            -- Таблица целей накоплений
            CREATE TABLE IF NOT EXISTS savings_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                target_amount DECIMAL(10,2) NOT NULL,
                current_amount DECIMAL(10,2) DEFAULT 0,
                target_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP NULL
            );

            -- Таблица семейных бюджетов
            CREATE TABLE IF NOT EXISTS shared_budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                creator_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                invite_code TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Таблица участников семейных бюджетов
            CREATE TABLE IF NOT EXISTS shared_budget_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shared_budget_id INTEGER NOT NULL REFERENCES shared_budgets(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                role TEXT DEFAULT 'member',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(shared_budget_id, user_id)
            );

            -- Таблица курсов валют
            CREATE TABLE IF NOT EXISTS exchange_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_currency TEXT NOT NULL,
                to_currency TEXT NOT NULL,
                rate DECIMAL(10,6) NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(from_currency, to_currency)
            );

            -- Таблица токенов восстановления пароля
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token TEXT UNIQUE NOT NULL,
                expires_at DATETIME NOT NULL,
                used INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            -- Таблица для хранения накопленных остатков по категориям
            CREATE TABLE IF NOT EXISTS budget_rollover (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
                month TEXT NOT NULL,
                limit_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
                spent_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
                rollover_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, category_id, month)
            );

            -- Таблица для связи пользователей с Telegram
            CREATE TABLE IF NOT EXISTS user_telegram (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                telegram_id TEXT UNIQUE NOT NULL,
                telegram_username TEXT,
                telegram_first_name TEXT,
                telegram_last_name TEXT,
                is_verified INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verified_at TIMESTAMP NULL,
                UNIQUE(user_id)
            );

            -- Создание индексов для производительности
            CREATE INDEX IF NOT EXISTS idx_expenses_user_month ON expenses(user_id, month);
            CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category_id);
            CREATE INDEX IF NOT EXISTS idx_categories_user ON categories(user_id);
            CREATE INDEX IF NOT EXISTS idx_income_daily_user_date ON income_daily(user_id, date);
            CREATE INDEX IF NOT EXISTS idx_savings_goals_user ON savings_goals(user_id);
            CREATE INDEX IF NOT EXISTS idx_shared_budget_members_budget ON shared_budget_members(shared_budget_id);
            CREATE INDEX IF NOT EXISTS idx_shared_budget_members_user ON shared_budget_members(user_id);
            CREATE INDEX IF NOT EXISTS idx_exchange_rates_currencies ON exchange_rates(from_currency, to_currency);
            CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user ON password_reset_tokens(user_id);
            CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token ON password_reset_tokens(token);
            CREATE INDEX IF NOT EXISTS idx_category_income_sources_category ON category_income_sources(category_id);
            CREATE INDEX IF NOT EXISTS idx_category_income_sources_user ON category_income_sources(user_id);
            CREATE INDEX IF NOT EXISTS idx_budget_rollover_user_category ON budget_rollover(user_id, category_id);
            CREATE INDEX IF NOT EXISTS idx_budget_rollover_month ON budget_rollover(month);
            CREATE INDEX IF NOT EXISTS idx_user_telegram_user ON user_telegram(user_id);
            CREATE INDEX IF NOT EXISTS idx_user_telegram_telegram_id ON user_telegram(telegram_id);
        """)
        
        conn.commit()
        conn.close()
        print("✅ База данных успешно инициализирована")
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Ошибка при создании базы данных: {e}")
        return False

def create_default_categories(user_id, conn):
    """Создает стандартные категории для нового пользователя"""
    default_categories = [
        ("Продукты", "percent", 30.0, "RUB"),
        ("Транспорт", "fixed", 5000.0, "RUB"),
        ("Развлечения", "percent", 15.0, "RUB"),
        ("Коммунальные", "fixed", 8000.0, "RUB"),
        ("Здоровье", "fixed", 3000.0, "RUB"),
        ("Одежда", "percent", 10.0, "RUB"),
    ]
    
    cursor = conn.cursor()
    for name, limit_type, value, currency in default_categories:
        cursor.execute("""
            INSERT OR IGNORE INTO categories (user_id, name, limit_type, value, currency)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, name, limit_type, value, currency))
    
    conn.commit()

def add_demo_data():
    """Добавляет демонстрационные данные (опционально)"""
    response = input("Добавить демонстрационные данные? (y/N): ").lower()
    if response != 'y':
        return
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Создаем демо-пользователя
        from werkzeug.security import generate_password_hash
        demo_email = "demo@crystalbudget.ru"
        demo_password = generate_password_hash("demo123")
        
        cursor.execute("""
            INSERT OR IGNORE INTO users (email, name, password_hash)
            VALUES (?, ?, ?)
        """, (demo_email, "Демо Пользователь", demo_password))
        
        # Получаем ID пользователя
        cursor.execute("SELECT id FROM users WHERE email = ?", (demo_email,))
        user_row = cursor.fetchone()
        if user_row:
            user_id = user_row[0]
            
            # Создаем категории
            create_default_categories(user_id, conn)
            
            # Добавляем доход
            current_month = datetime.now().strftime("%Y-%m")
            cursor.execute("""
                INSERT OR IGNORE INTO income (user_id, month, amount)
                VALUES (?, ?, ?)
            """, (user_id, current_month, 100000.0))
            
            print(f"✅ Создан демо-пользователь: {demo_email} / demo123")
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка при создании демо-данных: {e}")

def check_database():
    """Проверяет состояние базы данных"""
    if not os.path.exists(DB_PATH):
        print(f"📁 База данных {DB_PATH} не существует")
        return False
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Проверяем основные таблицы
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN (
                'users', 'categories', 'expenses', 'income_daily', 
                'savings_goals', 'shared_budgets', 'budget_rollover', 
                'category_income_sources', 'income_sources'
            )
        """)
        
        tables = [row[0] for row in cursor.fetchall()]
        expected_tables = ['users', 'categories', 'expenses', 'income_daily', 'savings_goals', 'shared_budgets', 'budget_rollover', 'category_income_sources', 'income_sources']
        
        print(f"📊 Найденные таблицы: {', '.join(tables)}")
        
        missing_tables = set(expected_tables) - set(tables)
        if missing_tables:
            print(f"⚠️  Отсутствующие таблицы: {', '.join(missing_tables)}")
            return False
        
        # Проверяем количество пользователей
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"👥 Пользователей в базе: {user_count}")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Ошибка при проверке базы данных: {e}")
        return False

def main():
    """Основная функция"""
    print("🏗️  CrystalBudget - Инициализация базы данных")
    print("=" * 50)
    
    # Проверяем текущее состояние
    if check_database():
        print("\n✅ База данных уже существует и корректна")
        response = input("Пересоздать таблицы? (y/N): ").lower()
        if response != 'y':
            print("Завершение работы")
            return
    
    # Создаем БД
    if not create_database():
        sys.exit(1)
    
    # Предлагаем добавить демо-данные
    add_demo_data()
    
    print("\n🎉 Инициализация завершена!")
    print(f"📁 База данных: {os.path.abspath(DB_PATH)}")
    print("\n🚀 Для запуска приложения выполните:")
    print("   python app.py")

if __name__ == "__main__":
    main()