#!/bin/bash
# Скрипт остановки админской панели

echo "🛑 Остановка админской панели..."

# Проверяем PID файл
if [ -f "admin_panel.pid" ]; then
    PID=$(cat admin_panel.pid)
    if kill -0 $PID 2>/dev/null; then
        echo "   Останавливаем процесс PID: $PID"
        kill $PID
        sleep 2
        
        # Проверяем, что процесс действительно остановлен
        if kill -0 $PID 2>/dev/null; then
            echo "   Принудительная остановка..."
            kill -9 $PID
        fi
        
        echo "✅ Админская панель остановлена"
    else
        echo "   Процесс уже не запущен"
    fi
    rm -f admin_panel.pid
else
    # Ищем процесс по имени
    if pgrep -f "admin_panel/admin_panel.py" > /dev/null; then
        echo "   Останавливаем все процессы admin_panel/admin_panel.py"
        pkill -f "admin_panel/admin_panel.py"
        echo "✅ Админская панель остановлена"
    else
        echo "   Админская панель не запущена"
    fi
fi