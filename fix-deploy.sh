#!/usr/bin/env bash
set -euo pipefail

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_DIR="/data/crystall-budget"
DB_USER="crystall"

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
    exit 1
}

log "Исправление развертывания..."

# Проверяем текущую директорию
current_dir="$(pwd)"
log "Текущая директория: ${current_dir}"

# Проверяем наличие api и web папок
if [[ ! -d "api" ]] || [[ ! -d "web" ]]; then
    error "Папки api/ или web/ не найдены в текущей директории"
fi

# Создаем целевую директорию если не существует
mkdir -p "${PROJECT_DIR}"

# Копируем файлы
log "Копирование файлов..."
cp -r api web *.sh *.service Caddyfile README.md CLAUDE.md "${PROJECT_DIR}/" 2>/dev/null

# Проверяем что скопировалось
if [[ ! -d "${PROJECT_DIR}/api" ]]; then
    error "Директория API не найдена после копирования"
fi

if [[ ! -d "${PROJECT_DIR}/web" ]]; then
    error "Директория Web не найдена после копирования"
fi

# Устанавливаем права
chown -R "${DB_USER}:${DB_USER}" "${PROJECT_DIR}"
success "Файлы скопированы в ${PROJECT_DIR}"

# Переходим в проект и продолжаем установку
cd "${PROJECT_DIR}"

# API setup
log "Установка зависимостей API..."
cd api

if [[ ! -f .env ]]; then
    cp .env.example .env
    sed -i "s/user:password/crystall:adminDII/g" .env
    sed -i "s/\/crystall/\/crystall/g" .env
    chown "${DB_USER}:${DB_USER}" .env
    success ".env файл создан"
fi

sudo -u "${DB_USER}" npm install
success "Зависимости API установлены"

# Web setup
log "Установка зависимостей Web..."
cd ../web
sudo -u "${DB_USER}" npm install
sudo -u "${DB_USER}" npm run build
success "Web приложение собрано"

# Systemd setup
log "Настройка systemd сервисов..."
cd ..
cp crystall-api.service /etc/systemd/system/
cp crystall-web.service /etc/systemd/system/
systemctl daemon-reload
success "Systemd сервисы настроены"

# Caddy setup
log "Настройка Caddy..."
EXTERNAL_IP=$(curl -s ifconfig.me || echo "161-35-31-38")
sed "s/YOUR-IP/${EXTERNAL_IP//./-}/g" Caddyfile > /etc/caddy/Caddyfile
success "Caddy настроен"

echo
echo -e "${GREEN}=========================================="
echo "           Исправление завершено!"
echo "==========================================${NC}"
echo
echo "Теперь можно запускать:"
echo "  sudo ./start.sh"