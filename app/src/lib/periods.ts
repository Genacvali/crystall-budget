import { Budget, Allocation } from '@prisma/client';
import { startOfMonth, endOfMonth, addMonths, format } from 'date-fns';
import { ru } from 'date-fns/locale';

export function findBudgetForDate(budgets: Budget[], date: Date): Budget | undefined {
  return budgets.find(b => 
    b.periodStart <= date && date < b.nextStart
  );
}

export function getCurrentBudget(budgets: Budget[]): Budget | undefined {
  return findBudgetForDate(budgets, new Date());
}

export function createMonthlyPeriod(date: Date = new Date()): { start: Date; end: Date } {
  const start = startOfMonth(date);
  const end = addMonths(start, 1);
  return { start, end };
}

export function createCustomPeriod(startDate: Date, durationDays: number): { start: Date; end: Date } {
  const start = new Date(startDate);
  const end = new Date(start.getTime() + durationDays * 24 * 60 * 60 * 1000);
  return { start, end };
}

export function formatPeriod(start: Date, end: Date): string {
  const startStr = format(start, 'd MMM', { locale: ru });
  const endStr = format(end, 'd MMM yyyy', { locale: ru });
  return `${startStr} - ${endStr}`;
}

export function getPeriodProgress(start: Date, end: Date): number {
  const now = new Date();
  if (now < start) return 0;
  if (now >= end) return 100;
  
  const total = end.getTime() - start.getTime();
  const elapsed = now.getTime() - start.getTime();
  return Math.round((elapsed / total) * 100);
}

export interface AllocationWithCategory extends Allocation {
  category: {
    id: string;
    name: string;
    icon: string;
    color: string;
  };
}

export function rolloverAllocations(
  prevBudget: Budget & { allocations: AllocationWithCategory[] },
  nextBudget: Budget & { allocations: Allocation[] }
): Allocation[] {
  const newAllocations: Allocation[] = [...nextBudget.allocations];
  
  for (const prevAlloc of prevBudget.allocations) {
    const remainder = Math.max(prevAlloc.planned - prevAlloc.spent, 0);
    if (remainder <= 0) continue;
    
    if (prevAlloc.rollover === 'SAME_CATEGORY') {
      const existingIndex = newAllocations.findIndex(a => a.categoryId === prevAlloc.categoryId);
      
      if (existingIndex >= 0) {
        // Добавляем к существующей аллокации
        newAllocations[existingIndex].planned += remainder;
      } else {
        // Создаём новую аллокацию
        newAllocations.push({
          id: '', // будет сгенерирован при сохранении
          budgetId: nextBudget.id,
          categoryId: prevAlloc.categoryId,
          type: 'FIXED',
          amount: remainder,
          percent: null,
          rollover: 'SAME_CATEGORY',
          planned: remainder,
          spent: 0,
          carryOut: 0,
        });
      }
    } else if (prevAlloc.rollover === 'TO_RESERVE') {
      // Добавляем к общему резерву бюджета
      // Это можно реализовать через специальную категорию "Резерв"
    }
    // NONE - не переносим
  }
  
  return newAllocations;
}

export function recalculatePercentAllocations(
  allocations: Allocation[],
  actualIncome: number
): Allocation[] {
  return allocations.map(allocation => {
    if (allocation.type === 'PERCENT' && allocation.percent !== null) {
      return {
        ...allocation,
        planned: Math.floor(actualIncome * allocation.percent / 100),
      };
    }
    return allocation;
  });
}