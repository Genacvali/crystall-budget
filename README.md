# CrystallBudget 💎

Минимальный budget management API + frontend для личного пользования.

## Развертывание на CentOS 9

### 1. Установка зависимостей
```bash
# Node.js 20 LTS
sudo dnf install -y nodejs npm

# PostgreSQL 16
sudo dnf install -y postgresql-server postgresql-contrib
sudo postgresql-setup --initdb
sudo systemctl enable --now postgresql

# Caddy
sudo dnf install -y 'dnf-command(copr)'
sudo dnf copr enable @caddy/caddy -y
sudo dnf install -y caddy
```

### 2. Настройка PostgreSQL
```bash
sudo -u postgres psql
```
```sql
CREATE USER crystall WITH ENCRYPTED PASSWORD 'adminDII';
CREATE DATABASE crystall OWNER crystall;
GRANT ALL PRIVILEGES ON DATABASE crystall TO crystall;
\q
```

### 3. Создание пользователя системы
```bash
sudo useradd -r -m -s /bin/bash crystall
sudo mkdir -p /data/crystall-budget
sudo chown crystall:crystall /data/crystall-budget
```

### 4. Развертывание проекта
```bash
# Скопировать файлы проекта в /data/crystall-budget
sudo cp -r . /data/crystall-budget/
sudo chown -R crystall:crystall /data/crystall-budget

# API
sudo -u crystall bash
cd /data/crystall-budget/api
cp .env.example .env
# Отредактировать .env с правильными данными БД
npm install

# Создать таблицу User
psql "postgres://crystall:adminDII@127.0.0.1:5432/crystall" -c "
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TABLE IF NOT EXISTS \"User\"(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  \"passwordHash\" TEXT NOT NULL
);"

# WEB
cd /data/crystall-budget/web
npm install
npm run build
```

### 5. Systemd сервисы
```bash
# Скопировать service файлы
sudo cp /data/crystall-budget/crystall-api.service /etc/systemd/system/
sudo cp /data/crystall-budget/crystall-web.service /etc/systemd/system/

# Запустить сервисы
sudo systemctl daemon-reload
sudo systemctl enable --now crystall-api
sudo systemctl enable --now crystall-web

# Проверить статус
sudo systemctl status crystall-api
sudo systemctl status crystall-web
```

### 6. Настройка Caddy
```bash
# Отредактировать /etc/caddy/Caddyfile (заменить YOUR-IP на реальный IP)
sudo cp /data/crystall-budget/Caddyfile /etc/caddy/
sudo systemctl reload caddy
```

## Автоматическое развертывание

Используй готовые скрипты для быстрого развертывания:

```bash
# Скачать и развернуть проект (выполнять от root)
sudo ./deploy.sh

# Запустить все сервисы
sudo ./start.sh

# Остановить все сервисы  
sudo ./stop.sh

# Проверить статус
sudo ./status.sh

# Посмотреть логи
sudo ./logs.sh
sudo ./logs.sh api          # только API
sudo ./logs.sh follow web   # мониторинг Web в реальном времени
```

## Проверка работы
```bash
# API
curl http://127.0.0.1:4000/api/health

# Web через Caddy
curl https://crystallbudget.YOUR-IP.sslip.io
```

## Скрипты управления

- **deploy.sh** - полное развертывание с проверкой портов и установкой зависимостей
- **start.sh** - запуск всех сервисов с проверкой статуса
- **stop.sh** - остановка всех сервисов с принудительной очисткой портов
- **status.sh** - детальная проверка состояния системы
- **logs.sh** - просмотр и мониторинг логов