#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Создание Caddyfile...${NC}"

# Получаем внешний IP
EXTERNAL_IP=$(curl -s ifconfig.me 2>/dev/null || echo "161-35-31-38")
DOMAIN="crystallbudget.${EXTERNAL_IP//./-}.sslip.io"

# Создаем Caddyfile
cat > /data/crystall-budget/Caddyfile << EOF
:80, :443 {
  redir https://${DOMAIN}{uri} permanent
}

${DOMAIN} {
  encode zstd gzip

  @api path /api/*
  reverse_proxy @api 127.0.0.1:4000

  reverse_proxy 127.0.0.1:3000

  header {
    Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
    X-Content-Type-Options "nosniff"
    Referrer-Policy "strict-origin-when-cross-origin"
  }
}
EOF

echo -e "${GREEN}✓ Caddyfile создан для домена: ${DOMAIN}${NC}"

# Копируем в Caddy
cp /data/crystall-budget/Caddyfile /etc/caddy/Caddyfile
systemctl reload caddy 2>/dev/null || systemctl restart caddy

echo -e "${GREEN}✓ Caddy настроен и перезапущен${NC}"

echo
echo -e "${GREEN}=========================================="
echo "           Проект полностью готов!"
echo "==========================================${NC}"
echo
echo "URL: https://${DOMAIN}"
echo
echo "Запуск сервисов:"
echo "  sudo ./start.sh"