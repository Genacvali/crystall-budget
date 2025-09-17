-- СРОЧНЫЙ ФИКС: Создание таблицы budget_rollover
-- Выполнить: sqlite3 /path/to/budget.db < URGENT_FIX.sql

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS budget_rollover (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    month TEXT NOT NULL,
    limit_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
    spent_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
    rollover_amount REAL NOT NULL DEFAULT 0.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, category_id, month)
);

-- Индексы для производительности
CREATE INDEX IF NOT EXISTS idx_rollover_user_month 
    ON budget_rollover(user_id, month);

CREATE INDEX IF NOT EXISTS idx_rollover_user_cat 
    ON budget_rollover(user_id, category_id);

-- Добавляем колонку multi_source если её нет
ALTER TABLE categories ADD COLUMN multi_source INTEGER NOT NULL DEFAULT 0;

-- Создаем category_income_sources если её нет  
CREATE TABLE IF NOT EXISTS category_income_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    source_id INTEGER NOT NULL REFERENCES income_sources(id) ON DELETE CASCADE,
    percentage REAL NOT NULL CHECK(percentage > 0 AND percentage <= 100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(category_id, source_id)
);

CREATE INDEX IF NOT EXISTS idx_category_income_sources_category 
    ON category_income_sources(category_id);
CREATE INDEX IF NOT EXISTS idx_category_income_sources_user 
    ON category_income_sources(user_id);