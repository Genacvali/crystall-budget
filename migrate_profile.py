#!/usr/bin/env python3
"""
Скрипт миграции для добавления полей профиля в таблицу users.
Запустить на сервере: python3 migrate_profile.py
"""

import os
import sqlite3
import sys

DB_PATH = os.environ.get("BUDGET_DB", "budget.db")

def add_profile_columns():
    """Добавляем поля профиля в таблицу users если их нет."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Получаем информацию о структуре таблицы
        cur.execute("PRAGMA table_info(users)")
        columns = {row[1]: row for row in cur.fetchall()}
        print(f"Existing columns: {list(columns.keys())}")
        
        migrations = [
            ("timezone", "ALTER TABLE users ADD COLUMN timezone TEXT DEFAULT 'UTC'"),
            ("locale", "ALTER TABLE users ADD COLUMN locale TEXT DEFAULT 'ru'"), 
            ("default_currency", "ALTER TABLE users ADD COLUMN default_currency TEXT DEFAULT 'RUB'"),
            ("theme", "ALTER TABLE users ADD COLUMN theme TEXT DEFAULT 'light'"),
            ("avatar_path", "ALTER TABLE users ADD COLUMN avatar_path TEXT")
        ]
        
        for column_name, sql in migrations:
            if column_name not in columns:
                try:
                    cur.execute(sql)
                    print(f"✓ Added column: {column_name}")
                except sqlite3.OperationalError as e:
                    print(f"✗ Failed to add column {column_name}: {e}")
            else:
                print(f"- Column {column_name} already exists")
        
        conn.commit()
        print("✓ Profile migration completed successfully")
        
        # Проверяем результат
        cur.execute("PRAGMA table_info(users)")
        final_columns = [row[1] for row in cur.fetchall()]
        print(f"Final columns: {final_columns}")
        
    except Exception as e:
        print(f"✗ Error in profile migration: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print(f"Running profile migration on database: {DB_PATH}")
    add_profile_columns()
    print("Migration completed!")