#!/usr/bin/env bash
set -euo pipefail

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "Этот скрипт должен запускаться от root (sudo)"
    fi
}

start_service() {
    local service_name=$1
    local display_name=$2
    
    log "Запуск ${display_name}..."
    
    if systemctl is-active --quiet "${service_name}"; then
        warning "${display_name} уже запущен"
        return 0
    fi
    
    if systemctl start "${service_name}"; then
        sleep 2
        if systemctl is-active --quiet "${service_name}"; then
            success "${display_name} запущен"
        else
            error "Не удалось запустить ${display_name}"
        fi
    else
        error "Ошибка при запуске ${display_name}"
    fi
}

check_ports() {
    log "Проверка портов..."
    
    # Проверяем API (порт 4000)
    if command -v nc &> /dev/null && nc -z 127.0.0.1 4000 2>/dev/null; then
        success "API доступен на порту 4000"
    else
        warning "API не отвечает на порту 4000 (nc не найден или порт закрыт)"
    fi
    
    # Проверяем Web (порт 3000)  
    if command -v nc &> /dev/null && nc -z 127.0.0.1 3000 2>/dev/null; then
        success "Web доступен на порту 3000"
    else
        warning "Web не отвечает на порту 3000 (nc не найден или порт закрыт)"
    fi
}

show_status() {
    echo
    echo -e "${BLUE}=== Статус сервисов ===${NC}"
    
    for service in crystall-api crystall-web caddy; do
        if systemctl is-active --quiet "${service}"; then
            echo -e "${GREEN}✓${NC} ${service}: активен"
        else
            echo -e "${RED}✗${NC} ${service}: неактивен"
        fi
    done
    
    echo
    echo -e "${BLUE}=== Логи (последние 5 строк) ===${NC}"
    echo -e "${YELLOW}API:${NC}"
    journalctl -u crystall-api --no-pager -n 5 || true
    echo
    echo -e "${YELLOW}Web:${NC}"
    journalctl -u crystall-web --no-pager -n 5 || true
}

main() {
    echo -e "${BLUE}"
    echo "=========================================="
    echo "      CrystallBudget Start Script"
    echo "=========================================="
    echo -e "${NC}"
    
    check_root
    
    # Запускаем PostgreSQL если не запущен
    if ! systemctl is-active --quiet postgresql; then
        log "Запуск PostgreSQL..."
        systemctl start postgresql
        success "PostgreSQL запущен"
    fi
    
    # Запускаем основные сервисы
    start_service "crystall-api" "API сервер"
    start_service "crystall-web" "Web сервер"
    start_service "caddy" "Caddy прокси"
    
    # Ждем немного для инициализации
    sleep 3
    
    # Проверяем порты
    check_ports
    
    # Показываем статус
    show_status
    
    echo
    echo -e "${GREEN}=========================================="
    echo "         Все сервисы запущены!"
    echo "==========================================${NC}"
    echo
    
    # Определяем внешний IP и показываем URL
    EXTERNAL_IP=$(curl -s ifconfig.me 2>/dev/null || echo "YOUR-IP")
    if [[ "${EXTERNAL_IP}" != "YOUR-IP" ]]; then
        echo "🌐 URL: https://crystallbudget.${EXTERNAL_IP//./-}.sslip.io"
    else
        echo "🌐 URL: https://crystallbudget.YOUR-IP.sslip.io (замените YOUR-IP)"
    fi
    echo
    echo "📊 Мониторинг:"
    echo "  sudo ./status.sh     - проверить статус"
    echo "  sudo ./logs.sh       - посмотреть логи"
    echo "  sudo ./stop.sh       - остановить сервисы"
}

main "$@"