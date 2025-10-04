# Деплой на Preprod

## 🚨 СРОЧНОЕ ВОССТАНОВЛЕНИЕ (если файлы удалились)

Если скрипт удалил файлы на preprod, немедленно запусти:

```bash
cd /opt/crystall-budget
./scripts/restore_preprod_urgent.sh
```

Это скопирует все файлы с dev на preprod без удалений.

---

## Быстрый деплой

Просто запусти скрипт на сервере:

```bash
cd /opt/crystall-budget
./scripts/deploy_to_preprod.sh
```

**Скрипт теперь безопасный:**
- Показывает preview изменений
- Спрашивает подтверждение
- НЕ удаляет файлы (без --delete)

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

# Удалить сломанный virtualenv если есть
sudo rm -rf .venv

# Создать новый
python3 -m venv .venv
sudo chown -R crystal:crystal .venv

# Установить зависимости
sudo -u crystal .venv/bin/pip install -r requirements.txt
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

### Virtualenv не создается

```bash
# Быстрое решение
cd /opt/preprod/crystall-budget
sudo rm -rf .venv
python3 -m venv .venv
sudo chown -R crystal:crystal .venv
sudo -u crystal .venv/bin/pip install --upgrade pip
sudo -u crystal .venv/bin/pip install -r requirements.txt
```

### Сервис не стартует (NAMESPACE error)

```bash
# Убедись что ВСЕ директории созданы
sudo mkdir -p /opt/preprod/crystall-budget/instance
sudo mkdir -p /opt/preprod/crystall-budget/logs  
sudo mkdir -p /opt/preprod/crystall-budget/static/avatars
sudo chown -R crystal:crystal /opt/preprod/crystall-budget

# Перезапусти
sudo systemctl daemon-reload
sudo systemctl restart crystalbudget_preprod
```
