#!/bin/bash
# Скрипт деплоя админской панели на продакшен

set -e

PROD_USER="admin"
PROD_PATH="/opt/crystalbudget/crystall-budget"
DOMAIN="admin.crystalbudget.net"  # Замените на ваш домен

echo "🚀 Деплой админской панели CrystalBudget"
echo "========================================"

# Проверяем что мы на сервере
if [ ! -d "$PROD_PATH" ]; then
    echo "❌ Путь $PROD_PATH не найден. Убедитесь что основное приложение установлено."
    exit 1
fi

# Копируем файлы админской панели
echo "📁 Копирование файлов админской панели..."
sudo cp admin_panel/admin_panel.py "$PROD_PATH/"
sudo cp -r admin_panel/templates/admin_panel "$PROD_PATH/templates/"

# Копируем systemd сервис
echo "🔧 Настройка systemd сервиса..."
sudo cp admin_panel/admin-panel.service /etc/systemd/system/
sudo systemctl daemon-reload

# Генерируем безопасные пароли
ADMIN_PASSWORD=$(openssl rand -base64 32)
SECRET_KEY=$(openssl rand -hex 32)

echo ""
echo "🔐 Сгенерированы учетные данные:"
echo "   Логин админки: admin"
echo "   Пароль админки: $ADMIN_PASSWORD"
echo "   Секретный ключ: $SECRET_KEY"
echo ""
echo "⚠️  СОХРАНИТЕ ЭТИ ДАННЫЕ В БЕЗОПАСНОМ МЕСТЕ!"

# Настраиваем переменные окружения в сервисе
sudo sed -i "s/CHANGE_THIS_PASSWORD/$ADMIN_PASSWORD/g" /etc/systemd/system/admin-panel.service
sudo sed -i "s/CHANGE_THIS_SECRET_KEY/$SECRET_KEY/g" /etc/systemd/system/admin-panel.service

# Устанавливаем зависимости если нужно
echo "📦 Проверка зависимостей..."
source /opt/crystalbudget/venv/bin/activate
pip install -q python-dotenv

# Создаем директорию для логов
sudo mkdir -p /var/log/crystalbudget
sudo chown $PROD_USER:$PROD_USER /var/log/crystalbudget

# Запускаем сервис
echo "🚀 Запуск админской панели..."
sudo systemctl enable admin-panel
sudo systemctl start admin-panel

# Проверяем статус
sleep 3
if sudo systemctl is-active --quiet admin-panel; then
    echo "✅ Админская панель запущена успешно"
else
    echo "❌ Ошибка запуска админской панели"
    sudo journalctl -u admin-panel --no-pager -n 20
    exit 1
fi

# Настройка Nginx (опционально)
if [ -f "/etc/nginx/nginx.conf" ]; then
    echo ""
    echo "🌐 Настройка Nginx..."
    
    # Копируем конфигурацию
    sudo cp admin_panel/nginx-admin-panel.conf /etc/nginx/sites-available/admin-crystalbudget
    
    echo "📝 Для завершения настройки Nginx выполните:"
    echo "   1. Отредактируйте домен в /etc/nginx/sites-available/admin-crystalbudget"
    echo "   2. sudo ln -s /etc/nginx/sites-available/admin-crystalbudget /etc/nginx/sites-enabled/"
    echo "   3. sudo certbot --nginx -d $DOMAIN"
    echo "   4. sudo nginx -t && sudo systemctl reload nginx"
else
    echo "⚠️  Nginx не найден. Админская панель доступна на порту 5001"
fi

echo ""
echo "🎉 Деплой завершен!"
echo ""
echo "📊 Информация:"
echo "   Сервис: admin-panel.service"
echo "   Порт: 5001"
echo "   Логи: sudo journalctl -u admin-panel -f"
echo "   URL: http://localhost:5001"
if [ -f "/etc/nginx/nginx.conf" ]; then
    echo "   После настройки Nginx: https://$DOMAIN"
fi
echo ""
echo "💡 Команды управления:"
echo "   sudo systemctl start admin-panel     - запуск"
echo "   sudo systemctl stop admin-panel      - остановка"
echo "   sudo systemctl restart admin-panel   - перезапуск"
echo "   sudo systemctl status admin-panel    - статус"