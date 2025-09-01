'use client';
import { useState } from 'react';
import { api } from '../../../lib/api';

export default function SignUp() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [ok, setOk] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    try {
      await api('/auth/signup', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      setOk(true);
    } catch (e:any) {
      setErr('Не удалось создать аккаунт (возможно, email занят)');
    }
  }

  return (
    <main className="max-w-md mx-auto p-6 space-y-4">
      <h1 className="text-2xl font-bold">Создать аккаунт</h1>
      <form onSubmit={onSubmit} className="space-y-3">
        <input className="w-full border p-2 rounded" value={email} onChange={e=>setEmail(e.target.value)} placeholder="email" />
        <input className="w-full border p-2 rounded" value={password} onChange={e=>setPassword(e.target.value)} type="password" placeholder="password" />
        <button className="px-4 py-2 rounded bg-blue-600 text-white">Создать</button>
      </form>
      {ok && <div className="text-green-700">Готово. Теперь можно <a className="underline" href="/auth/signin">войти</a>.</div>}
      {err && <div className="text-red-600">{err}</div>}
    </main>
  );
}