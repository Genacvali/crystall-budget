export const metadata = {
  title: 'CrystallBudget',
  description: 'Управление семейным бюджетом',
};
export const viewport = { width: 'device-width', initialScale: 1, themeColor: '#3b82f6' };

import './globals.css';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body className="min-h-screen bg-gray-50 text-gray-900">{children}</body>
    </html>
  );
}