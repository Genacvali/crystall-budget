#!/usr/bin/env python3
"""
Скрипт для создания всех таблиц в budget.db с нуля

ВНИМАНИЕ: Этот скрипт полностью пересоздает базу данных!
Все существующие данные будут удалены.

Использует актуальную схему из app.py со всеми необходимыми полями:
- users (email, name, currency, timestamps)  
- categories (с category_type и unique constraint)
- expenses (с note, month, currency)
- income_daily (с currency)
- остальные таблицы согласно схеме

Запуск: python scripts/create_tables.py
"""

import sqlite3
import os
from decimal import Decimal

def create_all_tables():
    """Создает все таблицы в budget.db с нуля"""
    
    # Удаляем старую базу если она есть
    db_path = "budget.db"
    if os.path.exists(db_path):
        print(f"Удаляем существующую базу данных: {db_path}")
        os.remove(db_path)
    
    # Создаем подключение к новой базе
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Создаем таблицы...")
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            currency TEXT DEFAULT 'RUB',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    # Таблица категорий
    cursor.execute('''
        CREATE TABLE categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            limit_type TEXT CHECK(limit_type IN ('fixed', 'percent')) DEFAULT 'fixed',
            value DECIMAL(10,2) NOT NULL,
            category_type TEXT DEFAULT 'expense' CHECK(category_type IN ('expense','income')),
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE(name, user_id, category_type)
        )
    ''')
    
    # Таблица расходов
    cursor.execute('''
        CREATE TABLE expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount DECIMAL(10,2) NOT NULL,
            description TEXT,
            note TEXT,
            category_id INTEGER,
            date DATE NOT NULL,
            month TEXT,
            currency TEXT DEFAULT 'RUB',
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE SET NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    
    # Таблица месячных доходов
    cursor.execute('''
        CREATE TABLE income (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount DECIMAL(10,2) NOT NULL,
            month INTEGER NOT NULL,
            year INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE(user_id, month, year)
        )
    ''')
    
    # Таблица ежедневных доходов
    cursor.execute('''
        CREATE TABLE income_daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount DECIMAL(10,2) NOT NULL,
            date DATE NOT NULL,
            source_id INTEGER,
            currency TEXT DEFAULT 'RUB',
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_id) REFERENCES income_sources (id) ON DELETE SET NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    
    # Таблица источников дохода
    cursor.execute('''
        CREATE TABLE income_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            is_default BOOLEAN DEFAULT 0,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    
    # Таблица правил привязки источников к категориям
    cursor.execute('''
        CREATE TABLE source_category_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            source_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE CASCADE,
            FOREIGN KEY (source_id) REFERENCES income_sources (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE(category_id, user_id)
        )
    ''')
    
    # Таблица целей сбережений
    cursor.execute('''
        CREATE TABLE savings_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            target_amount DECIMAL(10,2) NOT NULL,
            current_amount DECIMAL(10,2) DEFAULT 0,
            target_date DATE,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    
    # Таблица общих бюджетов
    cursor.execute('''
        CREATE TABLE shared_budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            invite_code TEXT UNIQUE NOT NULL,
            creator_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (creator_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    
    # Таблица участников общих бюджетов
    cursor.execute('''
        CREATE TABLE shared_budget_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            budget_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT CHECK(role IN ('admin', 'member')) DEFAULT 'member',
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (budget_id) REFERENCES shared_budgets (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE(budget_id, user_id)
        )
    ''')
    
    # Таблица обменных курсов
    cursor.execute('''
        CREATE TABLE exchange_rates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_currency TEXT NOT NULL,
            to_currency TEXT NOT NULL,
            rate DECIMAL(10,6) NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(from_currency, to_currency)
        )
    ''')
    
    print("Создаем индексы для оптимизации...")
    
    # Индексы для оптимизации запросов
    cursor.execute('CREATE INDEX idx_expenses_user_date ON expenses(user_id, date)')
    cursor.execute('CREATE INDEX idx_expenses_category ON expenses(category_id)')
    cursor.execute('CREATE INDEX idx_income_daily_user_date ON income_daily(user_id, date)')
    cursor.execute('CREATE INDEX idx_categories_user ON categories(user_id)')
    cursor.execute('CREATE INDEX idx_income_sources_user ON income_sources(user_id)')
    cursor.execute('CREATE INDEX idx_users_email ON users(email)')
    
    conn.commit()
    print("Все таблицы созданы успешно!")
    
    # Показываем созданные таблицы
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"\nСозданные таблицы ({len(tables)}):")
    for table in tables:
        print(f"  - {table[0]}")
    
    conn.close()
    print(f"\nБаза данных создана: {os.path.abspath(db_path)}")

if __name__ == "__main__":
    create_all_tables()