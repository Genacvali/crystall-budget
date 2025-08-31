'use client';

import { useEffect, useState } from 'react';
import { AuthService } from '@/lib/auth';
import { APIClient } from '@/lib/api';

export default function HomePage() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [health, setHealth] = useState<any>(null);

  useEffect(() => {
    const checkAuth = async () => {
      setIsAuthenticated(AuthService.isAuthenticated());
      
      try {
        const healthData = await APIClient.health();
        setHealth(healthData);
      } catch (error) {
        console.error('API health check failed:', error);
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, []);

  const handleLogout = () => {
    AuthService.logout();
    setIsAuthenticated(false);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg">Загрузка...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-8">
      <div className="max-w-md w-full text-center space-y-6">
        <h1 className="text-4xl font-bold text-blue-600">💎 CrystallBudget</h1>
        <p className="text-gray-600">Умное управление семейным бюджетом</p>
        
        {health && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-3">
            <p className="text-sm text-green-700">
              ✅ API работает (ts: {health.ts})
            </p>
          </div>
        )}

        {isAuthenticated ? (
          <div className="space-y-4">
            <p className="text-green-600">✅ Вы авторизованы</p>
            <button
              onClick={handleLogout}
              className="w-full bg-red-600 text-white py-2 px-4 rounded-lg hover:bg-red-700 transition"
            >
              Выйти
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-gray-600">Войдите в аккаунт</p>
            <div className="space-y-2">
              <a
                href="/auth/login"
                className="block w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 transition text-center"
              >
                Войти
              </a>
              <a
                href="/auth/signup"
                className="block w-full border border-blue-600 text-blue-600 py-2 px-4 rounded-lg hover:bg-blue-50 transition text-center"
              >
                Создать аккаунт
              </a>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}