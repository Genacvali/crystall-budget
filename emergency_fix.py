#!/usr/bin/env python3
"""
СРОЧНЫЙ ФИКС для продакшена - создает недостающую таблицу budget_rollover
"""

import sqlite3
import os
import sys

def find_database():
    """Ищет файл БД в возможных местах"""
    possible_paths = [
        "/opt/crystalbudget/crystall-budget/budget.db",
        "/opt/crystalbudget/budget.db", 
        "/opt/crystall-budget/budget.db",
        "budget.db",
        "./budget.db"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"✅ Найдена БД: {path}")
            return path
    
    print("❌ БД не найдена в стандартных местах")
    print("Ищем по всей системе...")
    
    # Поиск по системе
    import subprocess
    try:
        result = subprocess.run(['find', '/opt', '-name', 'budget.db', '-type', 'f'], 
                              capture_output=True, text=True, timeout=30)
        if result.stdout.strip():
            path = result.stdout.strip().split('\n')[0]
            print(f"✅ Найдена БД: {path}")
            return path
    except:
        pass
    
    return None

def fix_database(db_path):
    """Исправляет БД, добавляя недостающие таблицы"""
    try:
        print(f"🔧 Подключаемся к БД: {db_path}")
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        
        # Проверяем существование budget_rollover
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='budget_rollover'")
        if cursor.fetchone():
            print("✅ Таблица budget_rollover уже существует")
        else:
            print("🔧 Создаем таблицу budget_rollover...")
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
            
            print("✅ Таблица budget_rollover создана успешно!")
        
        # Проверяем category_income_sources
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='category_income_sources'")
        if cursor.fetchone():
            print("✅ Таблица category_income_sources уже существует")
        else:
            print("🔧 Создаем таблицу category_income_sources...")
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
            
            conn.execute("CREATE INDEX IF NOT EXISTS idx_category_income_sources_category ON category_income_sources(category_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_category_income_sources_user ON category_income_sources(user_id)")
            
            print("✅ Таблица category_income_sources создана успешно!")
        
        # Проверяем multi_source колонку
        cursor = conn.execute("PRAGMA table_info(categories)")
        columns = [row[1] for row in cursor.fetchall()]
        if "multi_source" in columns:
            print("✅ Колонка multi_source уже существует")
        else:
            print("🔧 Добавляем колонку multi_source...")
            conn.execute("ALTER TABLE categories ADD COLUMN multi_source INTEGER NOT NULL DEFAULT 0")
            print("✅ Колонка multi_source добавлена!")
        
        conn.commit()
        conn.close()
        
        print("\n🎉 Экстренный фикс БД завершен успешно!")
        print("📋 Теперь нужно перезапустить сервис:")
        print("   sudo systemctl restart crystalbudget")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при исправлении БД: {e}")
        return False

def main():
    print("🚨 ЭКСТРЕННЫЙ ФИКС ПРОДАКШЕНА")
    print("=" * 50)
    
    # Находим БД
    db_path = find_database()
    if not db_path:
        print("❌ Не удалось найти файл БД")
        print("Попробуйте запустить скрипт из директории с budget.db")
        sys.exit(1)
    
    # Создаем резервную копию
    backup_path = f"{db_path}.backup_emergency"
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"💾 Создана резервная копия: {backup_path}")
    except Exception as e:
        print(f"⚠️  Не удалось создать резервную копию: {e}")
        response = input("Продолжить без резервной копии? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Исправляем БД
    if fix_database(db_path):
        print("\n✅ ГОТОВО! Сервис можно перезапускать.")
    else:
        print("\n❌ Не удалось исправить БД")
        sys.exit(1)

if __name__ == "__main__":
    main()