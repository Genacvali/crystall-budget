#!/bin/bash
# Скрипт запуска админской панели CrystalBudget

set -e

echo "🚀 Запуск админской панели CrystalBudget"
echo "=========================================="

# Проверяем наличие виртуального окружения
if [ ! -d ".venv" ]; then
    echo "❌ Виртуальное окружение не найдено. Создаем..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    echo "✅ Активируем виртуальное окружение"
    source .venv/bin/activate
fi

# Проверяем наличие базы данных
if [ ! -f "budget.db" ]; then
    echo "⚠️  База данных не найдена. Создаем..."
    python init_db.py
fi

# Устанавливаем переменные окружения для админки
export BUDGET_DB="budget.db"
export ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
export ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin123}"
export ADMIN_SECRET_KEY="${ADMIN_SECRET_KEY:-admin-panel-secret-$(date +%s)}"

echo ""
echo "📋 Конфигурация:"
echo "   База данных: $BUDGET_DB"
echo "   Логин админки: $ADMIN_USERNAME"
echo "   Пароль админки: $ADMIN_PASSWORD"
echo "   Порт: 5001"
echo ""

# Проверяем размер базы данных
if [ -f "$BUDGET_DB" ]; then
    DB_SIZE=$(du -h "$BUDGET_DB" | cut -f1)
    echo "📊 Размер базы данных: $DB_SIZE"
fi

# Считаем количество пользователей
if [ -f "$BUDGET_DB" ]; then
    USER_COUNT=$(sqlite3 "$BUDGET_DB" "SELECT COUNT(*) FROM users;" 2>/dev/null || echo "0")
    echo "👥 Пользователей в базе: $USER_COUNT"
fi

echo ""
echo "🌐 Админская панель будет доступна по адресу:"
echo "   http://localhost:5001"
echo ""

# Проверяем, не запущена ли уже панель
if pgrep -f "admin_panel/admin_panel.py" > /dev/null; then
    echo "⚠️  Админская панель уже запущена!"
    echo "   PID: $(pgrep -f admin_panel/admin_panel.py)"
    echo ""
    echo "   Для остановки: ./stop_admin.sh"
    echo "   Для перезапуска: ./restart_admin.sh"
    exit 0
fi

# Запускаем админскую панель в фоне
echo "🚀 Запускаем админскую панель в фоновом режиме..."
nohup python admin_panel/admin_panel.py > logs/admin_panel.log 2>&1 &
ADMIN_PID=$!

# Сохраняем PID для возможности остановки
echo $ADMIN_PID > admin_panel.pid

echo "✅ Админская панель запущена!"
echo "   PID: $ADMIN_PID"
echo "   Логи: logs/admin_panel.log"
echo ""
echo "💡 Команды управления:"
echo "   ./stop_admin.sh    - остановить"
echo "   ./restart_admin.sh - перезапустить" 
echo "   ./logs_admin.sh    - просмотреть логи"