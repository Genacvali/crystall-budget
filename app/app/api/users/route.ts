import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/db';
import { hashPassword, validateEmail, validatePassword } from '@/lib/security';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { email, password, householdName } = body;

    // Валидация
    if (!email || !password) {
      return NextResponse.json(
        { error: 'Email и пароль обязательны' },
        { status: 400 }
      );
    }

    if (!validateEmail(email)) {
      return NextResponse.json(
        { error: 'Некорректный email' },
        { status: 400 }
      );
    }

    const passwordValidation = validatePassword(password);
    if (!passwordValidation.isValid) {
      return NextResponse.json(
        { error: passwordValidation.errors[0] },
        { status: 400 }
      );
    }

    // Проверка существующего пользователя
    const existingUser = await prisma.user.findUnique({
      where: { email: email.toLowerCase() }
    });

    if (existingUser) {
      return NextResponse.json(
        { error: 'Пользователь с таким email уже существует' },
        { status: 400 }
      );
    }

    // Хэшируем пароль
    const passwordHash = await hashPassword(password);

    // Создаём пользователя с домохозяйством в транзакции
    const result = await prisma.$transaction(async (tx) => {
      // Создаём пользователя
      const user = await tx.user.create({
        data: {
          email: email.toLowerCase(),
          passwordHash,
        }
      });

      // Создаём домохозяйство
      const household = await tx.household.create({
        data: {
          name: householdName || 'Семья',
        }
      });

      // Добавляем пользователя как владельца домохозяйства
      await tx.householdMember.create({
        data: {
          userId: user.id,
          householdId: household.id,
          role: 'OWNER',
        }
      });

      // Создаём базовые категории
      const categories = [
        { name: 'Продукты', icon: '🛒', color: '#ef4444' },
        { name: 'Транспорт', icon: '🚗', color: '#3b82f6' },
        { name: 'Развлечения', icon: '🎬', color: '#8b5cf6' },
        { name: 'Здоровье', icon: '🏥', color: '#22c55e' },
        { name: 'Образование', icon: '📚', color: '#f59e0b' },
        { name: 'Коммунальные', icon: '🏠', color: '#06b6d4' },
        { name: 'Одежда', icon: '👕', color: '#ec4899' },
        { name: 'Прочее', icon: '💰', color: '#6b7280' },
      ];

      for (const category of categories) {
        await tx.category.create({
          data: {
            ...category,
            householdId: household.id,
          }
        });
      }

      // Основной счёт не создаём - используем упрощённую схему без модели Account

      return { user, household };
    });

    return NextResponse.json({
      message: 'Пользователь успешно создан',
      userId: result.user.id,
      householdId: result.household.id,
    });

  } catch (error) {
    console.error('Registration error:', error);
    return NextResponse.json(
      { error: 'Внутренняя ошибка сервера' },
      { status: 500 }
    );
  }
}