-- ЭКСТРЕННЫЙ ФИКС: создание недостающих таблиц
-- Выполнить: sqlite3 /path/to/budget.db < fix.sql

-- Создаем таблицу budget_rollover
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

-- Создаем индексы для budget_rollover
CREATE INDEX IF NOT EXISTS idx_budget_rollover_user_category ON budget_rollover(user_id, category_id);
CREATE INDEX IF NOT EXISTS idx_budget_rollover_month ON budget_rollover(month);

-- Создаем таблицу category_income_sources
CREATE TABLE IF NOT EXISTS category_income_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    source_id INTEGER NOT NULL REFERENCES income_sources(id) ON DELETE CASCADE,
    percentage REAL NOT NULL CHECK(percentage > 0 AND percentage <= 100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(category_id, source_id)
);

-- Создаем индексы для category_income_sources
CREATE INDEX IF NOT EXISTS idx_category_income_sources_category ON category_income_sources(category_id);
CREATE INDEX IF NOT EXISTS idx_category_income_sources_user ON category_income_sources(user_id);

-- Добавляем колонку multi_source (может выдать ошибку если уже существует - это нормально)
ALTER TABLE categories ADD COLUMN multi_source INTEGER NOT NULL DEFAULT 0;