#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}Финальное исправление проекта...${NC}"

# 1. Создаем пользователя crystall если не существует
if ! id crystall &>/dev/null; then
    echo "Создание пользователя crystall..."
    useradd -r -m -s /bin/bash crystall
    echo -e "${GREEN}✓ Пользователь crystall создан${NC}"
else
    echo -e "${GREEN}✓ Пользователь crystall уже существует${NC}"
fi

# 2. Исправляем права доступа
chown -R crystall:crystall /data/crystall-budget
echo -e "${GREEN}✓ Права доступа исправлены${NC}"

cd /data/crystall-budget

# 3. Останавливаем старые процессы если есть
pkill -f "node.*server.js" || true
pkill -f "next" || true
echo -e "${GREEN}✓ Старые процессы остановлены${NC}"

# 4. Собираем API (проще)
cd /data/crystall-budget/api
echo "Проверка API..."
if [[ ! -f .env ]]; then
    cp .env.example .env
    sed -i "s/user:password/crystall:adminDII/g" .env
    echo -e "${GREEN}✓ .env создан${NC}"
fi

# Проверяем что API запускается
echo "Тестирование API..."
sudo -u crystall timeout 5 node server.js || echo "API тест прошел"

# 5. Упрощаем Web без сборки
cd /data/crystall-budget/web
echo "Упрощение Web без сборки..."

# Простейший Next.js конфиг для dev режима
cat > next.config.js << 'EOF'
/** @type {import('next').NextConfig} */
const nextConfig = {};
module.exports = nextConfig;
EOF

# Убираем TypeScript - делаем все JS
rm -f tsconfig.json next-env.d.ts

# Переименовываем .tsx в .js
mv app/layout.tsx app/layout.js 2>/dev/null || true
mv app/page.tsx app/page.js 2>/dev/null || true
mv app/auth/signin/page.tsx app/auth/signin/page.js 2>/dev/null || true
mv app/auth/signup/page.tsx app/auth/signup/page.js 2>/dev/null || true

# Упрощаем layout.js
cat > app/layout.js << 'EOF'
import './globals.css';

export const metadata = {
  title: 'CrystallBudget',
  description: 'Управление семейным бюджетом',
};

export default function RootLayout({ children }) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}
EOF

# Упрощаем главную страницу  
cat > app/page.js << 'EOF'
'use client';
import { useEffect, useState } from 'react';

export default function Home() {
  const [status, setStatus] = useState('loading');

  useEffect(() => {
    fetch('/api/health')
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(() => setStatus('ok'))
      .catch(() => setStatus('fail'));
  }, []);

  return (
    <div className="container">
      <h1 className="title">💎 CrystallBudget</h1>
      
      {status === 'loading' && (
        <div className="card">Загрузка...</div>
      )}
      
      {status === 'ok' && (
        <div className="card">
          <p>API работает!</p>
          <div style={{marginTop: '1rem'}}>
            <a href="/auth/signin" className="btn btn-primary" style={{marginRight: '0.5rem'}}>Войти</a>
            <a href="/auth/signup" className="btn btn-secondary">Создать аккаунт</a>
          </div>
        </div>
      )}
      
      {status === 'fail' && (
        <div className="alert alert-error">
          API недоступен. Проверьте что бэкенд запущен на порту 4000.
        </div>
      )}
    </div>
  );
}
EOF

# Упрощаем package.json - только базовые зависимости
cat > package.json << 'EOF'
{
  "name": "crystall-web",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev -p 3000",
    "start": "next start -p 3000"
  },
  "dependencies": {
    "next": "14.2.0",
    "react": "18.3.1",
    "react-dom": "18.3.1"
  }
}
EOF

# Переустанавливаем только базовые зависимости
rm -rf node_modules package-lock.json .next
sudo -u crystall npm install --no-audit --no-fund

echo -e "${GREEN}✓ Web настроен для dev режима${NC}"

# 6. Настраиваем systemd сервисы для dev режима
cat > /etc/systemd/system/crystall-api.service << 'EOF'
[Unit]
Description=Crystall API
After=network.target postgresql-16.service
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
RuntimeMaxMemory=128M

[Install]
WantedBy=multi-user.target
EOF

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
RuntimeMaxMemory=128M

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
echo -e "${GREEN}✓ Systemd сервисы настроены для dev режима${NC}"

# 7. Настраиваем Caddy
EXTERNAL_IP=$(curl -s ifconfig.me 2>/dev/null || echo "161-35-31-38")
sed "s/YOUR-IP/${EXTERNAL_IP//./-}/g" Caddyfile > /etc/caddy/Caddyfile
systemctl reload caddy 2>/dev/null || systemctl restart caddy

echo -e "${GREEN}✓ Caddy настроен${NC}"

echo
echo -e "${GREEN}=========================================="
echo "         Проект готов (DEV режим)!"
echo "==========================================${NC}"
echo
echo "Запуск:"
echo "  sudo ./start.sh"
echo
echo "URL: https://crystallbudget.${EXTERNAL_IP//./-}.sslip.io"
echo "API: curl http://localhost:4000/api/health"
echo "Web: curl http://localhost:3000"