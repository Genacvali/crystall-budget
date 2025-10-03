# Production Deployment Guide

## Скрипты деплоя

### 0. `sync_migrations.sh` - Синхронизация БД ⚠️ ВАЖНО ДЛЯ ПЕРВОГО ДЕПЛОЯ

**Используйте этот скрипт ПЕРВЫМ ДЕЛОМ**, если у вас уже есть рабочая БД на проде, но миграции не применены.

**Проблема:** БД уже содержит таблицы, но `alembic_version` отсутствует или устарела.

**Что делает:**
1. 🔍 Проверяет существующие таблицы
2. 🔍 Проверяет структуру схемы (какие колонки есть)
3. 🎯 Определяет текущую миграцию автоматически
4. ✅ "Штампует" БД правильной версией миграции
5. 📝 Говорит, нужен ли дальнейший upgrade

**Использование:**
```bash
cd /opt/crystall-budget
export BUDGET_DB="sqlite:////var/lib/crystalbudget/budget.db"
./scripts/sync_migrations.sh
```

**ВАЖНО:** Запустите этот скрипт ПЕРЕД `deploy_prod.sh`, если видите ошибку "table already exists"!

---

### 1. `deploy_prod.sh` - Основной деплой

Применяет миграции базы данных на продакшене.

**Что делает:**
1. ✅ Проверяет виртуальное окружение
2. ✅ Проверяет наличие базы данных
3. ✅ Создаёт бэкап БД (в `backups/`)
4. ✅ Показывает текущую миграцию
5. ✅ Показывает предстоящие SQL-изменения
6. ✅ Спрашивает подтверждение
7. ✅ Применяет миграции (`flask db upgrade`)
8. ✅ Проверяет целостность БД

**Использование:**
```bash
cd /opt/crystall-budget
./scripts/deploy_prod.sh
```

**Требования:**
- Виртуальное окружение в `.venv/`
- База данных по пути `BUDGET_DB` (или дефолтный путь)
- Права на запись в `backups/`

---

### 2. `rollback_prod.sh` - Откат изменений

Откатывает БД к предыдущему состоянию из бэкапа.

**Что делает:**
1. 📋 Показывает список бэкапов
2. ⚠️ Останавливает приложение
3. 💾 Создаёт emergency-бэкап текущего состояния
4. 🔄 Восстанавливает выбранный бэкап
5. ▶️ Запускает приложение

**Использование:**
```bash
cd /opt/crystall-budget
sudo ./scripts/rollback_prod.sh
```

**ВНИМАНИЕ:** Требует `sudo` для остановки/запуска systemd-сервиса!

---

## Пошаговая инструкция деплоя

### Перед деплоем

1. **Убедитесь, что код обновлён:**
   ```bash
   cd /opt/crystall-budget
   git pull origin main
   ```

2. **Проверьте, что виртуальное окружение активировано:**
   ```bash
   source .venv/bin/activate
   ```

3. **Установите зависимости (если есть новые):**
   ```bash
   pip install -r requirements.txt
   ```

### Деплой

1. **Запустите скрипт деплоя:**
   ```bash
   ./scripts/deploy_prod.sh
   ```

2. **Проверьте вывод:**
   - Убедитесь, что показаны правильные миграции
   - Проверьте SQL-изменения
   - Введите `yes` для продолжения

3. **Дождитесь завершения**

### После деплоя

1. **Перезапустите приложение:**
   ```bash
   sudo systemctl restart crystalbudget
   ```

2. **Проверьте логи:**
   ```bash
   sudo journalctl -u crystalbudget -f
   ```

3. **Проверьте работу приложения:**
   - Откройте сайт в браузере
   - Проверьте основные функции
   - Проверьте семейный доступ (если применимо)

---

## Структура бэкапов

```
backups/
├── budget_20251004_120530.db    # Автоматический бэкап перед деплоем
├── budget_20251004_145612.db
└── emergency_20251004_153045.db # Emergency-бэкап при откате
```

**Формат имени:** `budget_YYYYMMDD_HHMMSS.db`

---

## Миграции в проекте

### Текущие миграции:

1. **1b77062a812f** - Initial migration (базовые таблицы)
2. **d06c52a8b6a7** - Add IncomeSource model
3. **add_date_to_income** - Add date to income
4. **515954c99c28** - Add shared budget support
5. **add_shared_budget_to_users** - Add shared_budget_id to users (HEAD)

### Проверить текущую миграцию:
```bash
flask db current
```

### Посмотреть историю:
```bash
flask db history
```

---

## Откат миграций

### Вариант 1: Откат через бэкап (РЕКОМЕНДУЕТСЯ)
```bash
sudo ./scripts/rollback_prod.sh
```

### Вариант 2: Откат через Alembic (сложнее)
```bash
# Откатить одну миграцию назад
flask db downgrade -1

# Откатить к конкретной миграции
flask db downgrade 515954c99c28
```

⚠️ **ВНИМАНИЕ:** При откате через Alembic данные могут быть потеряны!

---

## Устранение проблем

### Проблема: "No such column"
**Причина:** Миграции не применены или применены частично.

**Решение:**
```bash
flask db upgrade
sudo systemctl restart crystalbudget
```

### Проблема: "Database is locked"
**Причина:** Приложение использует БД.

**Решение:**
```bash
sudo systemctl stop crystalbudget
# Выполните операцию
sudo systemctl start crystalbudget
```

### Проблема: "Migration failed"
**Причина:** Ошибка в миграции или конфликт схемы.

**Решение:**
1. Посмотрите логи: `flask db upgrade`
2. Откатитесь к бэкапу: `sudo ./scripts/rollback_prod.sh`
3. Исправьте проблему в коде
4. Повторите деплой

---

## Проверка целостности БД

```bash
# Через SQLite
sqlite3 /opt/crystall-budget/instance/budget.db "PRAGMA integrity_check;"

# Через скрипт (автоматически при деплое)
./scripts/deploy_prod.sh
```

---

## Переменные окружения

- `BUDGET_DB` - путь к БД (по умолчанию: `sqlite:////opt/crystall-budget/instance/budget.db`)
- `SECRET_KEY` - секретный ключ (ОБЯЗАТЕЛЬНО в продакшене!)
- `HTTPS_MODE` - включить HTTPS-режим (рекомендуется: `true`)
- `TELEGRAM_BOT_TOKEN` - токен Telegram-бота

---

## Контрольный чеклист деплоя

- [ ] Код обновлён (`git pull`)
- [ ] Зависимости установлены (`pip install -r requirements.txt`)
- [ ] Запущен скрипт деплоя (`./scripts/deploy_prod.sh`)
- [ ] Миграции применены успешно
- [ ] Приложение перезапущено (`sudo systemctl restart crystalbudget`)
- [ ] Логи проверены (`journalctl -u crystalbudget`)
- [ ] Приложение работает (проверено в браузере)
- [ ] Бэкап создан (проверьте `backups/`)

---

## Контакты и поддержка

При проблемах с деплоем:
1. Проверьте логи: `sudo journalctl -u crystalbudget -n 100`
2. Проверьте статус: `sudo systemctl status crystalbudget`
3. Откатитесь к бэкапу если необходимо
