'use client';

import { ReactNode } from 'react';
import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { clsx } from 'clsx';
import { 
  HomeIcon, 
  ChartBarIcon, 
  TagIcon,
  CogIcon,
  PlusIcon
} from '@heroicons/react/24/outline';
import {
  HomeIcon as HomeIconSolid,
  ChartBarIcon as ChartBarIconSolid, 
  TagIcon as TagIconSolid,
  CogIcon as CogIconSolid
} from '@heroicons/react/24/solid';

interface AppShellProps {
  children: ReactNode;
}

const navigation = [
  { name: 'Дашборд', href: '/', icon: HomeIcon, iconSolid: HomeIconSolid },
  { name: 'Бюджеты', href: '/budgets', icon: ChartBarIcon, iconSolid: ChartBarIconSolid },
  { name: 'Категории', href: '/categories', icon: TagIcon, iconSolid: TagIconSolid },
  { name: 'Настройки', href: '/settings', icon: CogIcon, iconSolid: CogIconSolid },
];

const AppShell = ({ children }: AppShellProps) => {
  const pathname = usePathname();

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="bg-white shadow-sm border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <h1 className="text-xl font-bold text-gray-900">
                    💎 CrystallBudget
                  </h1>
                </div>
              </div>
              
              {/* Quick add button */}
              <button className="inline-flex items-center p-2 border border-transparent rounded-full shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500">
                <PlusIcon className="h-6 w-6" aria-hidden="true" />
              </button>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            {children}
          </div>
        </main>

        {/* Bottom navigation for mobile */}
        <nav className="bg-white border-t border-gray-200 sm:hidden">
          <div className="flex justify-around">
            {navigation.map((item) => {
              const isActive = pathname === item.href;
              const Icon = isActive ? item.iconSolid : item.icon;
              
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={clsx(
                    'flex flex-col items-center py-2 px-3 text-xs font-medium min-h-touch',
                    isActive
                      ? 'text-primary-600'
                      : 'text-gray-500 hover:text-gray-700'
                  )}
                >
                  <Icon className="h-6 w-6 mb-1" aria-hidden="true" />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </div>
        </nav>
      </div>

      {/* Sidebar for desktop */}
      <aside className="hidden sm:flex sm:flex-shrink-0">
        <div className="flex flex-col w-64">
          <nav className="flex-1 px-4 py-4 bg-white border-r border-gray-200 space-y-1">
            {navigation.map((item) => {
              const isActive = pathname === item.href;
              const Icon = isActive ? item.iconSolid : item.icon;
              
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={clsx(
                    'group flex items-center px-3 py-2 text-sm font-medium rounded-md',
                    isActive
                      ? 'bg-primary-50 border-r-2 border-primary-600 text-primary-700'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  )}
                >
                  <Icon
                    className={clsx(
                      'mr-3 h-6 w-6 flex-shrink-0',
                      isActive ? 'text-primary-500' : 'text-gray-400 group-hover:text-gray-500'
                    )}
                    aria-hidden="true"
                  />
                  {item.name}
                </Link>
              );
            })}
          </nav>
        </div>
      </aside>
    </div>
  );
};

export default AppShell;