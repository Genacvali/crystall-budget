export const CURRENCY_SYMBOLS = {
  RUB: '₽',
  USD: '$',
  EUR: '€',
} as const;

export type Currency = keyof typeof CURRENCY_SYMBOLS;

export function formatMoney(amountInCents: number, currency: Currency = 'RUB'): string {
  const amount = amountInCents / 100;
  const symbol = CURRENCY_SYMBOLS[currency];
  
  return new Intl.NumberFormat('ru-RU', {
    style: 'decimal',
    minimumFractionDigits: amount % 1 === 0 ? 0 : 2,
    maximumFractionDigits: 2,
  }).format(amount) + ` ${symbol}`;
}

export function parseMoney(value: string): number {
  // Убираем пробелы, запятые заменяем на точки, убираем валютные символы
  const cleaned = value
    .replace(/\s/g, '')
    .replace(/,/g, '.')
    .replace(/[₽$€]/g, '');
  
  const number = parseFloat(cleaned);
  return isNaN(number) ? 0 : Math.round(number * 100);
}

export function formatPercent(value: number): string {
  return new Intl.NumberFormat('ru-RU', {
    style: 'percent',
    minimumFractionDigits: 0,
    maximumFractionDigits: 1,
  }).format(value / 100);
}

export function calculateProgress(spent: number, planned: number): number {
  if (planned === 0) return 0;
  return Math.min((spent / planned) * 100, 100);
}

export function getProgressColor(progress: number): string {
  if (progress < 50) return 'text-green-600';
  if (progress < 80) return 'text-yellow-600';
  if (progress < 100) return 'text-orange-600';
  return 'text-red-600';
}