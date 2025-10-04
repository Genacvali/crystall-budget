# Scripts Directory

Автоматизированные скрипты для управления CrystalBudget.

## 📋 Миграции БД

### `backup_db.sh`
Создает резервную копию базы данных.

```bash
./scripts/backup_db.sh
```

**Возможности:**
- Создает timestamped бэкап в `backups/`
- Проверяет целостность бэкапа через `sqlite3 PRAGMA integrity_check`
- Автоматически удаляет старые бэкапы (хранит последние 10)
- Показывает размер БД и бэкапа

**Использование:**
- Перед ручными изменениями БД
- Перед рискованными операциями
- Автоматически вызывается `prod_migrate.sh`

### `prod_baseline.sh`
Создает baseline миграцию для существующей production БД.

```bash
./scripts/prod_baseline.sh
```

**⚠️ Использовать ТОЛЬКО ОДИН РАЗ** при первой настройке миграций на проде!

**Что делает:**
1. Создает бэкап БД
2. Генерирует миграцию на основе текущих моделей
3. Штампует БД текущей ревизией (без изменения схемы)

**После выполнения:**
- Все будущие изменения делай через `flask db migrate`
- Для применения используй `prod_migrate.sh`

### `prod_migrate.sh`
Безопасно применяет миграции на production.

```bash
./scripts/prod_migrate.sh
```

**Что делает:**
1. Показывает текущий статус миграций
2. Создает автоматический бэкап БД
3. Останавливает сервис
4. Показывает план миграции (SQL)
5. Применяет миграции
6. Запускает сервис
7. Проверяет health endpoint

**Безопасность:**
- Требует подтверждения на каждом критическом шаге
- Автоматический rollback при ошибках
- Восстановление из бэкапа при фейле миграции
- Проверка состояния сервиса после миграции

## 🧪 Тестирование

### `run-tests.sh`
Запускает тестовый набор локально.

```bash
./scripts/run-tests.sh                    # Все тесты
./scripts/run-tests.sh --suite api        # Только API тесты
./scripts/run-tests.sh --suite e2e        # Только E2E тесты
./scripts/run-tests.sh --verbose          # Подробный вывод
./scripts/run-tests.sh --stop-on-fail     # Остановка на первой ошибке
```

**Возможности:**
- Автоматическое создание тестовой БД
- Активация venv если нужно
- Установка зависимостей при необходимости
- Поддержка разных test suites

### `ci-check.sh`
CI-совместимый тестовый раннер.

```bash
APP_PORT=5000 APP_CONFIG=testing ./scripts/ci-check.sh --suite all --no-e2e
```

**Опции:**
- `--suite api|e2e|smoke|all` - выбор набора тестов
- `--no-e2e` - пропустить E2E тесты
- `--fast` - быстрые тесты без запуска сервера
- `--verbose` - подробный вывод

## 🚀 Деплой

### `deploy_prod.sh`
Деплой основного приложения на production.

```bash
./scripts/deploy_prod.sh
```

### `setup_production.sh`
Первоначальная настройка production окружения.

```bash
./scripts/setup_production.sh
```

### `rollback_prod.sh`
Откат production деплоя.

```bash
./scripts/rollback_prod.sh
```

### `sync_migrations.sh`
Синхронизация миграций между окружениями.

```bash
./scripts/sync_migrations.sh
```

## 📝 Общие рекомендации

### Права доступа
Все скрипты должны быть исполняемыми:

```bash
chmod +x scripts/*.sh
```

### Переменные окружения
Скрипты используют следующие переменные:

```bash
PROD_PATH="/opt/crystall-budget"  # Путь к проекту
SERVICE_NAME="crystalbudget"       # Имя systemd сервиса
BUDGET_DB="..."                    # URI базы данных
```

### Логирование
Скрипты используют цветной вывод:
- 🟢 Зеленый - успешные операции
- 🟡 Желтый - предупреждения и информация
- 🔴 Красный - ошибки
- 🔵 Синий - информационные сообщения

### Безопасность
- Скрипты проверяют права пользователя
- Требуют подтверждения для критических операций
- Создают бэкапы перед изменениями
- Автоматический rollback при ошибках

## 🆘 Troubleshooting

### Скрипт не запускается
```bash
chmod +x scripts/script_name.sh
```

### Ошибка "Virtual environment not found"
```bash
cd /opt/crystall-budget
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Ошибка "Database not found"
Проверь переменную `BUDGET_DB` и путь к базе:
```bash
echo $BUDGET_DB
ls -la instance/budget.db
```

### Миграция зависла
```bash
# Проверь блокировки
lsof instance/budget.db

# Останови сервис
sudo systemctl stop crystalbudget

# Повтори миграцию
./scripts/prod_migrate.sh
```

## 📚 См. также

- `docs/MIGRATIONS.md` - Полное руководство по миграциям
- `docs/MIGRATIONS_QUICKSTART.md` - Быстрая справка по миграциям
- `scripts/DEPLOYMENT.md` - Руководство по деплою
