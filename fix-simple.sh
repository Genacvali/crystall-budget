#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}Простое исправление без Tailwind...${NC}"

cd /data/crystall-budget/web

# Удаляем Tailwind конфигурацию и стили
rm -f tailwind.config.js postcss.config.js
echo -e "${GREEN}✓ Удалили Tailwind конфиги${NC}"

# Создаем простой CSS
cat > app/globals.css << 'EOF'
/* Простые стили без Tailwind */
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  line-height: 1.6;
  color: #333;
  background-color: #f9fafb;
  min-height: 100vh;
}

.container {
  max-width: 500px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

.form {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  margin-bottom: 1rem;
}

.form-group {
  margin-bottom: 1rem;
}

.input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 1rem;
  transition: border-color 0.2s;
}

.input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  text-decoration: none;
  display: inline-block;
  text-align: center;
}

.btn-primary {
  background-color: #3b82f6;
  color: white;
}

.btn-primary:hover {
  background-color: #2563eb;
}

.btn-secondary {
  background-color: #e5e7eb;
  color: #374151;
}

.btn-secondary:hover {
  background-color: #d1d5db;
}

.error {
  color: #dc2626;
  margin-top: 0.5rem;
  font-size: 0.875rem;
}

.success {
  color: #059669;
  margin-top: 0.5rem;
  font-size: 0.875rem;
}

.title {
  font-size: 2rem;
  font-weight: bold;
  margin-bottom: 1rem;
  color: #111827;
}

.subtitle {
  font-size: 1.5rem;
  font-weight: 600;
  margin-bottom: 1.5rem;
  color: #374151;
}

.link {
  color: #3b82f6;
  text-decoration: underline;
}

.link:hover {
  color: #2563eb;
}

.card {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  margin-bottom: 1rem;
}

.alert {
  padding: 1rem;
  border-radius: 6px;
  margin-bottom: 1rem;
}

.alert-error {
  background-color: #fef2f2;
  border: 1px solid #fecaca;
  color: #dc2626;
}

.alert-success {
  background-color: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #059669;
}

.flex {
  display: flex;
}

.space-x-2 > * + * {
  margin-left: 0.5rem;
}

.space-y-4 > * + * {
  margin-top: 1rem;
}

.text-center {
  text-align: center;
}

.mb-4 {
  margin-bottom: 1rem;
}
EOF

echo -e "${GREEN}✓ Создали простой CSS${NC}"

# Исправляем layout.tsx
cat > app/layout.tsx << 'EOF'
import './globals.css';

export const metadata = {
  title: 'CrystallBudget',
  description: 'Управление семейным бюджетом',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}
EOF

echo -e "${GREEN}✓ Обновили layout.tsx${NC}"

# Исправляем главную страницу
cat > app/page.tsx << 'EOF'
'use client';
import { useEffect, useState } from 'react';

export default function Home() {
  const [status, setStatus] = useState<'loading'|'ok'|'fail'>('loading');

  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_API_URL || '/api';
    fetch(`${base}/health`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(() => setStatus('ok'))
      .catch(() => setStatus('fail'));
  }, []);

  return (
    <div className="container">
      <h1 className="title">💎 CrystallBudget</h1>
      
      {status === 'loading' && (
        <div className="card">
          <p>Загрузка...</p>
        </div>
      )}
      
      {status === 'ok' && (
        <div className="card">
          <div className="space-y-4">
            <p>API работает! Система готова к использованию.</p>
            <div className="flex space-x-2">
              <a href="/auth/signin" className="btn btn-primary">Войти</a>
              <a href="/auth/signup" className="btn btn-secondary">Создать аккаунт</a>
            </div>
          </div>
        </div>
      )}
      
      {status === 'fail' && (
        <div className="alert alert-error">
          Не удалось достучаться до API. Проверьте что бэкенд запущен.
        </div>
      )}
    </div>
  );
}
EOF

echo -e "${GREEN}✓ Обновили главную страницу${NC}"

# Исправляем страницу входа
cat > app/auth/signin/page.tsx << 'EOF'
'use client';
import { useState } from 'react';
import { api, setToken } from '../../../lib/api';

export default function SignIn() {
  const [email, setEmail] = useState('demo@crystall.local');
  const [password, setPassword] = useState('demo1234');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await api<{token:string}>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      setToken(res.token);
      window.location.href = '/';
    } catch {
      setError('Неверные учетные данные');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container">
      <div className="form">
        <h1 className="subtitle">Вход в систему</h1>
        
        <form onSubmit={onSubmit}>
          <div className="form-group">
            <input
              className="input"
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="Email"
              required
            />
          </div>
          
          <div className="form-group">
            <input
              className="input"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="Пароль"
              required
            />
          </div>
          
          <button className="btn btn-primary" disabled={loading}>
            {loading ? 'Вход...' : 'Войти'}
          </button>
        </form>
        
        {error && <div className="error">{error}</div>}
        
        <p style={{ marginTop: '1rem' }}>
          Нет аккаунта? <a href="/auth/signup" className="link">Создать</a>
        </p>
      </div>
    </div>
  );
}
EOF

echo -e "${GREEN}✓ Обновили страницу входа${NC}"

# Исправляем страницу регистрации
cat > app/auth/signup/page.tsx << 'EOF'
'use client';
import { useState } from 'react';
import { api } from '../../../lib/api';

export default function SignUp() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await api('/auth/signup', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      setSuccess(true);
    } catch {
      setError('Не удалось создать аккаунт (возможно, email занят)');
    } finally {
      setLoading(false);
    }
  }

  if (success) {
    return (
      <div className="container">
        <div className="alert alert-success">
          <h2>Аккаунт создан!</h2>
          <p>Теперь можете <a href="/auth/signin" className="link">войти в систему</a>.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container">
      <div className="form">
        <h1 className="subtitle">Создание аккаунта</h1>
        
        <form onSubmit={onSubmit}>
          <div className="form-group">
            <input
              className="input"
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="Email"
              required
            />
          </div>
          
          <div className="form-group">
            <input
              className="input"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="Пароль"
              required
            />
          </div>
          
          <button className="btn btn-primary" disabled={loading}>
            {loading ? 'Создание...' : 'Создать аккаунт'}
          </button>
        </form>
        
        {error && <div className="error">{error}</div>}
        
        <p style={{ marginTop: '1rem' }}>
          Есть аккаунт? <a href="/auth/signin" className="link">Войти</a>
        </p>
      </div>
    </div>
  );
}
EOF

echo -e "${GREEN}✓ Обновили страницу регистрации${NC}"

# Убираем Tailwind из package.json
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
    "typescript": "^5.5.0"
  }
}
EOF

echo -e "${GREEN}✓ Упростили package.json${NC}"

# Переустанавливаем зависимости
rm -rf node_modules package-lock.json
echo "Переустановка зависимостей..."
sudo -u crystall npm install

# Пересобираем
echo "Пересборка проекта..."
sudo -u crystall npm run build

if [[ $? -eq 0 ]]; then
    echo -e "${GREEN}✓ Web успешно собран${NC}"
else
    echo -e "${RED}✗ Ошибка сборки${NC}"
    exit 1
fi

echo
echo -e "${GREEN}=========================================="
echo "     Простая версия готова!"
echo "==========================================${NC}"
echo
echo "Теперь можно запускать:"
echo "  sudo ./start.sh"