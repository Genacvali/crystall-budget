#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Исправление прав доступа и TypeScript...${NC}"

cd /data/crystall-budget/web

# Исправляем права доступа
chown -R crystall:crystall /data/crystall-budget/web
echo -e "${GREEN}✓ Права доступа исправлены${NC}"

# Добавляем TypeScript типы в package.json заранее
cat > package.json << 'EOF'
{
  "name": "crystall-web",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev -p 3000",
    "build": "next build", 
    "start": "next start -p 3000"
  },
  "dependencies": {
    "next": "14.2.0",
    "react": "18.3.1",
    "react-dom": "18.3.1"
  },
  "devDependencies": {
    "@types/node": "^20.14.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "typescript": "^5.5.0"
  }
}
EOF

echo -e "${GREEN}✓ Обновили package.json с TypeScript типами${NC}"

# Переустанавливаем зависимости с правильными правами
rm -rf node_modules package-lock.json
sudo -u crystall npm install
echo -e "${GREEN}✓ Зависимости установлены${NC}"

# Пересобираем проект
echo "Пересборка проекта..."
sudo -u crystall npm run build

if [[ $? -eq 0 ]]; then
    echo -e "${GREEN}✓ Web успешно собран${NC}"
    
    # Настраиваем systemd сервисы
    echo "Настройка systemd сервисов..."
    cp ../crystall-api.service /etc/systemd/system/
    cp ../crystall-web.service /etc/systemd/system/
    systemctl daemon-reload
    echo -e "${GREEN}✓ Systemd сервисы настроены${NC}"
    
    # Настраиваем Caddy
    echo "Настройка Caddy..."
    EXTERNAL_IP=$(curl -s ifconfig.me 2>/dev/null || echo "161-35-31-38")
    sed "s/YOUR-IP/${EXTERNAL_IP//./-}/g" ../Caddyfile > /etc/caddy/Caddyfile
    echo -e "${GREEN}✓ Caddy настроен для домена: crystallbudget.${EXTERNAL_IP//./-}.sslip.io${NC}"
    
    echo
    echo -e "${GREEN}=========================================="
    echo "           Проект готов к работе!"
    echo "==========================================${NC}"
    echo
    echo "Теперь можно запускать:"
    echo "  sudo ./start.sh"
    echo
    echo "URL: https://crystallbudget.${EXTERNAL_IP//./-}.sslip.io"
    
else
    echo -e "${RED}✗ Ошибка сборки${NC}"
    exit 1
fi