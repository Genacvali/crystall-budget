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

stop_service() {
    local service_name=$1
    local display_name=$2
    
    log "Остановка ${display_name}..."
    
    if ! systemctl is-active --quiet "${service_name}"; then
        warning "${display_name} уже остановлен"
        return 0
    fi
    
    if systemctl stop "${service_name}"; then
        sleep 2
        if ! systemctl is-active --quiet "${service_name}"; then
            success "${display_name} остановлен"
        else
            error "Не удалось остановить ${display_name}"
        fi
    else
        error "Ошибка при остановке ${display_name}"
    fi
}

force_kill_ports() {
    log "Проверка и принудительное освобождение портов..."
    
    # Проверяем и убиваем процессы на портах 3000 и 4000
    for port in 3000 4000; do
        local pid=$(lsof -ti:${port} 2>/dev/null || true)
        if [[ -n "${pid}" ]]; then
            warning "Процесс на порту ${port} (PID: ${pid}) будет принудительно завершен"
            kill -9 ${pid} 2>/dev/null || true
            success "Порт ${port} освобожден"
        fi
    done
}

show_final_status() {
    echo
    echo -e "${BLUE}=== Финальный статус сервисов ===${NC}"
    
    local all_stopped=true
    
    for service in crystall-api crystall-web caddy; do
        if systemctl is-active --quiet "${service}"; then
            echo -e "${YELLOW}⚠${NC} ${service}: все еще активен"
            all_stopped=false
        else
            echo -e "${GREEN}✓${NC} ${service}: остановлен"
        fi
    done
    
    if [[ "${all_stopped}" == "true" ]]; then
        success "Все сервисы успешно остановлены"
    else
        warning "Некоторые сервисы все еще активны"
    fi
}

main() {
    echo -e "${BLUE}"
    echo "=========================================="
    echo "       CrystallBudget Stop Script"
    echo "=========================================="
    echo -e "${NC}"
    
    check_root
    
    # Останавливаем сервисы в обратном порядке
    stop_service "caddy" "Caddy прокси"
    stop_service "crystall-web" "Web сервер"
    stop_service "crystall-api" "API сервер"
    
    # Принудительно освобождаем порты
    force_kill_ports
    
    # Показываем финальный статус
    show_final_status
    
    echo
    echo -e "${GREEN}=========================================="
    echo "         Все сервисы остановлены!"
    echo "==========================================${NC}"
    echo
    echo "Для повторного запуска используйте:"
    echo "  sudo ./start.sh"
    echo
    echo "Для полной переустановки:"
    echo "  sudo ./deploy.sh"
}

main "$@"