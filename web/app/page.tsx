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
    <main className="max-w-lg mx-auto p-6">
      <div className="text-3xl font-bold mb-4">💎 CrystallBudget</div>
      {status === 'loading' && <div>Загрузка…</div>}
      {status === 'ok' && (
        <div className="space-y-4">
          <div className="space-x-2">
            <a href="/auth/signin" className="px-4 py-2 rounded bg-blue-600 text-white">Войти</a>
            <a href="/auth/signup" className="px-4 py-2 rounded bg-gray-200">Создать аккаунт</a>
          </div>
        </div>
      )}
      {status === 'fail' && (
        <div className="rounded-md p-3 bg-red-50 border border-red-200">
          Не удалось достучаться до API (проверь Caddy/бэкенд)
        </div>
      )}
    </main>
  );
}