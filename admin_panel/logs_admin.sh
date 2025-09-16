#!/bin/bash
# Скрипт просмотра логов админской панели

echo "📋 Логи админской панели:"
echo "========================"

if [ -f "logs/admin_panel.log" ]; then
    echo ""
    echo "📄 Последние 50 строк логов:"
    echo ""
    tail -50 logs/admin_panel.log
    echo ""
    echo "💡 Для просмотра в реальном времени: tail -f logs/admin_panel.log"
else
    echo "❌ Файл логов не найден: logs/admin_panel.log"
    echo ""
    echo "💡 Убедитесь что админская панель была запущена"
fi

echo ""
echo "📊 Статус процесса:"
if pgrep -f "admin_panel.py" > /dev/null; then
    echo "✅ Админская панель запущена (PID: $(pgrep -f admin_panel.py))"
else
    echo "❌ Админская панель не запущена"
fi