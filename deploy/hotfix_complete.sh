#!/bin/bash
set -e

echo "🚑 COMPLETE HOTFIX: Исправление всех проблем production"

# Проверка пользователя
if [ "$EUID" -ne 0 ]; then
    echo "❌ Запустите как root или с sudo"
    exit 1
fi

APP_DIR="/opt/crystalbudget/crystall-budget"
SERVICE_NAME="crystalbudget"

echo "🔄 Остановка сервиса..."
systemctl stop $SERVICE_NAME

echo "🔄 Переход в директорию приложения..."
cd $APP_DIR

echo "🔄 Исправление auth routes (sqlite3.Row.get ошибка)..."
# Исправляем auth/routes.py
if [ -f "app/blueprints/auth/routes.py" ]; then
    # Создаем backup
    cp app/blueprints/auth/routes.py app/blueprints/auth/routes.py.backup
    
    # Применяем исправления
    sed -i "s/user\.get('theme', 'light')/user['theme'] if 'theme' in user.keys() else 'light'/g" app/blueprints/auth/routes.py
    sed -i "s/user\.get('default_currency', 'RUB')/user['default_currency'] if 'default_currency' in user.keys() else 'RUB'/g" app/blueprints/auth/routes.py
    
    echo "✅ Исправлен auth/routes.py"
else
    echo "❌ Файл app/blueprints/auth/routes.py не найден!"
    exit 1
fi

echo "🔄 Обновление systemd сервиса..."
cat > /etc/systemd/system/crystalbudget.service << 'EOF'
[Unit]
Description=CrystalBudget Personal Finance Application
After=network.target

[Service]
Type=notify
User=crystal
Group=crystal
WorkingDirectory=/opt/crystalbudget/crystall-budget

Environment="FLASK_ENV=production"
Environment="LOG_LEVEL=INFO"
Environment="SECRET_KEY=0xm5hy67Txo5taHWK_CuWy72wSDFkgN0f9Rc2L7c_ZhdYFMJTYu8IoXjoW6QQ0x"
Environment="BUDGET_DB=/var/lib/crystalbudget/budget.db"
Environment="HTTPS_MODE=true"
Environment="PYTHONPATH=/opt/crystalbudget/crystall-budget"

ExecStart=/opt/crystalbudget/venv/bin/gunicorn \
  --chdir /opt/crystalbudget/crystall-budget \
  --workers=3 --threads=2 --timeout=60 \
  --bind 127.0.0.1:5000 \
  --enable-stdio-inheritance \
  wsgi:app

Restart=always
RestartSec=5

NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ReadWritePaths=/var/lib/crystalbudget /opt/crystalbudget/crystall-budget/logs

[Install]
WantedBy=multi-user.target
EOF

echo "🔄 Перезагрузка systemd..."
systemctl daemon-reload

echo "🔄 Проверка wsgi.py..."
if [ ! -f "wsgi.py" ]; then
    cat > wsgi.py << 'EOF'
"""WSGI entry point for Crystal Budget application."""

import os
from app import create_app

# Create application instance
app = create_app()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0", 
        port=int(os.environ.get("PORT", 5000)), 
        debug=os.environ.get("FLASK_ENV") == "development"
    )
EOF
    chmod +x wsgi.py
fi

echo "🔄 Установка прав доступа..."
chown -R crystal:crystal /opt/crystalbudget/crystall-budget
chmod +x wsgi.py

echo "🔄 Тест импорта..."
sudo -u crystal python3 -c "
import sys
sys.path.insert(0, '/opt/crystalbudget/crystall-budget')
from app import create_app
app = create_app('production')
print('✅ Импорт модулей работает')
print('✅ Создание приложения работает')
" || {
    echo "❌ Ошибка импорта или создания приложения"
    exit 1
}

echo "🔄 Запуск сервиса..."
systemctl start $SERVICE_NAME

# Проверка статуса с задержкой
echo "🔄 Ожидание запуска сервиса..."
sleep 5

if systemctl is-active --quiet $SERVICE_NAME; then
    echo "✅ Сервис запущен успешно!"
    
    # Тест HTTP
    echo "🔄 Тест HTTP соединения..."
    sleep 2
    if curl -s -f http://localhost:5000 > /dev/null; then
        echo "✅ HTTP тест пройден"
    else
        echo "⚠️  HTTP тест не прошел, но сервис работает"
    fi
    
    echo "✅ COMPLETE HOTFIX применен успешно!"
    
else
    echo "❌ Сервис не запустился после исправлений"
    echo "🔍 Последние логи:"
    journalctl -u $SERVICE_NAME --no-pager -l --since "2 minutes ago"
    exit 1
fi

echo ""
echo "🎉 Все исправления применены!"
echo "📊 Статус сервиса:"
systemctl status $SERVICE_NAME --no-pager
echo ""
echo "📝 Полезные команды:"
echo "  journalctl -u $SERVICE_NAME -f    # Просмотр логов"
echo "  systemctl restart $SERVICE_NAME   # Перезапуск"