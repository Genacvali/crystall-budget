#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Исправление версий зависимостей...${NC}"

# Исправляем API package.json
cat > /data/crystall-budget/api/package.json << 'EOF'
{
  "name": "crystall-api",
  "version": "1.0.0",
  "private": true,
  "main": "server.js",
  "type": "commonjs",
  "scripts": {
    "start": "NODE_ENV=production node server.js",
    "dev": "node server.js"
  },
  "dependencies": {
    "@fastify/cors": "^8.5.0",
    "@fastify/helmet": "^11.1.1",
    "@node-rs/argon2": "^1.8.0",
    "dotenv": "^16.4.5",
    "fastify": "^4.29.1",
    "jsonwebtoken": "^9.0.2",
    "pg": "^8.12.0"
  }
}
EOF

echo -e "${GREEN}✓ API package.json обновлен${NC}"

# Устанавливаем зависимости
cd /data/crystall-budget/api
echo "Очистка npm cache..."
rm -rf node_modules package-lock.json
npm cache clean --force

echo "Установка зависимостей API..."
sudo -u crystall npm install

echo -e "${GREEN}✓ Зависимости API установлены${NC}"

# Web зависимости
cd /data/crystall-budget/web
echo "Установка зависимостей Web..."
sudo -u crystall npm install
sudo -u crystall npm run build

echo -e "${GREEN}✓ Web собран${NC}"

echo
echo -e "${GREEN}=========================================="
echo "     Зависимости исправлены!"
echo "==========================================${NC}"
echo
echo "Теперь можно запускать:"
echo "  sudo ./start.sh"