#!/usr/bin/env bash
set -euo pipefail

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

LINES=${1:-50}  # По умолчанию показываем 50 последних строк

show_service_logs() {
    local service_name=$1
    local display_name=$2
    
    echo -e "${BLUE}=== Логи ${display_name} (последние ${LINES} строк) ===${NC}"
    
    if systemctl is-active --quiet "${service_name}"; then
        echo -e "${GREEN}✓ Сервис активен${NC}"
    else
        echo -e "${YELLOW}⚠ Сервис неактивен${NC}"
    fi
    
    echo -e "${CYAN}Команда: journalctl -u ${service_name} -n ${LINES}${NC}"
    echo "---"
    
    journalctl -u "${service_name}" -n "${LINES}" --no-pager -o short-precise 2>/dev/null || {
        echo -e "${RED}Ошибка получения логов для ${service_name}${NC}"
    }
    
    echo
}

show_error_logs() {
    echo -e "${BLUE}=== Ошибки (последние ${LINES} строк) ===${NC}"
    
    echo -e "${CYAN}API ошибки:${NC}"
    journalctl -u crystall-api -p err -n "${LINES}" --no-pager -o short-precise 2>/dev/null | head -20 || {
        echo "Нет ошибок API"
    }
    
    echo
    echo -e "${CYAN}Web ошибки:${NC}"
    journalctl -u crystall-web -p err -n "${LINES}" --no-pager -o short-precise 2>/dev/null | head -20 || {
        echo "Нет ошибок Web"
    }
    
    echo
}

follow_logs() {
    local service=$1
    
    echo -e "${BLUE}=== Мониторинг логов ${service} (Ctrl+C для выхода) ===${NC}"
    journalctl -u "${service}" -f --no-pager -o short-precise
}

show_help() {
    echo -e "${BLUE}Использование:${NC}"
    echo "  ./logs.sh                  - все логи (50 строк)"
    echo "  ./logs.sh 100              - все логи (100 строк)"
    echo "  ./logs.sh api              - только API логи"
    echo "  ./logs.sh web              - только Web логи"
    echo "  ./logs.sh caddy            - только Caddy логи"
    echo "  ./logs.sh errors           - только ошибки"
    echo "  ./logs.sh follow api       - мониторинг API (в реальном времени)"
    echo "  ./logs.sh follow web       - мониторинг Web"
    echo
}

main() {
    case "${1:-all}" in
        "help"|"-h"|"--help")
            show_help
            ;;
        "follow")
            if [[ -n "${2:-}" ]]; then
                follow_logs "crystall-${2}"
            else
                echo -e "${RED}Укажите сервис для мониторинга: api, web, или caddy${NC}"
                exit 1
            fi
            ;;
        "api")
            show_service_logs "crystall-api" "API сервера"
            ;;
        "web")
            show_service_logs "crystall-web" "Web сервера"
            ;;
        "caddy")
            show_service_logs "caddy" "Caddy прокси"
            ;;
        "errors")
            show_error_logs
            ;;
        [0-9]*)
            LINES=$1
            echo -e "${BLUE}"
            echo "=========================================="
            echo "     CrystallBudget Logs (${LINES} строк)"
            echo "=========================================="
            echo -e "${NC}"
            
            show_service_logs "crystall-api" "API сервера"
            show_service_logs "crystall-web" "Web сервера"
            show_service_logs "caddy" "Caddy прокси"
            ;;
        *)
            echo -e "${BLUE}"
            echo "=========================================="
            echo "     CrystallBudget Logs (${LINES} строк)"
            echo "=========================================="
            echo -e "${NC}"
            
            show_service_logs "crystall-api" "API сервера"
            show_service_logs "crystall-web" "Web сервера"
            show_service_logs "caddy" "Caddy прокси"
            
            echo -e "${YELLOW}Используйте './logs.sh help' для просмотра всех опций${NC}"
            ;;
    esac
}

main "$@"