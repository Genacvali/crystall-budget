// «Сердце» фронта — обёртка над fetch с токеном из localStorage.
// Базовый URL берём из NEXT_PUBLIC_API_URL (или /api — через Caddy).

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api';

export function setToken(token: string) {
  localStorage.setItem('token', token);
}

export function getToken(): string | null {
  return typeof window === 'undefined' ? null : localStorage.getItem('token');
}

export async function api<T = any>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(init.headers || {});
  headers.set('content-type', 'application/json');
  if (token) headers.set('authorization', `Bearer ${token}`);

  const res = await fetch(`${API_BASE}${path}`, { ...init, headers, credentials: 'include' });
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}