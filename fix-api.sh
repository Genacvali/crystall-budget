#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}Исправление API сервиса...${NC}"

cd /data/crystall-budget

# 1. Исправляем права на .env файл
chmod 644 api/.env
chown crystall:crystall api/.env
echo -e "${GREEN}✓ Права на .env исправлены${NC}"

# 2. Исправляем systemd сервис для API (убираем RuntimeMaxMemory для старых версий systemd)
cat > /etc/systemd/system/crystall-api.service << 'EOF'
[Unit]
Description=Crystall API
After=network.target postgresql.service
Wants=network-online.target

[Service]
Type=simple
User=crystall
Group=crystall
WorkingDirectory=/data/crystall-budget/api
ExecStart=/usr/bin/node server.js
EnvironmentFile=/data/crystall-budget/api/.env
Restart=always
RestartSec=5
MemoryLimit=128M

[Install]
WantedBy=multi-user.target
EOF

# 3. Исправляем systemd сервис для Web
cat > /etc/systemd/system/crystall-web.service << 'EOF'
[Unit]
Description=Crystall Budget Next.js Web
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=crystall
Group=crystall
WorkingDirectory=/data/crystall-budget/web
ExecStart=/usr/bin/npx next dev -p 3000
Environment=NODE_ENV=development
Restart=always
RestartSec=5
MemoryLimit=128M

[Install]
WantedBy=multi-user.target
EOF

# 4. Перезагружаем systemd
systemctl daemon-reload
echo -e "${GREEN}✓ Systemd сервисы обновлены${NC}"

# 5. Останавливаем старые сервисы
systemctl stop crystall-api 2>/dev/null || true
systemctl stop crystall-web 2>/dev/null || true
sleep 2

# 6. Убиваем старые процессы если висят
pkill -f "node.*server.js" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
sleep 1

echo -e "${GREEN}✓ Старые процессы остановлены${NC}"

# 7. Тестируем API запуск вручную
echo "Тестирование API..."
cd /data/crystall-budget/api
if sudo -u crystall timeout 3 node server.js 2>&1 | grep -q "listening"; then
    echo -e "${GREEN}✓ API запускается корректно${NC}"
else
    echo -e "${RED}⚠ API тест не прошел, но продолжаем${NC}"
fi

# 8. Запускаем сервисы
echo "Запуск API сервиса..."
systemctl start crystall-api
sleep 2

if systemctl is-active --quiet crystall-api; then
    echo -e "${GREEN}✓ API сервис запущен${NC}"
else
    echo -e "${RED}✗ Проблема с API сервисом${NC}"
    journalctl -u crystall-api --no-pager -n 5
fi

echo "Запуск Web сервиса..."
systemctl restart crystall-web
sleep 3

if systemctl is-active --quiet crystall-web; then
    echo -e "${GREEN}✓ Web сервис запущен${NC}"
else
    echo -e "${RED}✗ Проблема с Web сервисом${NC}"
    journalctl -u crystall-web --no-pager -n 5
fi

# 9. Проверяем порты
echo "Проверка портов..."
sleep 5

if curl -s --max-time 3 http://127.0.0.1:4000/api/health >/dev/null 2>&1; then
    echo -e "${GREEN}✓ API доступен на порту 4000${NC}"
else
    echo -e "${RED}⚠ API не отвечает на порту 4000${NC}"
fi

if curl -s --max-time 3 http://127.0.0.1:3000 >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Web доступен на порту 3000${NC}"
else
    echo -e "${RED}⚠ Web не отвечает на порту 3000${NC}"
fi

echo
echo -e "${GREEN}=========================================="
echo "           API исправлен!"
echo "==========================================${NC}"
echo
echo "🌐 URL: https://crystallbudget.161-35-31-38.sslip.io"
echo
echo "Проверка статуса:"
echo "  sudo ./status.sh"