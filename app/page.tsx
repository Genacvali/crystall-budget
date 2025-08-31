// /data/crystall-budget/app/page.tsx
'use client';

import { useEffect, useState } from 'react';

export default function Home() {
  const [status, setStatus] = useState<'loading'|'ok'|'fail'>('loading');
  const [ts, setTs] = useState<number|undefined>();

  useEffect(() => {
    const url = process.env.NEXT_PUBLIC_API_URL || '/api';
    fetch(`${url}/health`)
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(j => { setStatus('ok'); setTs(j.ts); })
      .catch(() => setStatus('fail'));
  }, []);

  return (
    <main className="max-w-lg mx-auto p-6">
      <div className="text-3xl font-bold mb-4">💎 CrystallBudget</div>

      {status === 'loading' && <div>Загрузка…</div>}
      {status === 'ok' && (
        <div className="space-y-4">
          <div className="rounded-md p-3 bg-green-50 border border-green-200">
            API живо ✅ {ts ? new Date(ts).toLocaleString() : ''}
          </div>
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