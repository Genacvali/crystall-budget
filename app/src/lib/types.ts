// TypeScript типы для замены Prisma enum'ов (SQLite не поддерживает enum)

export const AllocationType = {
  FIXED: 'FIXED',
  PERCENT: 'PERCENT',
} as const;
export type AllocationType = keyof typeof AllocationType | 'FIXED' | 'PERCENT';

export const RolloverType = {
  SAME_CATEGORY: 'SAME_CATEGORY',
  TO_RESERVE: 'TO_RESERVE',
  NONE: 'NONE',
} as const;
export type RolloverType = keyof typeof RolloverType | 'SAME_CATEGORY' | 'TO_RESERVE' | 'NONE';

export const Currency = {
  RUB: 'RUB',
} as const;
export type Currency = keyof typeof Currency | 'RUB';

export const MemberRole = {
  OWNER: 'OWNER',
  MEMBER: 'MEMBER',
} as const;
export type MemberRole = keyof typeof MemberRole | 'OWNER' | 'MEMBER';

// Утилиты для валидации
export const isValidAllocationType = (value: string): value is AllocationType => {
  return Object.values(AllocationType).includes(value as AllocationType);
};

export const isValidRolloverType = (value: string): value is RolloverType => {
  return Object.values(RolloverType).includes(value as RolloverType);
};

export const isValidCurrency = (value: string): value is Currency => {
  return Object.values(Currency).includes(value as Currency);
};

export const isValidMemberRole = (value: string): value is MemberRole => {
  return Object.values(MemberRole).includes(value as MemberRole);
};