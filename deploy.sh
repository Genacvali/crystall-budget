#!/usr/bin/env bash
set -euo pipefail

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Конфигурация
PROJECT_DIR="/data/crystall-budget"
API_PORT="4000"
WEB_PORT="3000"
DB_USER="crystall"
DB_PASS="adminDII"
DB_NAME="crystall"

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
    exit 1
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "Этот скрипт должен запускаться от root (sudo)"
    fi
}

check_ports() {
    log "Проверка занятых портов..."
    
    if netstat -tuln | grep -q ":${API_PORT} "; then
        warning "Порт ${API_PORT} занят:"
        netstat -tuln | grep ":${API_PORT} "
        read -p "Продолжить? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        success "Порт ${API_PORT} свободен"
    fi
    
    if netstat -tuln | grep -q ":${WEB_PORT} "; then
        warning "Порт ${WEB_PORT} занят:"
        netstat -tuln | grep ":${WEB_PORT} "
        read -p "Продолжить? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        success "Порт ${WEB_PORT} свободен"
    fi
}

install_dependencies() {
    log "Установка системных зависимостей..."
    
    # Node.js 20 LTS
    if ! command -v node &> /dev/null; then
        log "Установка Node.js..."
        dnf install -y nodejs npm
        success "Node.js установлен"
    else
        success "Node.js уже установлен: $(node --version)"
    fi
    
    # PostgreSQL
    if ! command -v psql &> /dev/null; then
        log "Установка PostgreSQL..."
        dnf install -y postgresql-server postgresql-contrib
        postgresql-setup --initdb
        systemctl enable --now postgresql
        success "PostgreSQL установлен"
    else
        success "PostgreSQL уже установлен"
    fi
    
    # Caddy
    if ! command -v caddy &> /dev/null; then
        log "Установка Caddy..."
        dnf install -y 'dnf-command(copr)' || true
        dnf copr enable -y @caddy/caddy || true
        dnf install -y caddy
        systemctl enable caddy
        success "Caddy установлен"
    else
        success "Caddy уже установлен: $(caddy version)"
    fi
}

setup_database() {
    log "Настройка базы данных..."
    
    # Проверяем, существует ли пользователь
    if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1; then
        success "Пользователь ${DB_USER} уже существует"
    else
        log "Создание пользователя ${DB_USER}..."
        sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH ENCRYPTED PASSWORD '${DB_PASS}';"
        success "Пользователь ${DB_USER} создан"
    fi
    
    # Проверяем, существует ли база
    if sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1; then
        success "База данных ${DB_NAME} уже существует"
    else
        log "Создание базы данных ${DB_NAME}..."
        sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"
        sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"
        success "База данных ${DB_NAME} создана"
    fi
    
    # Создаем таблицы
    log "Создание таблиц..."
    sudo -u postgres psql -d "${DB_NAME}" -c "
        CREATE EXTENSION IF NOT EXISTS pgcrypto;
        CREATE TABLE IF NOT EXISTS \"User\"(
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email TEXT UNIQUE NOT NULL,
            \"passwordHash\" TEXT NOT NULL
        );
    " || warning "Возможно, таблицы уже существуют"
    
    success "База данных настроена"
}

setup_user() {
    log "Создание системного пользователя..."
    
    if id "${DB_USER}" &>/dev/null; then
        success "Пользователь ${DB_USER} уже существует"
    else
        useradd -r -m -s /bin/bash "${DB_USER}"
        success "Пользователь ${DB_USER} создан"
    fi
    
    mkdir -p "${PROJECT_DIR}"
    chown "${DB_USER}:${DB_USER}" "${PROJECT_DIR}"
}

deploy_project() {
    log "Развертывание проекта..."
    
    # Копируем файлы
    if [[ -d "${PROJECT_DIR}" ]]; then
        log "Очистка старого проекта..."
        rm -rf "${PROJECT_DIR}"/*
    fi
    
    cp -r ./* "${PROJECT_DIR}/" 2>/dev/null || true
    chown -R "${DB_USER}:${DB_USER}" "${PROJECT_DIR}"
    
    # Настройка API
    log "Установка зависимостей API..."
    cd "${PROJECT_DIR}/api"
    
    # Создаем .env если не существует
    if [[ ! -f .env ]]; then
        cp .env.example .env
        sed -i "s/user:password/${DB_USER}:${DB_PASS}/g" .env
        sed -i "s/\/crystall/\/${DB_NAME}/g" .env
        chown "${DB_USER}:${DB_USER}" .env
        success ".env файл создан"
    fi
    
    sudo -u "${DB_USER}" npm install
    success "Зависимости API установлены"
    
    # Настройка Web
    log "Установка зависимостей Web..."
    cd "${PROJECT_DIR}/web"
    sudo -u "${DB_USER}" npm install
    sudo -u "${DB_USER}" npm run build
    success "Web приложение собрано"
}

setup_services() {
    log "Настройка systemd сервисов..."
    
    # Копируем service файлы
    cp "${PROJECT_DIR}/crystall-api.service" /etc/systemd/system/
    cp "${PROJECT_DIR}/crystall-web.service" /etc/systemd/system/
    
    systemctl daemon-reload
    success "Systemd сервисы настроены"
}

setup_caddy() {
    log "Настройка Caddy..."
    
    # Получаем внешний IP
    EXTERNAL_IP=$(curl -s ifconfig.me || curl -s ipinfo.io/ip || echo "YOUR-IP")
    DOMAIN="crystallbudget.${EXTERNAL_IP//./-}.sslip.io"
    
    # Обновляем Caddyfile
    sed "s/YOUR-IP/${EXTERNAL_IP//./-}/g" "${PROJECT_DIR}/Caddyfile" > /etc/caddy/Caddyfile
    
    success "Caddy настроен для домена: ${DOMAIN}"
}

main() {
    echo -e "${BLUE}"
    echo "=========================================="
    echo "    CrystallBudget Deployment Script"
    echo "=========================================="
    echo -e "${NC}"
    
    check_root
    check_ports
    install_dependencies
    setup_database
    setup_user
    deploy_project
    setup_services
    setup_caddy
    
    echo
    echo -e "${GREEN}=========================================="
    echo "           Развертывание завершено!"
    echo "==========================================${NC}"
    echo
    echo "Для управления сервисами используйте:"
    echo "  ./start.sh  - запустить сервисы"
    echo "  ./stop.sh   - остановить сервисы"
    echo
    echo "Проверить статус:"
    echo "  systemctl status crystall-api"
    echo "  systemctl status crystall-web"
    echo
    EXTERNAL_IP=$(curl -s ifconfig.me 2>/dev/null || echo "YOUR-IP")
    echo "URL: https://crystallbudget.${EXTERNAL_IP//./-}.sslip.io"
}

main "$@"