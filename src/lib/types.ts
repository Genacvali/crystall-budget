import type { AllocationType, RolloverType, Currency, MemberRole } from '@prisma/client';

export type { AllocationType, RolloverType, Currency, MemberRole };

export interface User {
  id: string;
  email: string;
  createdAt: Date;
}

export interface Household {
  id: string;
  name: string;
  createdAt: Date;
}

export interface HouseholdMember {
  id: string;
  householdId: string;
  userId: string;
  role: MemberRole;
  joinedAt: Date;
}

export interface Budget {
  id: string;
  householdId: string;
  periodStart: Date;
  nextStart: Date;
  incomePlanned: number;
  incomeActual: number;
  carryIn: number;
  createdAt: Date;
}

export interface Category {
  id: string;
  householdId: string;
  name: string;
  icon?: string;
  isHidden: boolean;
}

export interface Allocation {
  id: string;
  budgetId: string;
  categoryId: string;
  type: AllocationType;
  amount?: number;
  percent?: number;
  rollover: RolloverType;
  planned: number;
  spent: number;
  carryOut: number;
}

export interface Transaction {
  id: string;
  householdId: string;
  userId?: string;
  categoryId?: string;
  budgetId?: string;
  amount: number;
  occurredAt: Date;
  note?: string;
  isPending: boolean;
}

// Utility types for API responses
export interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };
}

// Form types
export interface SignUpFormData {
  email: string;
  password: string;
  confirmPassword: string;
  householdName: string;
}

export interface SignInFormData {
  email: string;
  password: string;
}