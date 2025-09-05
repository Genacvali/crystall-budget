#!/bin/bash

# Скрипт развертывания CrystalBudget на сервере
# Запускать из директории /root/crystall-budget

set -e

echo "🚀 Развертывание CrystalBudget..."

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция для вывода с цветом
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Проверка что мы в правильной директории
if [[ "$PWD" != "/root/crystall-budget" ]]; then
    print_error "Скрипт должен запускаться из директории /root/crystall-budget"
    exit 1
fi

# Проверка наличия файлов
for file in app.py requirements.txt crystalbudget.service nginx-crystalbudget.conf; do
    if [[ ! -f "$file" ]]; then
        print_error "Файл $file не найден!"
        exit 1
    fi
done

echo "📦 Установка зависимостей..."

# Обновление пакетов
apt update

# Установка nginx, certbot, python3
apt install -y nginx python3 python3-pip python3-venv certbot python3-certbot-nginx

print_status "Зависимости установлены"

echo "🐍 Настройка Python окружения..."

# Создание виртуального окружения если его нет
if [[ ! -d ".venv" ]]; then
    python3 -m venv .venv
    print_status "Виртуальное окружение создано"
fi

# Установка Python зависимостей
.venv/bin/pip install -r requirements.txt

print_status "Python зависимости установлены"

echo "📁 Создание директорий для логов..."

# Создание директорий для логов
mkdir -p /var/log/crystalbudget
mkdir -p logs
chown -R root:root /var/log/crystalbudget
chown -R root:root logs

print_status "Директории для логов созданы"

echo "⚙️ Настройка systemd сервиса..."

# Копирование и установка systemd сервиса
cp crystalbudget.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable crystalbudget

print_status "Systemd сервис настроен"

echo "🌐 Настройка nginx..."

# Копирование конфигурации nginx
cp nginx-crystalbudget.conf /etc/nginx/sites-available/crystalbudget

# Создание символической ссылки
if [[ ! -L /etc/nginx/sites-enabled/crystalbudget ]]; then
    ln -s /etc/nginx/sites-available/crystalbudget /etc/nginx/sites-enabled/
    print_status "Конфигурация nginx активирована"
fi

# Проверка конфигурации nginx
if nginx -t; then
    print_status "Конфигурация nginx корректна"
else
    print_error "Ошибка в конфигурации nginx!"
    exit 1
fi

echo "🔧 Генерация секретного ключа..."

# Генерация секретного ключа если его нет
SECRET_KEY_FILE="/root/crystall-budget/.secret_key"
if [[ ! -f "$SECRET_KEY_FILE" ]]; then
    python3 -c "import secrets; print(secrets.token_urlsafe(32))" > "$SECRET_KEY_FILE"
    chmod 600 "$SECRET_KEY_FILE"
    print_status "Секретный ключ сгенерирован в $SECRET_KEY_FILE"
fi

SECRET_KEY=$(cat "$SECRET_KEY_FILE")

# Обновление systemd сервиса с секретным ключом
sed -i "s/your-production-secret-key-change-this/$SECRET_KEY/g" /etc/systemd/system/crystalbudget.service
systemctl daemon-reload

print_status "Секретный ключ установлен в systemd сервис"

echo "🚀 Запуск сервисов..."

# Запуск Flask приложения
systemctl start crystalbudget

# Проверка статуса
if systemctl is-active --quiet crystalbudget; then
    print_status "CrystalBudget сервис запущен"
else
    print_error "Не удалось запустить CrystalBudget сервис!"
    systemctl status crystalbudget
    exit 1
fi

# Перезагрузка nginx
systemctl reload nginx

if systemctl is-active --quiet nginx; then
    print_status "Nginx перезагружен"
else
    print_error "Проблема с nginx!"
    systemctl status nginx
    exit 1
fi

echo ""
print_status "Базовое развертывание завершено!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Обновите домен в /etc/nginx/sites-available/crystalbudget"
echo "2. Настройте DNS записи для вашего домена"
echo "3. Запустите: certbot --nginx -d your-domain.com"
echo "4. Настройте файрвол: ufw allow 'Nginx Full'"
echo ""
echo "🔍 Проверка:"
echo "• Статус сервиса: systemctl status crystalbudget"
echo "• Логи приложения: journalctl -u crystalbudget -f"
echo "• Логи nginx: tail -f /var/log/nginx/crystalbudget.*.log"
echo "• Health check: curl http://localhost:5000/health"
echo ""

# Показать статус сервисов
echo "📊 Текущий статус сервисов:"
systemctl --no-pager status crystalbudget nginx