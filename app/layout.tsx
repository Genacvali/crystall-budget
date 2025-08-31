import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'CrystallBudget',
  description: 'Умное управление семейным бюджетом',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ru">
      <body className="bg-gray-50 text-gray-900">
        {children}
      </body>
    </html>
  )
}