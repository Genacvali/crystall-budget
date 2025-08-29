import type { Metadata, Viewport } from 'next';
import { Inter } from 'next/font/google';
import { getServerSession } from 'next-auth';
import { SessionProvider } from '@/components/providers/SessionProvider';
import { authOptions } from '@/lib/auth';
import './globals.css';

const inter = Inter({ subsets: ['latin', 'cyrillic'] });

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: '#3b82f6',
  colorScheme: 'light',
  viewportFit: 'cover',
};

export const metadata: Metadata = {
  title: {
    template: '%s | CrystallBudget',
    default: 'CrystallBudget - Умное управление бюджетом',
  },
  description: 'Персональный помощник для управления семейным бюджетом с динамическим распределением доходов',
  keywords: ['бюджет', 'финансы', 'деньги', 'семья', 'планирование', 'доходы', 'расходы'],
  authors: [{ name: 'CrystallBudget Team' }],
  creator: 'CrystallBudget',
  publisher: 'CrystallBudget',
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  manifest: '/manifest.json',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'default',
    title: 'CrystallBudget',
  },
  openGraph: {
    type: 'website',
    locale: 'ru_RU',
    title: 'CrystallBudget - Умное управление бюджетом',
    description: 'Персональный помощник для управления семейным бюджетом',
    siteName: 'CrystallBudget',
  },
  twitter: {
    card: 'summary',
    title: 'CrystallBudget',
    description: 'Умное управление семейным бюджетом',
  },
  robots: {
    index: false,
    follow: false,
  },
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await getServerSession(authOptions);

  return (
    <html lang="ru" className="h-full">
      <head>
        <link rel="icon" href="/favicon.ico" sizes="any" />
        <link rel="icon" href="/icons/icon-192x192.png" type="image/png" />
        <link rel="apple-touch-icon" href="/icons/icon-192x192.png" />
      </head>
      <body className={`${inter.className} h-full bg-gray-50`}>
        <SessionProvider session={session}>
          {children}
        </SessionProvider>
      </body>
    </html>
  );
}