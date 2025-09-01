#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}Исправление Next.js конфигурации...${NC}"

cd /data/crystall-budget/web

# Исправляем tsconfig.json
cat > tsconfig.json << 'EOF'
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["DOM", "ES2020"],
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "baseUrl": ".",
    "paths": {
      "@/*": ["./*"]
    },
    "jsx": "preserve",
    "strict": true,
    "noEmit": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "incremental": true,
    "plugins": [
      {
        "name": "next"
      }
    ]
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx"],
  "exclude": ["node_modules"]
}
EOF

echo -e "${GREEN}✓ tsconfig.json исправлен${NC}"

# Обновляем next.config.js с правильными путями
cat > next.config.js << 'EOF'
const path = require('path');

/** @type {import('next').NextConfig} */
const nextConfig = { 
  output: 'standalone',
  webpack: (config) => {
    config.resolve.alias['@'] = path.resolve(__dirname, '.');
    return config;
  },
};
module.exports = nextConfig;
EOF

echo -e "${GREEN}✓ next.config.js обновлен${NC}"

# Пересобираем проект
echo "Пересборка проекта..."
sudo -u crystall npm run build

if [[ $? -eq 0 ]]; then
    echo -e "${GREEN}✓ Web успешно собран${NC}"
else
    echo -e "${RED}✗ Ошибка сборки${NC}"
    
    echo -e "${BLUE}Попробуем альтернативный способ...${NC}"
    
    # Исправляем импорты в файлах напрямую
    sed -i "s|from '@/lib/api'|from '../../../lib/api'|g" app/auth/signin/page.tsx
    sed -i "s|from '@/lib/api'|from '../../../lib/api'|g" app/auth/signup/page.tsx
    
    echo -e "${GREEN}✓ Импорты исправлены на относительные пути${NC}"
    
    # Пробуем собрать снова
    echo "Повторная сборка..."
    sudo -u crystall npm run build
fi

echo
echo -e "${GREEN}=========================================="
echo "     Next.js конфигурация исправлена!"
echo "==========================================${NC}"
echo
echo "Теперь можно запускать:"
echo "  sudo ./start.sh"