#!/usr/bin/env bash
set -euo pipefail

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

check_service() {
    local service_name=$1
    local display_name=$2
    
    printf "%-20s " "${display_name}:"
    
    if systemctl is-active --quiet "${service_name}"; then
        echo -e "${GREEN}✓ активен${NC}"
        
        # Показываем дополнительную информацию для основных сервисов
        case "${service_name}" in
            "crystall-api")
                local pid=$(systemctl show -p MainPID --value crystall-api)
                if [[ "${pid}" != "0" ]]; then
                    echo -e "  ${CYAN}PID: ${pid}${NC}"
                fi
                ;;
            "crystall-web")
                local pid=$(systemctl show -p MainPID --value crystall-web)
                if [[ "${pid}" != "0" ]]; then
                    echo -e "  ${CYAN}PID: ${pid}${NC}"
                fi
                ;;
        esac
    else
        echo -e "${RED}✗ неактивен${NC}"
        
        # Показываем причину остановки
        local failed_state=$(systemctl is-failed "${service_name}" 2>/dev/null || echo "inactive")
        if [[ "${failed_state}" == "failed" ]]; then
            echo -e "  ${RED}Статус: failed${NC}"
        fi
    fi
}

check_ports() {
    echo -e "${BLUE}=== Проверка портов ===${NC}"
    
    for port in 3000 4000 80 443; do
        printf "%-10s " "Порт ${port}:"
        
        if nc -z 127.0.0.1 "${port}" 2>/dev/null; then
            echo -e "${GREEN}✓ доступен${NC}"
            
            # Показываем какой процесс использует порт
            local pid=$(lsof -ti:${port} 2>/dev/null || echo "")
            if [[ -n "${pid}" ]]; then
                local process=$(ps -p ${pid} -o comm= 2>/dev/null || echo "unknown")
                echo -e "  ${CYAN}Процесс: ${process} (PID: ${pid})${NC}"
            fi
        else
            echo -e "${RED}✗ недоступен${NC}"
        fi
    done
}

check_api_health() {
    echo -e "\n${BLUE}=== Проверка API ===${NC}"
    
    printf "API Health: "
    if curl -s --max-time 5 http://127.0.0.1:4000/api/health &>/dev/null; then
        echo -e "${GREEN}✓ API отвечает${NC}"
        
        # Получаем детали ответа
        local response=$(curl -s --max-time 5 http://127.0.0.1:4000/api/health || echo "{}")
        echo -e "  ${CYAN}Ответ: ${response}${NC}"
    else
        echo -e "${RED}✗ API не отвечает${NC}"
    fi
}

check_database() {
    echo -e "\n${BLUE}=== Проверка базы данных ===${NC}"
    
    printf "PostgreSQL: "
    if systemctl is-active --quiet postgresql; then
        echo -e "${GREEN}✓ активен${NC}"
        
        # Проверяем подключение к базе
        printf "Подключение: "
        if sudo -u postgres psql -d crystall -c "SELECT version();" &>/dev/null; then
            echo -e "${GREEN}✓ успешно${NC}"
            
            # Проверяем таблицы
            local tables=$(sudo -u postgres psql -d crystall -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null || echo "0")
            echo -e "  ${CYAN}Таблиц в базе: ${tables}${NC}"
        else
            echo -e "${RED}✗ ошибка подключения${NC}"
        fi
    else
        echo -e "${RED}✗ неактивен${NC}"
    fi
}

check_disk_space() {
    echo -e "\n${BLUE}=== Использование диска ===${NC}"
    
    local usage=$(df -h /data/crystall-budget 2>/dev/null | awk 'NR==2 {print $5}' || echo "N/A")
    local available=$(df -h /data/crystall-budget 2>/dev/null | awk 'NR==2 {print $4}' || echo "N/A")
    
    echo -e "Проект: ${CYAN}${usage} использовано, ${available} доступно${NC}"
    
    # Проверяем размер логов
    local log_size=$(du -sh /var/log/journal/ 2>/dev/null | awk '{print $1}' || echo "N/A")
    echo -e "Логи: ${CYAN}${log_size}${NC}"
}

show_urls() {
    echo -e "\n${BLUE}=== URLs ===${NC}"
    
    local external_ip=$(curl -s --max-time 5 ifconfig.me 2>/dev/null || echo "unknown")
    
    if [[ "${external_ip}" != "unknown" ]]; then
        local domain="crystallbudget.${external_ip//./-}.sslip.io"
        echo -e "🌐 Public:  ${CYAN}https://${domain}${NC}"
    fi
    
    echo -e "🏠 API:     ${CYAN}http://127.0.0.1:4000/api/health${NC}"
    echo -e "🖥️  Web:     ${CYAN}http://127.0.0.1:3000${NC}"
}

main() {
    echo -e "${BLUE}"
    echo "=========================================="
    echo "      CrystallBudget Status Check"
    echo "=========================================="
    echo -e "${NC}"
    
    echo -e "${BLUE}=== Статус сервисов ===${NC}"
    check_service "postgresql" "PostgreSQL"
    check_service "crystall-api" "API сервер"
    check_service "crystall-web" "Web сервер"  
    check_service "caddy" "Caddy прокси"
    
    check_ports
    check_api_health
    check_database
    check_disk_space
    show_urls
    
    echo -e "\n${BLUE}=== Управление ===${NC}"
    echo "  sudo ./start.sh    - запустить все сервисы"
    echo "  sudo ./stop.sh     - остановить все сервисы"
    echo "  sudo ./logs.sh     - показать логи"
    echo "  sudo ./deploy.sh   - переустановить"
    
    echo
}

main "$@"