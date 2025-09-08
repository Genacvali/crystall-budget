"""Database operations and migrations."""

import sqlite3
import os
from datetime import datetime
from flask import current_app


def get_db():
    """Get database connection with Row factory."""
    conn = sqlite3.connect(current_app.config['DB_PATH'])
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Initialize database with basic schema."""
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            value REAL NOT NULL,
            limit_type TEXT DEFAULT 'fixed' CHECK(limit_type IN ('fixed','percent')),
            UNIQUE(user_id, name)
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            date TEXT NOT NULL,
            month TEXT NOT NULL,
            category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
            amount REAL NOT NULL,
            note TEXT
        );

        CREATE TABLE IF NOT EXISTS income_daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            date TEXT NOT NULL,
            amount REAL NOT NULL,
            source_id INTEGER REFERENCES income_sources(id)
        );

        CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses(user_id, date DESC);
        CREATE INDEX IF NOT EXISTS idx_expenses_user_month ON expenses(user_id, month);
        CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category_id);
        CREATE INDEX IF NOT EXISTS idx_categories_user ON categories(user_id);
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_income_daily_user_date ON income_daily(user_id, date DESC);
        CREATE INDEX IF NOT EXISTS idx_income_daily_source ON income_daily(source_id);
        """
    )
    conn.commit()
    conn.close()


def migrate_income_to_daily_if_needed():
    """
    Если есть старая схема income (user_id, month, amount),
    переносим в новую income_daily с датой = month-01.
    """
    conn = get_db()
    cur = conn.cursor()

    # уже мигрировано?
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='income_daily'"
    )
    if cur.fetchone():
        conn.close()
        return

    # есть ли вообще income?
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='income'")
    income_exists = cur.fetchone() is not None

    # создаём новую таблицу (если нет)
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS income_daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            date TEXT NOT NULL,   -- YYYY-MM-DD
            amount REAL NOT NULL,
            source_id INTEGER REFERENCES income_sources(id)
        );

        -- Income indexes
        CREATE INDEX IF NOT EXISTS idx_income_daily_user_date ON income_daily(user_id, date DESC);
        CREATE INDEX IF NOT EXISTS idx_income_daily_source ON income_daily(source_id);
        """
    )

    if income_exists:
        # проверим колонки старой income
        cur.execute("PRAGMA table_info(income)")
        cols = [r[1] for r in cur.fetchall()]

        if "month" in cols and "amount" in cols:
            # переносим: month -> date = month-01
            cur.execute("SELECT user_id, month, amount FROM income")
            rows = cur.fetchall()
            for uid, month, amount in rows:
                if month and len(month) == 7:
                    date_str = f"{month}-01"
                else:
                    date_str = datetime.now().strftime("%Y-%m-01")
                cur.execute(
                    "INSERT INTO income_daily (user_id, date, amount) VALUES (?, ?, ?)",
                    (uid, date_str, amount),
                )
            # сохраним бэкап старой таблицы
            cur.executescript("ALTER TABLE income RENAME TO income_backup_monthly;")

    conn.commit()
    conn.close()


def ensure_income_sources_tables():
    """Создаём таблицы источников и правил, если их нет."""
    conn = get_db()
    cur = conn.cursor()
    # таблица источников доходов
    cur.execute("""
    CREATE TABLE IF NOT EXISTS income_sources (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      name TEXT NOT NULL,
      is_default INTEGER NOT NULL DEFAULT 0,
      UNIQUE(user_id, name)
    )
    """)
    # таблица правил маршрутизации расходов
    cur.execute("""
    CREATE TABLE IF NOT EXISTS source_category_rules (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      source_id INTEGER NOT NULL REFERENCES income_sources(id) ON DELETE CASCADE,
      category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
      priority INTEGER NOT NULL DEFAULT 100,
      UNIQUE(user_id, category_id)
    )
    """)
    
    conn.commit()
    conn.close()


def add_source_id_column_if_missing():
    """Добавляет колонку source_id в income_daily, если её нет."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(income_daily)")
    cols = [r[1] for r in cur.fetchall()]
    if "source_id" not in cols:
        try:
            cur.execute("ALTER TABLE income_daily ADD COLUMN source_id INTEGER REFERENCES income_sources(id)")
            conn.commit()
        except sqlite3.OperationalError:
            pass
    conn.close()


def add_category_type_column_if_missing():
    """Добавляет колонку category_type в categories, если её нет."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(categories)")
    cols = [r[1] for r in cur.fetchall()]
    if "category_type" not in cols:
        try:
            cur.execute("ALTER TABLE categories ADD COLUMN category_type TEXT DEFAULT 'expense' CHECK(category_type IN ('expense','income'))")
            conn.commit()
            current_app.logger.info("Added category_type column to categories table")
        except sqlite3.OperationalError as e:
            current_app.logger.error(f"Failed to add category_type column: {e}")
    conn.close()


def add_currency_columns_if_missing():
    """Добавляет колонки currency в expenses и income_daily, если их нет."""
    conn = get_db()
    cur = conn.cursor()
    
    # Проверяем expenses
    try:
        cur.execute("ALTER TABLE expenses ADD COLUMN currency TEXT DEFAULT 'RUB'")
        current_app.logger.info("Added currency column to expenses table")
    except Exception:
        pass  # Колонка уже существует или ошибка
    
    # Проверяем income_daily
    try:
        cur.execute("ALTER TABLE income_daily ADD COLUMN currency TEXT DEFAULT 'RUB'")
        current_app.logger.info("Added currency column to income_daily table")
    except Exception:
        pass  # Колонка уже существует или ошибка
    
    conn.commit()
    conn.close()


def add_profile_columns_if_missing():
    """Добавляет дополнительные колонки профиля в users, если их нет."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(users)")
    cols = [r[1] for r in cur.fetchall()]
    
    migrations = []
    if "timezone" not in cols:
        migrations.append("ALTER TABLE users ADD COLUMN timezone TEXT DEFAULT 'UTC'")
    if "locale" not in cols:
        migrations.append("ALTER TABLE users ADD COLUMN locale TEXT DEFAULT 'ru'")
    if "default_currency" not in cols:
        migrations.append("ALTER TABLE users ADD COLUMN default_currency TEXT DEFAULT 'RUB'")
    if "theme" not in cols:
        migrations.append("ALTER TABLE users ADD COLUMN theme TEXT DEFAULT 'light'")
    if "avatar_path" not in cols:
        migrations.append("ALTER TABLE users ADD COLUMN avatar_path TEXT")
    
    for migration in migrations:
        try:
            cur.execute(migration)
            current_app.logger.info(f"Profile migration: {migration}")
        except sqlite3.OperationalError as e:
            current_app.logger.error(f"Profile migration failed: {migration}, error: {e}")
    
    conn.commit()
    conn.close()
    current_app.logger.info("Profile columns migration completed successfully")


def ensure_new_tables():
    """Создание новых таблиц для дополнительной функциональности."""
    conn = get_db()
    cur = conn.cursor()
    
    # Таблица savings_goals
    cur.execute("""
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
    """)
    
    # Таблица shared_budgets
    cur.execute("""
    CREATE TABLE IF NOT EXISTS shared_budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        creator_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        invite_code TEXT UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Таблица shared_budget_members
    cur.execute("""
    CREATE TABLE IF NOT EXISTS shared_budget_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        budget_id INTEGER NOT NULL REFERENCES shared_budgets(id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        role TEXT NOT NULL DEFAULT 'member' CHECK(role IN ('admin', 'member')),
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(budget_id, user_id)
    )
    """)
    
    # Таблица exchange_rates
    cur.execute("""
    CREATE TABLE IF NOT EXISTS exchange_rates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_currency TEXT NOT NULL,
        to_currency TEXT NOT NULL,
        rate DECIMAL(10,6) NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(from_currency, to_currency)
    )
    """)
    
    conn.commit()
    conn.close()
    current_app.logger.info("New tables migration completed successfully")


# Helper functions
def get_default_source_id(conn, user_id):
    """Get default income source ID for user."""
    row = conn.execute(
        "SELECT id FROM income_sources WHERE user_id=? AND is_default=1",
        (user_id,)
    ).fetchone()
    return row["id"] if row else None


def get_source_for_category(conn, user_id, category_id):
    """Get source ID for category rule."""
    row = conn.execute(
        "SELECT source_id FROM source_category_rules WHERE user_id=? AND category_id=?",
        (user_id, category_id)
    ).fetchone()
    return row["source_id"] if row else None