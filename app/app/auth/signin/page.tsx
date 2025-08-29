'use client';

import { useState } from 'react';
import { signIn, getSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';

export default function SignInPage() {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const result = await signIn('credentials', {
        email: formData.email,
        password: formData.password,
        redirect: false,
      });

      if (result?.error) {
        setError('Неверный email или пароль');
      } else {
        // Получаем обновлённую сессию
        const session = await getSession();
        if (session) {
          router.push('/');
          router.refresh();
        }
      }
    } catch (err) {
      setError('Произошла ошибка при входе');
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }));
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <div className="mx-auto h-12 w-12 flex items-center justify-center">
            <span className="text-3xl">💎</span>
          </div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Вход в CrystallBudget
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Или{' '}
            <Link
              href="/auth/signup"
              className="font-medium text-primary-600 hover:text-primary-500"
            >
              создайте новый аккаунт
            </Link>
          </p>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="space-y-4">
            <Input
              label="Email"
              name="email"
              type="email"
              autoComplete="email"
              required
              fullWidth
              value={formData.email}
              onChange={handleChange}
              placeholder="your@email.com"
            />
            <Input
              label="Пароль"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              fullWidth
              value={formData.password}
              onChange={handleChange}
              placeholder="Введите пароль"
            />
          </div>

          {error && (
            <div className="rounded-md bg-danger-50 p-4">
              <div className="text-sm text-danger-700">
                {error}
              </div>
            </div>
          )}

          <div>
            <Button
              type="submit"
              fullWidth
              loading={isLoading}
              disabled={!formData.email || !formData.password}
            >
              Войти
            </Button>
          </div>

          <div className="text-center">
            <p className="text-xs text-gray-500">
              Демо-аккаунт: demo@crystall.local / demo1234
            </p>
          </div>
        </form>
      </div>
    </div>
  );
}