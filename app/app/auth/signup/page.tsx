'use client';

import { useState } from 'react';
import { signIn } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';

export default function SignUpPage() {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    householdName: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.email) {
      newErrors.email = 'Email обязателен';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Некорректный email';
    }

    if (!formData.password) {
      newErrors.password = 'Пароль обязателен';
    } else if (formData.password.length < 8) {
      newErrors.password = 'Пароль должен содержать минимум 8 символов';
    }

    if (!formData.confirmPassword) {
      newErrors.confirmPassword = 'Подтвердите пароль';
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Пароли не совпадают';
    }

    if (!formData.householdName) {
      formData.householdName = 'Семья'; // Значение по умолчанию
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) return;

    setIsLoading(true);
    setErrors({});

    try {
      const response = await fetch('/api/users', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: formData.email,
          password: formData.password,
          householdName: formData.householdName || 'Семья',
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        setErrors({ submit: data.error || 'Произошла ошибка при регистрации' });
        return;
      }

      // Автоматически входим после регистрации
      const signInResult = await signIn('credentials', {
        email: formData.email,
        password: formData.password,
        redirect: false,
      });

      if (signInResult?.ok) {
        router.push('/');
        router.refresh();
      } else {
        // Если автовход не удался, перенаправляем на страницу входа
        router.push('/auth/signin?message=registration_success');
      }
    } catch (err) {
      setErrors({ submit: 'Произошла ошибка при регистрации' });
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }));
    // Очищаем ошибку для конкретного поля
    if (errors[e.target.name]) {
      setErrors(prev => ({
        ...prev,
        [e.target.name]: ''
      }));
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <div className="mx-auto h-12 w-12 flex items-center justify-center">
            <span className="text-3xl">💎</span>
          </div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Создать аккаунт
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Или{' '}
            <Link
              href="/auth/signin"
              className="font-medium text-primary-600 hover:text-primary-500"
            >
              войдите в существующий
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
              error={errors.email}
              placeholder="your@email.com"
            />
            <Input
              label="Пароль"
              name="password"
              type="password"
              autoComplete="new-password"
              required
              fullWidth
              value={formData.password}
              onChange={handleChange}
              error={errors.password}
              placeholder="Минимум 8 символов"
              helperText="Используйте заглавные и строчные буквы, цифры"
            />
            <Input
              label="Подтвердите пароль"
              name="confirmPassword"
              type="password"
              autoComplete="new-password"
              required
              fullWidth
              value={formData.confirmPassword}
              onChange={handleChange}
              error={errors.confirmPassword}
              placeholder="Повторите пароль"
            />
            <Input
              label="Название домохозяйства"
              name="householdName"
              type="text"
              fullWidth
              value={formData.householdName}
              onChange={handleChange}
              error={errors.householdName}
              placeholder="Семья (по умолчанию)"
              helperText="Можно изменить позже в настройках"
            />
          </div>

          {errors.submit && (
            <div className="rounded-md bg-danger-50 p-4">
              <div className="text-sm text-danger-700">
                {errors.submit}
              </div>
            </div>
          )}

          <div>
            <Button
              type="submit"
              fullWidth
              loading={isLoading}
              disabled={!formData.email || !formData.password || !formData.confirmPassword}
            >
              Создать аккаунт
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}