import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/db';
import { hashPassword } from '@/lib/security';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { email, password, householdName } = body;

    if (!email || !password) {
      return NextResponse.json(
        { error: 'Email и пароль обязательны' },
        { status: 400 }
      );
    }

    // Проверяем, существует ли пользователь
    const existingUser = await prisma.user.findUnique({
      where: { email: email.toLowerCase() }
    });

    if (existingUser) {
      return NextResponse.json(
        { error: 'Пользователь с таким email уже существует' },
        { status: 400 }
      );
    }

    // Создаём пользователя и домохозяйство в транзакции
    const result = await prisma.$transaction(async (tx) => {
      // Хэшируем пароль
      const passwordHash = await hashPassword(password);

      // Создаём пользователя
      const user = await tx.user.create({
        data: {
          email: email.toLowerCase(),
          passwordHash,
        }
      });

      // Создаём домохозяйство
      let household;
      if (householdName?.trim()) {
        household = await tx.household.create({
          data: {
            name: householdName.trim(),
            members: {
              create: {
                userId: user.id,
                role: 'OWNER'
              }
            }
          }
        });
      } else {
        // Создаём домохозяйство с именем по умолчанию
        household = await tx.household.create({
          data: {
            name: `Семья ${user.email.split('@')[0]}`,
            members: {
              create: {
                userId: user.id,
                role: 'OWNER'
              }
            }
          }
        });
      }

      return { user, household };
    });

    return NextResponse.json({
      message: 'Пользователь успешно создан',
      userId: result.user.id,
      householdId: result.household.id
    });

  } catch (error) {
    console.error('Registration error:', error);
    return NextResponse.json(
      { error: 'Ошибка при создании пользователя' },
      { status: 500 }
    );
  }
}