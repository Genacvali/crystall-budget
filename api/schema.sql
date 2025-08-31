CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'allocationtype') THEN
    CREATE TYPE AllocationType AS ENUM ('FIXED','PERCENT');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'rollovertype') THEN
    CREATE TYPE RolloverType AS ENUM ('SAME_CATEGORY','TO_RESERVE','NONE');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'memberrole') THEN
    CREATE TYPE MemberRole AS ENUM ('OWNER','MEMBER');
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS "User" (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  "passwordHash" TEXT NOT NULL,
  "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS "Household" (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS "HouseholdMember" (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  "householdId" UUID NOT NULL REFERENCES "Household"(id) ON DELETE CASCADE,
  "userId" UUID NOT NULL REFERENCES "User"(id) ON DELETE CASCADE,
  role MemberRole NOT NULL DEFAULT 'MEMBER',
  "joinedAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE("householdId","userId")
);

CREATE TABLE IF NOT EXISTS "Budget" (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  "householdId" UUID NOT NULL REFERENCES "Household"(id) ON DELETE CASCADE,
  "periodStart" DATE NOT NULL,
  "nextStart" DATE NOT NULL,
  "incomePlanned" INTEGER NOT NULL DEFAULT 0,
  "incomeActual" INTEGER NOT NULL DEFAULT 0,
  "carryIn" INTEGER NOT NULL DEFAULT 0,
  "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE("householdId","periodStart")
);

CREATE TABLE IF NOT EXISTS "Category" (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  "householdId" UUID NOT NULL REFERENCES "Household"(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  icon TEXT,
  "isHidden" BOOLEAN NOT NULL DEFAULT FALSE,
  UNIQUE("householdId", name)
);

CREATE TABLE IF NOT EXISTS "Allocation" (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  "budgetId" UUID NOT NULL REFERENCES "Budget"(id) ON DELETE CASCADE,
  "categoryId" UUID NOT NULL REFERENCES "Category"(id) ON DELETE RESTRICT,
  type AllocationType NOT NULL,
  amount INTEGER,
  percent DOUBLE PRECISION,
  rollover RolloverType NOT NULL DEFAULT 'SAME_CATEGORY',
  planned INTEGER NOT NULL DEFAULT 0,
  spent INTEGER NOT NULL DEFAULT 0,
  "carryOut" INTEGER NOT NULL DEFAULT 0,
  UNIQUE("budgetId","categoryId")
);

CREATE TABLE IF NOT EXISTS "Transaction" (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  "householdId" UUID NOT NULL REFERENCES "Household"(id) ON DELETE CASCADE,
  "userId" UUID REFERENCES "User"(id) ON DELETE SET NULL,
  "categoryId" UUID REFERENCES "Category"(id) ON DELETE SET NULL,
  "budgetId" UUID REFERENCES "Budget"(id) ON DELETE SET NULL,
  amount INTEGER NOT NULL,
  "occurredAt" TIMESTAMPTZ NOT NULL,
  note TEXT,
  "isPending" BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS "Transaction_household_occurred_idx" ON "Transaction"("householdId","occurredAt");