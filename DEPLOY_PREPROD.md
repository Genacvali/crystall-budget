# Деплой на Preprod

## Быстрый деплой

Просто запусти скрипт на сервере:

```bash
cd /opt/crystall-budget
./scripts/deploy_to_preprod.sh
```

Скрипт автоматически:
1. ✅ Создаст все нужные директории
2. ✅ Синхронизирует файлы с dev
3. ✅ Установит правильные permissions
4. ✅ Настроит virtualenv
5. ✅ Применит миграции БД
6. ✅ Перезапустит сервис

## Что делает скрипт

- Копирует проект из `/opt/crystall-budget` в `/opt/preprod/crystall-budget`
- **НЕ трогает** базу данных и аватары (если они уже есть)
- Исключает `.git`, `__pycache__`, `.venv` и другие временные файлы
- Устанавливает владельца `crystal:crystal`
- Создает недостающие директории (`instance`, `logs`, `static/avatars`)

## Ручной деплой (если нужно)

### 1. Создать директории
```bash
sudo mkdir -p /opt/preprod/crystall-budget/{instance,logs,static/avatars}
sudo chown -R crystal:crystal /opt/preprod/crystall-budget
```

### 2. Синхронизировать код
```bash
sudo rsync -av --delete \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='.venv' \
    --exclude='instance/*.db' \
    /opt/crystall-budget/ \
    /opt/preprod/crystall-budget/
```

### 3. Установить зависимости
```bash
cd /opt/preprod/crystall-budget
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 4. Применить миграции
```bash
export BUDGET_DB="sqlite:////opt/preprod/crystall-budget/instance/budget.db"
.venv/bin/flask db upgrade
```

### 5. Перезапустить сервис
```bash
sudo systemctl restart crystalbudget_preprod
sudo journalctl -u crystalbudget_preprod -f
```

## Проверка

После деплоя проверь:
```bash
# Статус сервиса
sudo systemctl status crystalbudget_preprod

# Логи
sudo journalctl -u crystalbudget_preprod -n 50

# Процессы
ps aux | grep python | grep preprod

# Health check (если на порту 5001)
curl http://localhost:5001/healthz
```

## Частые проблемы

### ProtectSystem=strict ошибки
Убедись что директории созданы ДО запуска сервиса:
```bash
sudo mkdir -p /opt/preprod/crystall-budget/instance
sudo chown crystal:crystal /opt/preprod/crystall-budget/instance
```

### Permission denied
```bash
sudo chown -R crystal:crystal /opt/preprod/crystall-budget
sudo chmod -R 755 /opt/preprod/crystall-budget
sudo chmod -R 775 /opt/preprod/crystall-budget/instance
```

### База данных locked
```bash
# Останови сервис
sudo systemctl stop crystalbudget_preprod

# Проверь процессы
ps aux | grep python | grep preprod

# Убей если нужно
sudo pkill -f "python.*preprod"

# Запусти снова
sudo systemctl start crystalbudget_preprod
```
