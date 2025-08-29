import { redirect } from 'next/navigation';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { prisma } from '@/lib/db';
import { formatMoney, calculateProgress, getProgressColor } from '@/lib/money';
import { getCurrentBudget } from '@/lib/periods';
import AppShell from '@/components/layout/AppShell';
import { PlusIcon, ArrowTrendingUpIcon, CurrencyDollarIcon } from '@heroicons/react/24/outline';
import Link from 'next/link';

async function getDashboardData(userId: string) {
  // Получаем домохозяйства пользователя
  const userHouseholds = await prisma.householdMember.findMany({
    where: { userId },
    include: {
      household: {
        include: {
          budgets: {
            include: {
              allocations: {
                include: {
                  category: true
                }
              }
            },
            orderBy: { periodStart: 'desc' }
          }
        }
      }
    }
  });

  if (userHouseholds.length === 0) {
    return null;
  }

  const household = userHouseholds[0].household;
  const currentBudget = getCurrentBudget(household.budgets);

  if (!currentBudget) {
    return {
      household,
      currentBudget: null,
      allocations: [],
      totalSpent: 0,
      totalPlanned: 0,
    };
  }

  const totalSpent = currentBudget.allocations?.reduce((sum, alloc) => sum + alloc.spent, 0) || 0;
  const totalPlanned = currentBudget.allocations?.reduce((sum, alloc) => sum + alloc.planned, 0) || 0;

  return {
    household,
    currentBudget,
    allocations: currentBudget.allocations || [],
    totalSpent,
    totalPlanned,
  };
}

export default async function DashboardPage() {
  const session = await getServerSession(authOptions);
  
  if (!session?.user?.id) {
    redirect('/auth/signin');
  }

  const dashboardData = await getDashboardData(session.user.id);

  if (!dashboardData) {
    redirect('/onboarding');
  }

  const { household, currentBudget, allocations, totalSpent, totalPlanned } = dashboardData;

  const remainingBudget = totalPlanned - totalSpent;
  const incomeReceived = currentBudget?.incomeActual || 0;
  const incomePlanned = currentBudget?.incomePlanned || 0;

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Дашборд</h1>
            <p className="text-gray-600">{household.name}</p>
          </div>
          <Link
            href="/transactions/new"
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
          >
            <PlusIcon className="h-4 w-4 mr-2" />
            Добавить операцию
          </Link>
        </div>

        {!currentBudget ? (
          // No current budget
          <div className="text-center py-12">
            <ArrowTrendingUpIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">Нет активного бюджета</h3>
            <p className="mt-1 text-sm text-gray-500">
              Создайте бюджет для начала управления финансами
            </p>
            <div className="mt-6">
              <Link
                href="/budgets/new"
                className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
              >
                <PlusIcon className="h-4 w-4 mr-2" />
                Создать бюджет
              </Link>
            </div>
          </div>
        ) : (
          <>
            {/* Stats */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="stat-card">
                <div className="flex items-center justify-center w-8 h-8 bg-green-100 rounded-md mx-auto mb-2">
                  <CurrencyDollarIcon className="w-5 h-5 text-green-600" />
                </div>
                <dt className="text-sm font-medium text-gray-500">Доход получен</dt>
                <dd className="text-2xl font-bold text-gray-900">
                  {formatMoney(incomeReceived)}
                </dd>
                {incomePlanned > 0 && (
                  <p className="text-xs text-gray-500 mt-1">
                    из {formatMoney(incomePlanned)} запланированных
                  </p>
                )}
              </div>

              <div className="stat-card">
                <div className="flex items-center justify-center w-8 h-8 bg-blue-100 rounded-md mx-auto mb-2">
                  <ArrowTrendingUpIcon className="w-5 h-5 text-blue-600" />
                </div>
                <dt className="text-sm font-medium text-gray-500">Запланировано</dt>
                <dd className="text-2xl font-bold text-gray-900">
                  {formatMoney(totalPlanned)}
                </dd>
              </div>

              <div className="stat-card">
                <div className="flex items-center justify-center w-8 h-8 bg-red-100 rounded-md mx-auto mb-2">
                  <span className="text-red-600 font-medium">−</span>
                </div>
                <dt className="text-sm font-medium text-gray-500">Потрачено</dt>
                <dd className="text-2xl font-bold text-gray-900">
                  {formatMoney(totalSpent)}
                </dd>
              </div>

              <div className="stat-card">
                <div className="flex items-center justify-center w-8 h-8 bg-purple-100 rounded-md mx-auto mb-2">
                  <span className="text-purple-600 font-medium">=</span>
                </div>
                <dt className="text-sm font-medium text-gray-500">Остаток</dt>
                <dd className={`text-2xl font-bold ${remainingBudget >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {formatMoney(remainingBudget)}
                </dd>
              </div>
            </div>

            {/* Categories Progress */}
            <div className="card">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-medium text-gray-900">Категории</h3>
                <Link
                  href="/categories"
                  className="text-sm text-primary-600 hover:text-primary-500"
                >
                  Все категории →
                </Link>
              </div>

              {allocations.length === 0 ? (
                <p className="text-gray-500 text-center py-4">
                  Категории не настроены
                </p>
              ) : (
                <div className="space-y-4">
                  {allocations.map((allocation) => {
                    const progress = calculateProgress(allocation.spent, allocation.planned);
                    const remaining = allocation.planned - allocation.spent;
                    
                    return (
                      <div key={allocation.id} className="flex items-center space-x-4">
                        <div className="flex-shrink-0 w-8 h-8 flex items-center justify-center">
                          <span className="text-xl">{allocation.category.icon}</span>
                        </div>
                        
                        <div className="flex-1 min-w-0">
                          <div className="flex justify-between items-center mb-1">
                            <p className="text-sm font-medium text-gray-900 truncate">
                              {allocation.category.name}
                            </p>
                            <div className="text-sm text-gray-500">
                              {formatMoney(allocation.spent)} / {formatMoney(allocation.planned)}
                            </div>
                          </div>
                          
                          <div className="progress-bar">
                            <div
                              className={`progress-fill ${
                                progress <= 50 ? 'bg-green-500' :
                                progress <= 80 ? 'bg-yellow-500' :
                                progress < 100 ? 'bg-orange-500' :
                                'bg-red-500'
                              }`}
                              style={{ width: `${Math.min(progress, 100)}%` }}
                            />
                          </div>
                          
                          <div className="flex justify-between items-center mt-1">
                            <span className={`text-xs ${getProgressColor(progress)}`}>
                              {progress.toFixed(0)}%
                            </span>
                            <span className={`text-xs ${remaining >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                              {remaining >= 0 ? 'остаток: ' : 'превышение: '}{formatMoney(Math.abs(remaining))}
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Quick Actions */}
            <div className="grid grid-cols-2 gap-4">
              <Link
                href="/transactions/new?type=expense"
                className="card hover:shadow-md transition-shadow p-6 text-center"
              >
                <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-3">
                  <span className="text-red-600 text-xl font-bold">−</span>
                </div>
                <h3 className="text-sm font-medium text-gray-900">Добавить расход</h3>
              </Link>

              <Link
                href="/transactions/new?type=income"
                className="card hover:shadow-md transition-shadow p-6 text-center"
              >
                <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-3">
                  <span className="text-green-600 text-xl font-bold">+</span>
                </div>
                <h3 className="text-sm font-medium text-gray-900">Добавить доход</h3>
              </Link>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}