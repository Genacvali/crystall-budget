'use client';

import { useState } from 'react';
import { signIn } from 'next-auth/react';

export default function SignInPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const canSubmit = email.trim() !== '' && password.trim() !== '';

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit || loading) return;
    setLoading(true);
    const res = await signIn('credentials', {
      email,
      password,
      redirect: true,
      callbackUrl: '/',
    });
    // next-auth сам редиректнёт по callbackUrl
    setLoading(false);
  }

  return (
    <div className="min-h-screen grid place-items-center bg-gray-50">
      <form onSubmit={onSubmit} className="w-full max-w-sm bg-white p-6 rounded-2xl shadow">
        <h1 className="text-2xl font-bold mb-4 text-center">Вход в CrystallBudget</h1>
        <label className="block text-sm mb-1">Email</label>
        <input
          type="email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          className="w-full rounded-xl border px-4 py-3 mb-3 outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="you@example.com"
          autoComplete="email"
        />
        <label className="block text-sm mb-1">Пароль</label>
        <input
          type="password"
          value={password}
          onChange={e => setPassword(e.target.value)}
          className="w-full rounded-xl border px-4 py-3 mb-4 outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="••••••••"
          autoComplete="current-password"
        />
        <button
          type="submit"
          disabled={!canSubmit || loading}
          className={`w-full rounded-2xl px-4 py-3 font-medium text-white ${canSubmit && !loading ? 'bg-blue-600 hover:bg-blue-700' : 'bg-gray-300 cursor-not-allowed'}`}
        >
          {loading ? 'Входим…' : 'Войти'}
        </button>
      </form>
    </div>
  );
}