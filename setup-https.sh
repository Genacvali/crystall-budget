#!/bin/bash

# Скрипт настройки HTTPS для CrystalBudget
# Запускать ПОСЛЕ deploy.sh

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

echo "🔒 Настройка HTTPS для CrystalBudget"
echo ""

# Проверка что deploy.sh был выполнен
if [[ ! -f "/etc/systemd/system/crystalbudget.service" ]]; then
    print_error "Сначала запустите deploy.sh!"
    exit 1
fi

# Запрос домена у пользователя
while true; do
    read -p "Введите ваш домен (например: budget.example.com): " DOMAIN
    if [[ -n "$DOMAIN" ]]; then
        break
    else
        print_warning "Домен не может быть пустым!"
    fi
done

# Опционально www поддомен
read -p "Добавить www.$DOMAIN? (y/n): " ADD_WWW

if [[ "$ADD_WWW" =~ ^[Yy]$ ]]; then
    DOMAINS="$DOMAIN www.$DOMAIN"
else
    DOMAINS="$DOMAIN"
fi

print_info "Домены для сертификата: $DOMAINS"

echo ""
echo "🌐 Обновление конфигурации nginx..."

# Обновление конфигурации nginx с реальным доменом
sed -i "s/your-domain.com/$DOMAIN/g" /etc/nginx/sites-available/crystalbudget

print_status "Конфигурация nginx обновлена"

# Проверка и перезагрузка nginx
if nginx -t; then
    systemctl reload nginx
    print_status "Nginx перезагружен"
else
    print_error "Ошибка в конфигурации nginx!"
    exit 1
fi

echo ""
echo "🔐 Получение SSL сертификата..."

# Проверка что домен указывает на этот сервер
print_warning "Убедитесь что DNS запись для $DOMAIN указывает на IP этого сервера!"
read -p "DNS настроен? Продолжить? (y/n): " DNS_READY

if [[ ! "$DNS_READY" =~ ^[Yy]$ ]]; then
    print_info "Настройте DNS и запустите скрипт снова"
    exit 0
fi

# Получение сертификата
echo "Получение SSL сертификата..."

if certbot --nginx -d $DOMAINS --non-interactive --agree-tos --email admin@$DOMAIN; then
    print_status "SSL сертификат получен и настроен!"
else
    print_error "Не удалось получить SSL сертификат!"
    echo ""
    print_info "Возможные причины:"
    echo "• DNS запись не настроена или не распространилась"
    echo "• Домен недоступен извне"  
    echo "• Файрвол блокирует порты 80/443"
    echo "• Nginx не запущен"
    exit 1
fi

echo ""
echo "🔥 Настройка файрвола..."

# Настройка UFW если установлен
if command -v ufw &> /dev/null; then
    ufw --force enable
    ufw allow 'Nginx Full'
    ufw allow ssh
    print_status "Файрвол настроен (UFW)"
else
    print_warning "UFW не установлен. Убедитесь что порты 80, 443, 22 открыты"
fi

echo ""
echo "🧪 Тестирование..."

# Тест HTTPS
echo "Тестирование HTTPS соединения..."
if curl -s -o /dev/null -w "%{http_code}" https://$DOMAIN | grep -q "200"; then
    print_status "HTTPS работает корректно!"
else
    print_warning "Возможны проблемы с HTTPS. Проверьте вручную: https://$DOMAIN"
fi

# Тест health check
echo "Тестирование health check..."
if curl -s https://$DOMAIN/health | grep -q "healthy"; then
    print_status "Health check работает!"
else
    print_warning "Health check может работать некорректно"
fi

echo ""
echo "✅ Настройка HTTPS завершена!"
echo ""
echo "🌐 Ваше приложение доступно по адресу: https://$DOMAIN"
echo ""
echo "📋 Полезные команды:"
echo "• Проверка SSL: curl -I https://$DOMAIN"
echo "• Рейтинг SSL: https://www.ssllabs.com/ssltest/analyze.html?d=$DOMAIN"
echo "• Обновление сертификата: certbot renew"
echo "• Статус сертификатов: certbot certificates"
echo ""
echo "🔄 Автообновление сертификатов:"
echo "Certbot автоматически добавил задачу в cron для обновления сертификатов."
echo "Проверить: certbot renew --dry-run"
echo ""

# Показать информацию о сертификате
certbot certificates