import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { redirect } from 'next/navigation';

export default async function HomePage() {
  const session = await getServerSession(authOptions);

  if (!session) {
    redirect('/auth/signin');
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            Добро пожаловать в CrystallBudget! 💎
          </h1>
          <p className="text-gray-600">
            Умное управление семейным бюджетом
          </p>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6">
          <h2 className="text-lg font-semibold mb-4">Ваши домохозяйства</h2>
          <div className="text-gray-500 text-center py-8">
            Скоро здесь будет интерфейс управления бюджетом
          </div>
        </div>
      </div>
    </div>
  );
}