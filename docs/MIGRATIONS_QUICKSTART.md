# Миграции - Быстрая справка

## 🚀 Основные команды

```bash
# Статус и история
flask db current        # Текущая ревизия
flask db history        # История миграций

# Разработка
flask db migrate -m "Add user field"  # Создать миграцию
flask db upgrade                      # Применить миграции
flask db downgrade -1                 # Откатить на 1 шаг

# Production
./scripts/prod_migrate.sh    # Безопасная миграция на проде
./scripts/backup_db.sh        # Бэкап БД
```

## 📋 Сценарии использования

### 1️⃣ Первый запуск на продакшене (есть БД, нет миграций)

```bash
# Один раз!
./scripts/prod_baseline.sh

# Далее используй обычный workflow
```

### 2️⃣ Добавление нового поля в модель

```bash
# 1. Изменить модель (например, app/modules/auth/models.py)
class User(db.Model):
    # ...
    avatar_url = db.Column(db.String(500))  # новое поле

# 2. Создать миграцию
flask db migrate -m "Add avatar_url to users"

# 3. Проверить файл миграции в migrations/versions/

# 4. Применить локально
flask db upgrade

# 5. Тест
python app.py

# 6. Коммит
git add migrations/versions/
git commit -m "Add avatar_url field"
git push
```

### 3️⃣ Деплой миграции на прод

```bash
# На проде
cd /opt/crystalbudget/crystall-budget
git pull
./scripts/prod_migrate.sh  # Все сделает автоматически:
                            # - бэкап
                            # - остановка
                            # - миграция
                            # - запуск
```

### 4️⃣ Data Migration (изменение данных)

```bash
# 1. Создать пустую миграцию
flask db revision -m "recalculate balances"

# 2. Отредактировать файл миграции
# migrations/versions/XXXXXX_recalculate_balances.py

def upgrade():
    from app.core.extensions import db
    from app.modules.auth.models import User

    bind = op.get_bind()
    session = db.Session(bind=bind)

    # Твоя логика
    users = session.query(User).all()
    for user in users:
        user.balance = calculate_balance(user)

    session.commit()

def downgrade():
    pass  # или логика отката

# 3. Применить
flask db upgrade
```

### 5️⃣ Откат если что-то пошло не так

```bash
# На проде
sudo systemctl stop crystalbudget

# Откат миграции
flask db downgrade -1

# Или восстановление из бэкапа
cp backups/budget_backup_20241004_120000.db instance/budget.db

sudo systemctl start crystalbudget
```

## ⚠️ Важные правила

1. **Всегда тестируй миграции локально** перед продом
2. **Бэкап обязателен** - скрипты делают автоматически
3. **Проверяй автогенерированные миграции** - Alembic не идеален
4. **Коммить миграции в git** - это часть кода
5. **Не редактируй примененные миграции** - только новые
6. **Пиши downgrade()** - для возможности отката

## 🔧 Настройки проекта

Проект уже настроен для SQLite:

- ✅ `render_as_batch=True` - для ALTER операций
- ✅ `compare_type=True` - отслеживание типов
- ✅ `compare_server_default=True` - отслеживание defaults
- ✅ Timestamp в именах файлов миграций
- ✅ Автоматические бэкапы в скриптах

## 📚 Полная документация

См. `docs/MIGRATIONS.md` для детального руководства.

## 🆘 Помощь

```bash
flask db --help           # Справка по командам
flask db migrate --help   # Справка по migrate
flask db upgrade --help   # Справка по upgrade
```

## 🎯 Чеклист для production миграции

- [ ] Миграция протестирована локально
- [ ] Миграция добавлена в git
- [ ] Есть свежий бэкап БД (скрипт сделает)
- [ ] Проверено что downgrade() работает
- [ ] Уведомлены пользователи о downtime (если есть)
- [ ] Запущен `./scripts/prod_migrate.sh`
- [ ] Проверены логи после миграции
- [ ] Протестирована работа приложения
