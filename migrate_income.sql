-- Income table migration script
-- Goal: Add autoincrement PRIMARY KEY id and align with Income model structure
-- Created: 2025-09-24

-- Step 1: Create new table with correct structure
CREATE TABLE income_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    source_name TEXT NOT NULL,
    amount NUMERIC(10,2) NOT NULL,
    currency TEXT NOT NULL DEFAULT 'RUB',
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Step 2: Migrate existing data from old income table
-- Note: Since old table only has user_id, month (TEXT), amount
-- We need to map old structure to new structure:
-- - Extract year and month from old month field (assuming format YYYY-MM)
-- - Set default values for missing fields
INSERT INTO income_new (user_id, source_name, amount, currency, year, month, created_at)
SELECT 
    user_id,
    'Основной доход' as source_name,  -- Default source name
    amount,
    'RUB' as currency,               -- Default currency
    CAST(substr(month, 1, 4) AS INTEGER) as year,
    CAST(substr(month, 6, 2) AS INTEGER) as month,
    CURRENT_TIMESTAMP as created_at
FROM income
WHERE month IS NOT NULL 
  AND length(month) >= 7 
  AND substr(month, 5, 1) = '-';

-- Step 3: Handle any records that don't match YYYY-MM format
-- Insert them with default year/month values
INSERT INTO income_new (user_id, source_name, amount, currency, year, month, created_at)
SELECT 
    user_id,
    'Основной доход' as source_name,
    amount,
    'RUB' as currency,
    2025 as year,                    -- Default to current year
    1 as month,                      -- Default to January
    CURRENT_TIMESTAMP as created_at
FROM income
WHERE month IS NULL 
   OR length(month) < 7 
   OR substr(month, 5, 1) != '-';

-- Step 4: Drop old table
DROP TABLE income;

-- Step 5: Rename new table
ALTER TABLE income_new RENAME TO income;

-- Step 6: Create indexes for performance
CREATE INDEX idx_income_user_year_month ON income(user_id, year, month);
CREATE INDEX idx_income_user_source ON income(user_id, source_name);

-- Step 7: Create unique constraint as defined in model
CREATE UNIQUE INDEX idx_income_unique ON income(user_id, source_name, year, month);

-- Migration completed
-- Summary: 
-- - Added INTEGER PRIMARY KEY id with autoincrement
-- - Added source_name, currency, year, month, created_at columns
-- - Converted old month TEXT to separate year/month integers
-- - Added performance indexes
-- - Added unique constraint to prevent duplicates