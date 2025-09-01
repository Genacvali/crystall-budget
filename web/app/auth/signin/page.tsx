'use client';
import { useState } from 'react';
import { api, setToken } from '../../../lib/api';

export default function SignIn() {
  const [email, setEmail] = useState('demo@crystall.local');
  const [password, setPassword] = useState('demo1234');
  const [err, setErr] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    try {
      const res = await api<{token:string}>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      setToken(res.token);
      location.href = '/'; // просто возвращаемся на главную
    } catch {
      setErr('Неверные учетные данные');
    }
  }

  return (
    <main className="max-w-md mx-auto p-6 space-y-4">
      <h1 className="text-2xl font-bold">Войти</h1>
      <form onSubmit={onSubmit} className="space-y-3">
        <input className="w-full border p-2 rounded" value={email} onChange={e=>setEmail(e.target.value)} placeholder="email" />
        <input className="w-full border p-2 rounded" value={password} onChange={e=>setPassword(e.target.value)} type="password" placeholder="password" />
        <button className="px-4 py-2 rounded bg-blue-600 text-white">Войти</button>
      </form>
      {err && <div className="text-red-600">{err}</div>}
    </main>
  );
}