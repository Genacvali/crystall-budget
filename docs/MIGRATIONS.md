# Database Migrations Guide

Этот проект использует Flask-Migrate (Alembic) для управления миграциями базы данных.

## Быстрый старт

### Основные команды

```bash
# Посмотреть текущую ревизию
flask db current

# Посмотреть историю миграций
flask db history

# Создать новую миграцию (автогенерация на основе моделей)
flask db migrate -m "Описание изменений"

# Применить все непримененные миграции
flask db upgrade

# Откатить одну миграцию назад
flask db downgrade -1

# Откатить к конкретной ревизии
flask db downgrade <revision_id>

# Посмотреть SQL без применения
flask db upgrade --sql

# Создать пустую миграцию (для data migrations)
flask db revision -m "Описание"
```

## Настройки проекта для SQLite

В этом проекте настроены специальные параметры для корректной работы с SQLite:

- `render_as_batch=True` - обязательно для SQLite, иначе многие ALTER операции не сработают
- `compare_type=True` - отслеживает изменения типов колонок
- `compare_server_default=True` - отслеживает изменения default значений

Эти настройки уже прописаны в `app/__init__.py` и `migrations/env.py`.

## Сценарий 1: Разработка (новая функция)

```bash
# 1. Изменить модели в app/modules/*/models.py
# 2. Создать миграцию
flask db migrate -m "Add user avatar field"

# 3. Проверить сгенерированную миграцию в migrations/versions/
# 4. Применить миграцию
flask db upgrade

# 5. Протестировать
python app.py
```

## Сценарий 2: Production - Первый деплой (базовая миграция)

Если у вас уже есть работающая БД на проде без миграций:

```bash
# На проде

# 1. Сделать бэкап БД
cp /var/lib/crystalbudget/budget.db /var/lib/crystalbudget/backups/budget_backup_$(date +%Y%m%d_%H%M%S).db

# 2. Создать baseline миграцию (пустую)
flask db revision -m "baseline production schema"

# 3. Пометить БД как находящуюся на этой ревизии (без изменений схемы)
flask db stamp head

# 4. Проверить
flask db current
```

Теперь все будущие изменения делайте через миграции.

## Сценарий 3: Production - Обновление существующей БД

```bash
# На локальной машине/staging

# 1. Разработать изменения моделей
# 2. Создать миграцию
flask db migrate -m "Add new column"

# 3. Протестировать на staging
flask db upgrade

# 4. Коммит и пуш в репозиторий
git add migrations/
git commit -m "Add migration: new column"
git push

# На production сервере

# 1. Остановить приложение
sudo systemctl stop crystalbudget

# 2. Сделать бэкап БД
scripts/backup_db.sh

# 3. Обновить код
git pull

# 4. Активировать venv
source .venv/bin/activate

# 5. Применить миграции
flask db upgrade

# 6. Запустить приложение
sudo systemctl start crystalbudget

# 7. Проверить логи
sudo journalctl -u crystalbudget -f

# 8. Проверить версию БД
flask db current
```

## Сценарий 4: Откат миграции (если что-то пошло не так)

```bash
# 1. Остановить приложение
sudo systemctl stop crystalbudget

# 2. Откатить миграцию
flask db downgrade -1

# Или откатить к конкретной ревизии
flask db downgrade <revision_id>

# 3. Восстановить из бэкапа если нужно
cp /var/lib/crystalbudget/backups/budget_backup_XXXXXXXX.db /var/lib/crystalbudget/budget.db

# 4. Запустить приложение
sudo systemctl start crystalbudget
```

## Сценарий 5: Data Migration (изменение данных)

Если нужно не только изменить схему, но и пересчитать/обновить данные:

```bash
# 1. Создать пустую миграцию
flask db revision -m "recalculate user balances"

# 2. Отредактировать файл миграции в migrations/versions/
# 3. Добавить код в функции upgrade() и downgrade()
```

Пример:

```python
def upgrade():
    # Структурное изменение
    op.add_column('users', sa.Column('balance', sa.Numeric(), nullable=True))

    # Пересчет данных
    from app.core.extensions import db
    from app.modules.auth.models import User
    from app.modules.budget.service import BudgetService

    # Получить подключение к БД
    bind = op.get_bind()
    session = db.Session(bind=bind)

    # Пересчитать балансы
    users = session.query(User).all()
    for user in users:
        balance = BudgetService.calculate_user_balance(user.id)
        user.balance = balance

    session.commit()

    # Сделать поле обязательным после заполнения
    op.alter_column('users', 'balance', nullable=False)


def downgrade():
    op.drop_column('users', 'balance')
```

## Частые проблемы и решения

### Миграция не находит изменения моделей

```bash
# Убедитесь что модели импортированы в migrations/env.py
# Проверьте что все модели импортированы в app/__init__.py до инициализации migrate
```

### SQLite ошибки при ALTER TABLE

```bash
# Убедитесь что render_as_batch=True установлен
# Проверьте app/__init__.py и migrations/env.py
```

### Конфликт миграций (две ветки создали миграции)

```bash
# 1. Посмотреть историю
flask db history

# 2. Создать merge миграцию
flask db merge -m "merge heads" <rev1> <rev2>

# 3. Применить
flask db upgrade
```

### Нужно пересоздать все миграции с нуля

```bash
# ТОЛЬКО ДЛЯ DEV! Не делайте на проде!

# 1. Удалить все миграции
rm -rf migrations/versions/*

# 2. Удалить БД
rm instance/budget.db

# 3. Создать новую начальную миграцию
flask db migrate -m "initial schema"

# 4. Применить
flask db upgrade
```

## Best Practices

1. **Всегда проверяйте автогенерированные миграции** - Alembic может что-то пропустить
2. **Тестируйте миграции на staging** - клонируйте prod БД и тестируйте на копии
3. **Делайте бэкапы перед миграцией** - используйте скрипт `scripts/backup_db.sh`
4. **Коммитьте миграции в git** - файлы в `migrations/versions/` это часть кода
5. **Пишите осмысленные сообщения** - `flask db migrate -m "Add user roles and permissions"`
6. **Разделяйте структурные и data миграции** - для больших изменений данных
7. **Делайте миграции обратимыми** - всегда пишите корректный `downgrade()`
8. **Используйте транзакции** - для SQLite они включены по умолчанию

## Автоматизация

Скрипты в `scripts/` для упрощения работы с миграциями:

```bash
# Бэкап БД перед миграцией
./scripts/backup_db.sh

# Применение миграций на проде
./scripts/prod_migrate.sh

# Синхронизация миграций между окружениями
./scripts/sync_migrations.sh
```

## Структура миграции

Каждая миграция - это Python файл в `migrations/versions/`:

```python
"""Description of migration

Revision ID: abc123def456
Revises: xyz789abc012
Create Date: 2024-01-15 14:30:00.123456

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'abc123def456'
down_revision = 'xyz789abc012'  # предыдущая миграция
branch_labels = None
depends_on = None


def upgrade():
    # Изменения для обновления БД
    op.add_column('users', sa.Column('avatar', sa.String(255), nullable=True))


def downgrade():
    # Изменения для отката БД
    op.drop_column('users', 'avatar')
```

## Полезные ссылки

- [Flask-Migrate документация](https://flask-migrate.readthedocs.io/)
- [Alembic документация](https://alembic.sqlalchemy.org/)
- [SQLite ALTER TABLE limitations](https://www.sqlite.org/lang_altertable.html)
