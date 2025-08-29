#!/bin/bash
# CrystallBudget - Быстрый деплой на CentOS 9
set -euo pipefail

echo "💎 CrystallBudget - Деплой на CentOS 9"
echo "======================================"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Проверка наличия .env
if [ ! -f ".env" ]; then
    log_warning ".env файл не найден! Создаю из примера..."
    cp .env.example .env
    log_info "Отредактируйте .env файл и запустите скрипт снова"
    echo ""
    echo "Необходимо заменить:"
    echo "  HOSTNAME=ваш-ip.sslip.io"
    echo "  NEXTAUTH_URL=https://ваш-ip.sslip.io"
    echo "  NEXTAUTH_SECRET=случайная-строка-32-символа"
    echo "  POSTGRES_PASSWORD=безопасный-пароль"
    exit 1
fi

# Проверка Docker
log_info "Проверка Docker..."
if ! command -v docker &> /dev/null; then
    log_error "Docker не установлен! Установите Docker и Docker Compose"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    if ! docker-compose version &> /dev/null; then
        log_error "Docker Compose не установлен!"
        exit 1
    else
        COMPOSE_CMD="docker-compose"
    fi
else
    COMPOSE_CMD="docker compose"
fi

log_success "Docker готов (команда: $COMPOSE_CMD)"

# Проверка портов
log_info "Проверка портов..."
if ss -tulpn | grep -q ":80 "; then
    log_warning "Порт 80 уже используется"
    ss -tulpn | grep ":80 "
fi

if ss -tulpn | grep -q ":443 "; then
    log_warning "Порт 443 уже используется"
    ss -tulpn | grep ":443 "
fi

# Получение IP адреса сервера
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s ipinfo.io/ip 2>/dev/null || echo "unknown")
log_info "IP адрес сервера: $SERVER_IP"

if [ "$SERVER_IP" != "unknown" ]; then
    SUGGESTED_HOST=$(echo $SERVER_IP | sed 's/\./-/g').sslip.io
    log_info "Рекомендуемый HOSTNAME: $SUGGESTED_HOST"
fi

# Чтение текущих настроек
CURRENT_HOSTNAME=$(grep "^HOSTNAME=" .env | cut -d'=' -f2 || echo "")
log_info "Текущий HOSTNAME в .env: $CURRENT_HOSTNAME"

# Проверка firewall
log_info "Проверка firewall..."
if systemctl is-active --quiet firewalld; then
    if ! firewall-cmd --list-ports | grep -q "80/tcp"; then
        log_warning "Порт 80 не открыт в firewall"
        read -p "Открыть порт 80? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo firewall-cmd --permanent --add-port=80/tcp
            sudo firewall-cmd --reload
            log_success "Порт 80 открыт"
        fi
    fi
    
    if ! firewall-cmd --list-ports | grep -q "443/tcp"; then
        log_warning "Порт 443 не открыт в firewall"
        read -p "Открыть порт 443? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo firewall-cmd --permanent --add-port=443/tcp
            sudo firewall-cmd --reload
            log_success "Порт 443 открыт"
        fi
    fi
else
    log_info "Firewalld неактивен"
fi

# Создание директорий для данных
log_info "Создание директорий для данных..."
sudo mkdir -p /data/postgres /data/caddy_data /data/caddy_config
sudo chown -R $USER:$USER /data/ 2>/dev/null || true

# Остановка существующих контейнеров
log_info "Остановка существующих контейнеров..."
$COMPOSE_CMD down 2>/dev/null || true

# Сборка и запуск
log_info "Сборка приложения..."
$COMPOSE_CMD build --no-cache app

log_info "Запуск сервисов..."
$COMPOSE_CMD up -d

# Ожидание готовности сервисов
log_info "Ожидание готовности сервисов..."

echo -n "PostgreSQL: "
for i in {1..30}; do
    if $COMPOSE_CMD exec -T db pg_isready -U $(grep POSTGRES_USER .env | cut -d'=' -f2) &>/dev/null; then
        log_success "готов"
        break
    fi
    if [[ $i -eq 30 ]]; then
        log_error "таймаут при подключении к PostgreSQL"
        $COMPOSE_CMD logs db
        exit 1
    fi
    sleep 2
    echo -n "."
done

echo -n "Приложение: "
for i in {1..60}; do
    if curl -s -o /dev/null http://localhost:3000 2>/dev/null; then
        log_success "готово"
        break
    fi
    if [[ $i -eq 60 ]]; then
        log_error "таймаут запуска приложения"
        $COMPOSE_CMD logs app
        exit 1
    fi
    sleep 2
    echo -n "."
done

echo -n "Caddy: "
for i in {1..30}; do
    if curl -s -o /dev/null http://localhost 2>/dev/null; then
        log_success "готов"
        break
    fi
    if [[ $i -eq 30 ]]; then
        log_error "таймаут запуска Caddy"
        $COMPOSE_CMD logs caddy
        exit 1
    fi
    sleep 2
    echo -n "."
done

# Проверка статуса
log_info "Статус сервисов:"
$COMPOSE_CMD ps

# Информация для пользователя
echo ""
log_success "🎉 CrystallBudget успешно развернут!"
echo ""
echo "📋 Информация для доступа:"
echo "  🌐 Web: http://$SERVER_IP (или https://$CURRENT_HOSTNAME если настроен)"
echo "  👤 Демо: demo@crystall.local / demo1234"
echo ""
echo "⚙️  Полезные команды:"
echo "  Логи:           $COMPOSE_CMD logs -f"
echo "  Перезапуск:     $COMPOSE_CMD restart"
echo "  Остановка:      $COMPOSE_CMD down"
echo "  Статус:         $COMPOSE_CMD ps"
echo ""
echo "🔧 Первые шаги:"
echo "  1. Откройте приложение в браузере"
echo "  2. Войдите с демо-аккаунтом или создайте новый"
echo "  3. Установите PWA (кнопка в браузере)"
echo "  4. Настройте категории и создайте первый бюджет"
echo ""

if [ "$CURRENT_HOSTNAME" ]; then
    log_info "Для полной функциональности PWA откройте: https://$CURRENT_HOSTNAME"
    log_warning "HTTPS может потребовать несколько минут для получения сертификата"
fi