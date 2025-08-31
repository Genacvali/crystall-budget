/**
 * Утилиты для работы с деньгами
 * Все суммы хранятся в копейках (целые числа)
 */

export const CURRENCY_SYMBOL = '₽';
export const CURRENCY_CODE = 'RUB';

/**
 * Преобразует рубли в копейки
 */
export function rubToKopecks(rubles: number): number {
  return Math.round(rubles * 100);
}

/**
 * Преобразует копейки в рубли
 */
export function kopecksToRub(kopecks: number): number {
  return kopecks / 100;
}

/**
 * Форматирует копейки в строку с валютой
 */
export function formatMoney(kopecks: number, showCurrency = true): string {
  const rubles = kopecksToRub(kopecks);
  const formatted = new Intl.NumberFormat('ru-RU', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  }).format(Math.abs(rubles));
  
  const sign = kopecks < 0 ? '-' : '';
  const currency = showCurrency ? ` ${CURRENCY_SYMBOL}` : '';
  
  return `${sign}${formatted}${currency}`;
}

/**
 * Парсит строку с деньгами в копейки
 */
export function parseMoney(moneyString: string): number {
  const cleaned = moneyString
    .replace(/[^\d\-,.]/g, '') // Удаляем все кроме цифр, минуса, запятой и точки
    .replace(',', '.'); // Заменяем запятую на точку
  
  const parsed = parseFloat(cleaned);
  return isNaN(parsed) ? 0 : rubToKopecks(parsed);
}

/**
 * Вычисляет процент от суммы
 */
export function calculatePercent(amount: number, percent: number): number {
  return Math.round((amount * percent) / 100);
}

/**
 * Проверяет, является ли сумма положительной
 */
export function isPositive(kopecks: number): boolean {
  return kopecks > 0;
}

/**
 * Проверяет, является ли сумма отрицательной
 */
export function isNegative(kopecks: number): boolean {
  return kopecks < 0;
}

/**
 * Возвращает абсолютное значение суммы
 */
export function absAmount(kopecks: number): number {
  return Math.abs(kopecks);
}

/**
 * Суммирует массив сумм в копейках
 */
export function sumAmounts(amounts: number[]): number {
  return amounts.reduce((sum, amount) => sum + amount, 0);
}

/**
 * Цвета для отображения сумм
 */
export function getAmountColor(kopecks: number): string {
  if (kopecks > 0) return 'text-green-600';
  if (kopecks < 0) return 'text-red-600';
  return 'text-gray-600';
}

/**
 * Получает цвет фона для сумм
 */
export function getAmountBgColor(kopecks: number): string {
  if (kopecks > 0) return 'bg-green-50';
  if (kopecks < 0) return 'bg-red-50';
  return 'bg-gray-50';
}