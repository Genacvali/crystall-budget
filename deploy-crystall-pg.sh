#!/usr/bin/env bash
set -euo pipefail

DOMAIN="${1:-crystallbudget.161-35-31-38.sslip.io}"
API_DIR="/opt/crystall-api"
API_USER="crystallapi"
API_PORT="4000"
API_UNIT="crystall-api.service"
CADDYFILE="/etc/caddy/Caddyfile"

echo "==> Using domain: ${DOMAIN}"

# Проверки
command -v psql >/dev/null || { echo "psql not found"; exit 1; }
command -v node >/dev/null || { echo "node not found"; exit 1; }
systemctl is-enabled caddy >/dev/null 2>&1 || { echo "caddy not enabled"; exit 1; }

# Создать пользователя и директорию
id -u "${API_USER}" >/dev/null 2>&1 || useradd -r -m -s /sbin/nologin "${API_USER}"
rm -rf "${API_DIR}"
mkdir -p "${API_DIR}"
chown -R "${API_USER}:${API_USER}" "${API_DIR}"

# .env
cat > "${API_DIR}/.env" <<'ENV'
PORT=4000
HOST=127.0.0.1
JWT_SECRET=change_me_super_secret_32_chars_long_key
DATABASE_URL=postgresql://crystall:supersecret@127.0.0.1:5432/crystall?schema=public
ENV

# package.json
cat > "${API_DIR}/package.json" <<'JSON'
{
  "name": "crystall-api",
  "version": "1.0.0",
  "main": "server.js",
  "scripts": {
    "start": "node server.js",
    "seed": "node seed.js"
  },
  "dependencies": {
    "bcrypt": "5.1.1",
    "dotenv": "16.4.5",
    "fastify": "4.28.1",
    "jsonwebtoken": "9.0.2",
    "pg": "8.12.0"
  }
}
JSON

# server.js
cat > "${API_DIR}/server.js" <<'JS'
const Fastify = require('fastify');
const jwt = require('jsonwebtoken');
const bcrypt = require('bcrypt');
const { Pool } = require('pg');
require('dotenv').config();

const app = Fastify({ logger: true });
app.register(require('@fastify/cors'), { origin: true });

const pool = new Pool({ connectionString: process.env.DATABASE_URL });
const JWT_SECRET = process.env.JWT_SECRET;
const PORT = process.env.PORT || 4000;
const HOST = process.env.HOST || '127.0.0.1';

// Auth guard
app.addHook('onRequest', async (req, reply) => {
  if (req.url.startsWith('/api/') && !req.url.startsWith('/api/auth/') && !req.url.startsWith('/api/health')) {
    const auth = req.headers.authorization || '';
    const token = auth.startsWith('Bearer ') ? auth.slice(7) : '';
    try { 
      req.user = jwt.verify(token, JWT_SECRET); 
    } catch { 
      return reply.code(401).send({ error: 'unauthorized' }); 
    }
  }
});

app.get('/api/health', async () => ({ ok: true, ts: Date.now() }));

app.post('/api/auth/signup', async (req, reply) => {
  const { email, password } = req.body || {};
  if (!email || !password) return reply.code(400).send({ error: 'bad_input' });
  
  const passwordHash = await bcrypt.hash(password, 10);
  try {
    await pool.query(`INSERT INTO "User"(id,email,"passwordHash") VALUES (gen_random_uuid(), $1, $2)`, [email, passwordHash]);
    reply.send({ ok: true });
  } catch (e) {
    if (e.code === '23505') return reply.code(409).send({ error: 'exists' });
    reply.code(500).send({ error: 'internal' });
  }
});

app.post('/api/auth/login', async (req, reply) => {
  const { email, password } = req.body || {};
  const { rows } = await pool.query(`SELECT id, "passwordHash" FROM "User" WHERE email=$1`, [email]);
  const user = rows[0];
  if (!user || !await bcrypt.compare(password, user.passwordHash)) {
    return reply.code(401).send({ error: 'bad_credentials' });
  }
  const token = jwt.sign({ sub: user.id }, JWT_SECRET, { expiresIn: '7d' });
  reply.send({ token });
});

app.listen({ host: HOST, port: PORT });
JS

# schema.sql
cat > "${API_DIR}/schema.sql" <<'SQL'
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
SQL

# seed.js
cat > "${API_DIR}/seed.js" <<'JS'
const { Pool } = require('pg');
const bcrypt = require('bcrypt');
require('dotenv').config();

(async () => {
  const pool = new Pool({ connectionString: process.env.DATABASE_URL });
  const passwordHash = await bcrypt.hash('demo1234', 10);
  await pool.query(`INSERT INTO "User"(id,email,"passwordHash") VALUES (gen_random_uuid(), $1, $2) ON CONFLICT (email) DO NOTHING`, ['demo@crystall.local', passwordHash]);
  console.log('Demo user created: demo@crystall.local / demo1234');
  await pool.end();
})();
JS

chown -R "${API_USER}:${API_USER}" "${API_DIR}"

# Установить зависимости
cd "${API_DIR}"
su -s /bin/bash -c "npm install --no-audit --no-fund" "${API_USER}"

# Применить схему
source "${API_DIR}/.env"
psql "$DATABASE_URL" -f "${API_DIR}/schema.sql"
su -s /bin/bash -c "npm run seed" "${API_USER}"

# systemd service
cat > "/etc/systemd/system/${API_UNIT}" <<UNIT
[Unit]
Description=Crystall API
After=network.target postgresql-16.service

[Service]
User=${API_USER}
WorkingDirectory=${API_DIR}
EnvironmentFile=${API_DIR}/.env
ExecStart=/usr/bin/node server.js
Restart=always
MemoryMax=300M

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now "${API_UNIT}"

# Обновить Caddy
cp "${CADDYFILE}" "${CADDYFILE}.bak"
cat > "${CADDYFILE}" <<CADDY
${DOMAIN} {
  @api path /api/*
  reverse_proxy @api 127.0.0.1:${API_PORT}
  reverse_proxy 127.0.0.1:3000
}
CADDY

systemctl reload caddy

echo "==> Done. Check: curl https://${DOMAIN}/api/health"