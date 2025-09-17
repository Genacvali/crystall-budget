#!/usr/bin/env python3
"""
Hotfix для продакшена - создает недостающие таблицы
"""

import sqlite3
import os

def create_missing_tables():
    """Создает недостающие таблицы в продакшене"""
    
    # Путь к продакшен БД
    DB_PATH = "/opt/crystalbudget/crystall-budget/budget.db"
    
    if not os.path.exists(DB_PATH):
        print(f"❌ БД не найдена: {DB_PATH}")
        return False
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON")
        
        # Проверяем и создаем budget_rollover таблицу
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='budget_rollover'")
        if not cursor.fetchone():
            print("Creating budget_rollover table...")
            conn.execute("""
            CREATE TABLE budget_rollover (
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
            )
            """)
            
            # Создаем индексы
            conn.execute("CREATE INDEX IF NOT EXISTS idx_budget_rollover_user_category ON budget_rollover(user_id, category_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_budget_rollover_month ON budget_rollover(month)")
            
            print("✅ budget_rollover table created")
        else:
            print("✅ budget_rollover table already exists")
        
        # Проверяем и создаем category_income_sources таблицу
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='category_income_sources'")
        if not cursor.fetchone():
            print("Creating category_income_sources table...")
            conn.execute("""
            CREATE TABLE category_income_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
                source_id INTEGER NOT NULL REFERENCES income_sources(id) ON DELETE CASCADE,
                percentage REAL NOT NULL CHECK(percentage > 0 AND percentage <= 100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(category_id, source_id)
            )
            """)
            
            # Создаем индексы
            conn.execute("CREATE INDEX IF NOT EXISTS idx_category_income_sources_category ON category_income_sources(category_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_category_income_sources_user ON category_income_sources(user_id)")
            
            print("✅ category_income_sources table created")
        else:
            print("✅ category_income_sources table already exists")
        
        # Проверяем и добавляем multi_source колонку
        cursor = conn.execute("PRAGMA table_info(categories)")
        columns = [row[1] for row in cursor.fetchall()]
        if "multi_source" not in columns:
            print("Adding multi_source column to categories...")
            conn.execute("ALTER TABLE categories ADD COLUMN multi_source INTEGER NOT NULL DEFAULT 0")
            print("✅ multi_source column added")
        else:
            print("✅ multi_source column already exists")
        
        conn.commit()
        conn.close()
        
        print("\n🎉 Production database hotfix completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    create_missing_tables()