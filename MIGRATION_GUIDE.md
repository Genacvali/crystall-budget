# Database Migration Guide

Этот документ описывает процесс миграции базы данных из продакшена в текущую схему.

## Быстрый старт

```bash
# 1. Скопируйте продакшн базу данных
cp /path/to/prod/budget.db instance/budget.db

# 2. Запустите миграцию
python migrate_prod_db.py

# 3. Следуйте инструкциям на экране
```

## Что делает скрипт миграции?

Скрипт `migrate_prod_db.py` автоматически:

1. ✅ **Создает резервную копию** базы данных перед миграцией
2. ✅ **Мигрирует данные** из устаревшей колонки `currency` в `default_currency`
3. ✅ **Создает недостающие таблицы**:
   - `budget_rollover` - для хранения переносов бюджета
   - `password_reset_tokens` - для сброса паролей
   - `income_backup_monthly` - резервные копии месячного дохода
   - `income_daily` - ежедневный доход
   - `source_category_rules` - правила распределения доходов
4. ✅ **Создает необходимые индексы** для оптимизации
5. ✅ **Сохраняет все данные** - никакие данные не удаляются

## Использование

### Вариант 1: Автоматическое определение базы данных

Скрипт автоматически найдет базу данных:

```bash
python migrate_prod_db.py
```

База данных будет найдена по пути:
- `$BUDGET_DB` (если установлена переменная окружения)
- `instance/budget.db` (по умолчанию)

### Вариант 2: Указать путь к базе данных

```bash
python migrate_prod_db.py /path/to/your/budget.db
```

### Вариант 3: Миграция с переменной окружения

```bash
export BUDGET_DB="sqlite:////opt/crystall-budget/instance/budget.db"
python migrate_prod_db.py
```

## Безопасность

⚠️ **Важно!** Скрипт создает резервную копию базы данных перед миграцией:

```
instance/budget.db.backup_20251002_123456
```

Если что-то пойдет не так, вы всегда можете восстановить данные:

```bash
# Восстановление из резервной копии
cp instance/budget.db.backup_20251002_123456 instance/budget.db
```

## Проверка после миграции

После миграции рекомендуется проверить:

```bash
# 1. Запустить приложение
python app.py

# 2. Проверить логин пользователя
# 3. Проверить отображение категорий
# 4. Проверить отображение трат
```

## Пример вывода успешной миграции

```
============================================================
DATABASE MIGRATION SCRIPT
============================================================
Database: instance/budget.db

Creating backup: instance/budget.db.backup_20251002_000417
✓ Backup created successfully

Found 14 tables in database

============================================================
1. Checking USERS table...
============================================================
   Current columns: [...]
   ⚠ Found deprecated 'currency' column
   → Migrating data to 'default_currency'...

============================================================
MIGRATION SUMMARY
============================================================

✅ Migration completed successfully!

Changes made (5):
   1. Created table budget_rollover
   2. Created table password_reset_tokens
   3. Created table income_backup_monthly
   4. Created table income_daily
   5. Created table source_category_rules

📦 Backup saved to: instance/budget.db.backup_20251002_000417

✅ All done! Your database is ready to use.
```

## Troubleshooting

### Ошибка: "Database not found"

**Проблема:** Скрипт не может найти базу данных

**Решение:** Укажите путь к базе данных явно:
```bash
python migrate_prod_db.py instance/budget.db
```

### Ошибка: "Permission denied"

**Проблема:** Нет прав на запись в базу данных

**Решение:** Проверьте права доступа:
```bash
chmod 644 instance/budget.db
```

### База данных уже мигрирована

Если скрипт обнаружит, что база уже мигрирована, он покажет:

```
✓ Database is already up to date, no changes needed
```

Это нормально и означает, что повторная миграция не требуется.

## Что НЕ делает скрипт

❌ Скрипт НЕ удаляет старые таблицы (`issues`, `issue_comments`, `category_rules`)
❌ Скрипт НЕ удаляет колонку `currency` (для обратной совместимости)
❌ Скрипт НЕ изменяет существующие данные (кроме копирования `currency` → `default_currency`)

## Дополнительная информация

### Схема базы данных

После миграции ваша база данных будет содержать:

**Основные таблицы:**
- `users` - Пользователи
- `categories` - Категории бюджета
- `expenses` - Расходы
- `income` - Доходы
- `income_sources` - Источники доходов
- `savings_goals` - Цели накоплений
- `shared_budgets` - Семейные бюджеты
- `shared_budget_members` - Участники семейных бюджетов

**Новые таблицы:**
- `budget_rollover` - Переносы бюджета между месяцами
- `password_reset_tokens` - Токены для сброса пароля
- `income_backup_monthly` - Резервные копии месячных доходов
- `income_daily` - Ежедневные доходы
- `source_category_rules` - Правила распределения по категориям

**Служебные таблицы:**
- `exchange_rates` - Курсы валют
- `alembic_version` - Версия миграций

### Поддержка

Если у вас возникли проблемы с миграцией:

1. Проверьте логи скрипта
2. Убедитесь, что резервная копия создана
3. Попробуйте запустить скрипт на копии базы данных для теста
4. Сообщите об ошибке с полным выводом скрипта
