#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}Простое исправление API без .env...${NC}"

cd /data/crystall-budget

# 1. Останавливаем все
systemctl stop crystall-api 2>/dev/null || true
pkill -f "node.*server.js" 2>/dev/null || true

# 2. Создаем новый systemd сервис без EnvironmentFile
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
Environment="DATABASE_URL=postgres://crystall:adminDII@127.0.0.1:5432/crystall"
Environment="JWT_SECRET=supersecret_jwt_key_32_chars_long_123"
Environment="HOST=127.0.0.1"
Environment="PORT=4000"
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✓ Systemd сервис обновлен (без .env файла)${NC}"

# 3. Перезагружаем systemd
systemctl daemon-reload

# 4. Тестируем API вручную
echo "Тестирование API вручную..."
cd api
sudo -u crystall DATABASE_URL="postgres://crystall:adminDII@127.0.0.1:5432/crystall" \
JWT_SECRET="supersecret_jwt_key_32_chars_long_123" \
HOST="127.0.0.1" \
PORT="4000" \
timeout 5 node server.js &

sleep 2
if curl -s http://127.0.0.1:4000/api/health >/dev/null 2>&1; then
    echo -e "${GREEN}✓ API работает вручную${NC}"
    # Убиваем тестовый процесс
    pkill -f "node.*server.js" 2>/dev/null || true
    sleep 1
else
    echo -e "${RED}⚠ API не отвечает даже вручную${NC}"
    pkill -f "node.*server.js" 2>/dev/null || true
fi

# 5. Запускаем через systemd
echo "Запуск через systemd..."
systemctl start crystall-api
sleep 3

if systemctl is-active --quiet crystall-api; then
    echo -e "${GREEN}✓ API сервис запущен${NC}"
    
    # Проверяем доступность
    sleep 2
    if curl -s --max-time 5 http://127.0.0.1:4000/api/health >/dev/null 2>&1; then
        echo -e "${GREEN}✓ API отвечает на /api/health${NC}"
    else
        echo -e "${RED}⚠ API не отвечает${NC}"
        journalctl -u crystall-api --no-pager -n 10
    fi
else
    echo -e "${RED}✗ API сервис не запустился${NC}"
    journalctl -u crystall-api --no-pager -n 10
fi

# 6. Проверяем все сервисы
echo
echo -e "${BLUE}=== Статус всех сервисов ===${NC}"
for service in crystall-api crystall-web caddy; do
    if systemctl is-active --quiet "${service}"; then
        echo -e "${GREEN}✓${NC} ${service}: активен"
    else
        echo -e "${RED}✗${NC} ${service}: неактивен"
    fi
done

# 7. Тестируем полный стек
echo
echo -e "${BLUE}=== Тест полного стека ===${NC}"
echo "API Health:"
curl -s --max-time 5 http://127.0.0.1:4000/api/health 2>/dev/null || echo "API недоступен"

echo "Web (через Caddy):"
curl -s --max-time 5 -I https://crystallbudget.161-35-31-38.sslip.io 2>/dev/null | head -1 || echo "Web через HTTPS недоступен"

echo
echo -e "${GREEN}=========================================="
echo "           Простое API готово!"
echo "==========================================${NC}"
echo
echo "🌐 URL: https://crystallbudget.161-35-31-38.sslip.io"
echo "🔍 API: curl http://127.0.0.1:4000/api/health"