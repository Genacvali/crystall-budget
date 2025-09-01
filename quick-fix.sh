#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Быстрое исправление...${NC}"

cd /data/crystall-budget/web

# Исправляем права
chown -R crystall:crystall .

# Устанавливаем TypeScript типы
sudo -u crystall npm install --save-dev @types/react @types/react-dom

echo -e "${GREEN}✓ TypeScript типы установлены${NC}"

# Пересобираем
sudo -u crystall npm run build

echo -e "${GREEN}✓ Проект собран${NC}"

echo "Можно запускать: sudo ./start.sh"