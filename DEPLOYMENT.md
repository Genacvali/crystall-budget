# CrystallBudget Deployment Guide - CentOS 9

Полное руководство по развертыванию CrystallBudget PWA на bare-metal сервере CentOS 9.

## Подготовка сервера

### 1. Установка PostgreSQL 16

```bash
# Репозиторий PGDG
sudo dnf -y install https://download.postgresql.org/pub/repos/yum/reporpms/EL-9-x86_64/pgdg-redhat-repo-latest.noarch.rpm
sudo dnf -y install postgresql16-server postgresql16

# Инициализация кластера
sudo /usr/pgsql-16/bin/postgresql-16-setup initdb
sudo systemctl enable --now postgresql-16
```

### 2. Настройка базы данных

```bash
# Создание БД и пользователя
sudo -u postgres psql <<'SQL'
CREATE USER crystall WITH PASSWORD 'supersecret';
CREATE DATABASE crystall OWNER crystall;
\q
SQL
```

### 3. Тюнинг PostgreSQL под 1GB памяти

```bash
sudo bash -lc 'cat >> /var/lib/pgsql/16/data/postgresql.conf <<EOF

# --- CrystallBudget low-memory ---
listen_addresses = '\''127.0.0.1'\''
max_connections  = 50
shared_buffers   = 128MB
effective_cache_size = 512MB
work_mem        = 4MB
maintenance_work_mem = 128MB
wal_buffers     = 4MB
checkpoint_completion_target = 0.9
default_statistics_target = 100
autovacuum = on
EOF'

sudo systemctl restart postgresql-16
```

### 4. Установка Node.js 20 и Caddy

```bash
# Node.js 20 LTS
curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
sudo dnf -y install nodejs

# EPEL + Caddy
sudo dnf -y install epel-release
sudo dnf -y install caddy
sudo systemctl enable --now caddy
```

## Развертывание приложения

### 1. Создание системного пользователя

```bash
sudo useradd -r -m -d /opt/crystall -s /sbin/nologin crystall
sudo mkdir -p /opt/crystall
sudo chown -R crystall:crystall /opt/crystall
```

### 2. Размещение кода

Скопируйте код в `/opt/crystall` любым удобным способом (git clone, rsync, sftp).

Структура должна быть:
```
/opt/crystall/
├── package.json
├── package-lock.json
├── app/
├── src/
├── prisma/
├── public/
├── next.config.js
└── tsconfig.json
```

### 3. Создание файла окружения

```bash
sudo -u crystall tee /opt/crystall/.env >/dev/null <<'ENV'
NODE_ENV=production
APP_NAME=CrystallBudget
APP_CURRENCY=RUB
NEXTAUTH_URL=https://161-35-31-38.sslip.io
NEXTAUTH_SECRET=change_me_32_chars_random_string_here

# PostgreSQL
DATABASE_URL=postgresql://crystall:supersecret@127.0.0.1:5432/crystall?schema=public
ENV
```

> **Важно**: Замените `NEXTAUTH_SECRET` на случайную строку длиной 32+ символов и `161-35-31-38.sslip.io` на ваш IP в формате sslip.io.

### 4. Сборка приложения

```bash
cd /opt/crystall
sudo -u crystall npm ci --no-audit --no-fund
sudo -u crystall npx prisma generate

# Если есть существующие миграции
sudo -u crystall npx prisma migrate deploy

# Если миграций нет, создайте первую
# sudo -u crystall npx prisma migrate dev --name init

sudo -u crystall npm run build
```

### 5. Создание systemd сервиса

Создайте файл `/etc/systemd/system/crystall.service`:

```ini
[Unit]
Description=CrystallBudget Next.js app
After=network-online.target postgresql-16.service
Wants=network-online.target

[Service]
Type=simple
User=crystall
Group=crystall
WorkingDirectory=/opt/crystall
EnvironmentFile=/opt/crystall/.env
Environment=HOST=127.0.0.1
Environment=PORT=3000
Environment=NODE_OPTIONS=--max-old-space-size=256
ExecStart=/usr/bin/node .next/standalone/server.js
Restart=always
RestartSec=5
MemoryMax=600M
NoNewPrivileges=yes

[Install]
WantedBy=multi-user.target
```

### 6. Запуск приложения

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now crystall
sudo systemctl status crystall --no-pager -l

# Проверка локально
curl -I http://127.0.0.1:3000/
```

## Настройка Caddy (HTTPS)

### 1. Конфигурация Caddyfile

Создайте файл `/etc/caddy/Caddyfile`:

```caddy
# Замените на ваш IP в формате sslip.io
161-35-31-38.sslip.io {
  encode zstd gzip
  reverse_proxy 127.0.0.1:3000

  header {
    Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
    X-Content-Type-Options "nosniff"
    Referrer-Policy "strict-origin-when-cross-origin"
  }
}
```

### 2. Применение конфигурации

```bash
sudo systemctl reload caddy
sudo journalctl -u caddy -n 50 --no-pager
```

В логах должен появиться процесс получения SSL сертификата от Let's Encrypt.

## Обслуживание

### Обновление приложения

```bash
cd /opt/crystall
sudo -u crystall git pull  # или rsync новых файлов
sudo -u crystall npm ci --no-audit --no-fund
sudo -u crystall npx prisma migrate deploy
sudo -u crystall npm run build
sudo systemctl restart crystall
```

### Резервное копирование БД

```bash
# Создание бэкапа
pg_dump -Fc -U crystall crystall > /root/backup/crystall-$(date +%F).dump

# Восстановление
# pg_restore -U crystall -d crystall /root/backup/crystall-2024-01-01.dump
```

### Мониторинг сервисов

```bash
# Статус всех сервисов
sudo systemctl status crystall postgresql-16 caddy

# Логи приложения
sudo journalctl -u crystall -f

# Логи Caddy
sudo journalctl -u caddy -f

# Использование ресурсов
htop
```

### Смена домена

Когда приобретете собственный домен:

1. Настройте A-запись в DNS: `budget.yourdomain.com → ваш_IP`
2. Обновите `/etc/caddy/Caddyfile`: замените sslip.io домен на ваш
3. Обновите `.env`: `NEXTAUTH_URL=https://budget.yourdomain.com`
4. Перезапустите сервисы:
   ```bash
   sudo systemctl reload caddy
   sudo systemctl restart crystall
   ```

## Оптимизация для 1GB памяти

### Лимиты ресурсов
- **Node.js**: 256MB (`--max-old-space-size=256`)
- **Systemd**: 600MB максимум (`MemoryMax=600M`)
- **PostgreSQL**: 128MB shared_buffers, 50 соединений

### Мониторинг памяти
```bash
# Общее использование
free -h

# По процессам
ps aux --sort=-%mem | head -10

# Systemd ограничения
systemctl show crystall --property=MemoryMax,MemoryCurrent
```

## Решение проблем

### Приложение не запускается
```bash
# Проверьте логи
sudo journalctl -u crystall -n 100

# Проверьте права доступа
sudo -u crystall ls -la /opt/crystall
```

### PostgreSQL недоступен
```bash
# Статус службы
sudo systemctl status postgresql-16

# Подключение к БД
sudo -u postgres psql -d crystall -c "SELECT version();"
```

### Caddy не получает сертификат
```bash
# Проверьте доступность портов 80/443
sudo netstat -tlnp | grep -E ':(80|443)'

# Проверьте DNS
nslookup ваш-домен.sslip.io
```

## Безопасность

### Брандмауэр (firewalld)
```bash
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### SELinux
Caddy из репозитория уже имеет правильные контексты SELinux для портов 80/443.

### Регулярные обновления
```bash
# Обновления системы
sudo dnf update

# Обновления Node.js зависимостей
cd /opt/crystall && sudo -u crystall npm audit
```