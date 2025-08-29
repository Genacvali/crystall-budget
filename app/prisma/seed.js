const { PrismaClient } = require('@prisma/client');
const argon2 = require('argon2');

const prisma = new PrismaClient();

async function main() {
  console.log('🌱 Seeding database...');

  // Проверяем, есть ли уже данные
  const existingUser = await prisma.user.findFirst();
  if (existingUser) {
    console.log('✅ Database already seeded, skipping...');
    return;
  }

  // Создаём тестового пользователя
  const passwordHash = await argon2.hash('demo1234');
  
  const user = await prisma.user.create({
    data: {
      email: 'demo@crystall.local',
      passwordHash,
    }
  });

  // Создаём домохозяйство
  const household = await prisma.household.create({
    data: {
      name: 'Семья Демо',
      currency: 'RUB',
    }
  });

  // Добавляем пользователя как владельца
  await prisma.householdMember.create({
    data: {
      userId: user.id,
      householdId: household.id,
      role: 'OWNER',
    }
  });

  // Создаём категории
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

  const createdCategories = {};
  for (const categoryData of categories) {
    const category = await prisma.category.create({
      data: {
        ...categoryData,
        householdId: household.id,
      }
    });
    createdCategories[categoryData.name] = category;
  }

  // Создаём основной счёт
  const account = await prisma.account.create({
    data: {
      name: 'Основной счёт',
      householdId: household.id,
      currency: 'RUB',
      balance: 0,
    }
  });

  // Создаём бюджет на текущий месяц
  const now = new Date();
  const periodStart = new Date(now.getFullYear(), now.getMonth(), 1);
  const nextStart = new Date(now.getFullYear(), now.getMonth() + 1, 1);

  const budget = await prisma.budget.create({
    data: {
      name: `Бюджет ${periodStart.toLocaleDateString('ru-RU', { month: 'long', year: 'numeric' })}`,
      householdId: household.id,
      periodStart,
      nextStart,
      incomePlanned: 15000000, // 150,000 руб в копейках
      incomeActual: 12000000,  // 120,000 руб поступило
    }
  });

  // Создаём аллокации с разными типами
  const allocations = [
    {
      categoryName: 'Продукты',
      type: 'FIXED',
      amount: 4000000, // 40,000 руб
      planned: 4000000,
      spent: 2500000, // потрачено 25,000
    },
    {
      categoryName: 'Транспорт', 
      type: 'PERCENT',
      percent: 10,
      planned: Math.floor(12000000 * 0.10), // 10% от фактического дохода
      spent: 800000, // потрачено 8,000
    },
    {
      categoryName: 'Развлечения',
      type: 'PERCENT', 
      percent: 5,
      planned: Math.floor(12000000 * 0.05), // 5% от фактического дохода
      spent: 300000, // потрачено 3,000
    },
    {
      categoryName: 'Здоровье',
      type: 'FIXED',
      amount: 1500000, // 15,000 руб
      planned: 1500000,
      spent: 750000, // потрачено 7,500
    },
    {
      categoryName: 'Коммунальные',
      type: 'FIXED',
      amount: 800000, // 8,000 руб
      planned: 800000,
      spent: 800000, // оплачено полностью
    }
  ];

  for (const allocData of allocations) {
    const category = createdCategories[allocData.categoryName];
    if (category) {
      await prisma.allocation.create({
        data: {
          budgetId: budget.id,
          categoryId: category.id,
          type: allocData.type,
          amount: allocData.amount || null,
          percent: allocData.percent || null,
          planned: allocData.planned,
          spent: allocData.spent,
          rollover: 'SAME_CATEGORY',
        }
      });
    }
  }

  // Создаём несколько транзакций
  const transactions = [
    {
      amount: 8000000, // доход 80,000
      categoryId: null,
      note: 'Зарплата',
      occurredAt: new Date(now.getFullYear(), now.getMonth(), 5),
    },
    {
      amount: 4000000, // доход 40,000
      categoryId: null,
      note: 'Премия',
      occurredAt: new Date(now.getFullYear(), now.getMonth(), 15),
    },
    {
      amount: -1500000, // расход 15,000
      categoryId: createdCategories['Продукты'].id,
      note: 'Супермаркет',
      occurredAt: new Date(now.getFullYear(), now.getMonth(), 10),
    },
    {
      amount: -1000000, // расход 10,000
      categoryId: createdCategories['Продукты'].id,
      note: 'Продуктовый магазин',
      occurredAt: new Date(now.getFullYear(), now.getMonth(), 20),
    },
    {
      amount: -500000, // расход 5,000
      categoryId: createdCategories['Транспорт'].id,
      note: 'Заправка',
      occurredAt: new Date(now.getFullYear(), now.getMonth(), 12),
    },
    {
      amount: -300000, // расход 3,000
      categoryId: createdCategories['Транспорт'].id,
      note: 'Автобус',
      occurredAt: new Date(now.getFullYear(), now.getMonth(), 18),
    },
  ];

  for (const transactionData of transactions) {
    await prisma.transaction.create({
      data: {
        ...transactionData,
        householdId: household.id,
        userId: user.id,
        accountId: account.id,
        budgetId: budget.id,
      }
    });
  }

  console.log('✅ Seeding completed!');
  console.log('📧 Demo user: demo@crystall.local / demo1234');
  console.log('🏠 Household:', household.name);
  console.log('💰 Budget created with sample data');
}

main()
  .catch((e) => {
    console.error('❌ Seeding failed:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });