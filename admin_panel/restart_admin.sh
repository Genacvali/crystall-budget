#!/bin/bash
# Скрипт перезапуска админской панели

echo "🔄 Перезапуск админской панели..."

# Останавливаем если запущена
./admin_panel/stop_admin.sh

sleep 1

# Запускаем заново
./admin_panel/start_admin.sh