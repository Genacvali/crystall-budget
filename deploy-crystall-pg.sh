#!/usr/bin/env bash
set -euo pipefail

DOMAIN="${1:-crystallbudget.161-35-31-38.sslip.io}"   # <- передаём хост в первом аргументе
API_DIR="/opt/crystall-api"
API_USER="crystallapi"
API_PORT="4000"
API_UNIT="crystall-api.service"
FRONT_UNIT="crystall.service"        # уже есть у тебя (Next.js фронт)
CADDYFILE="/etc/caddy/Caddyfile"

echo "==> Using domain: ${DOMAIN}"

# --- 0) sanity ---
command -v psql >/dev/null || { echo "psql not found. Install PostgreSQL client."; exit 1; }
command -v node >/dev/null || { echo "node not found. Install Node.js 20."; exit 1; }
systemctl is-enabled caddy >/dev/null 2>&1 || { echo "Caddy must be installed & enabled."; exit 1; }

# --- 1) создать пользователя/папку API ---
id -u "${API_USER}" >/dev/null 2>&1 || useradd -r -m -s /sbin/nologin "${API_USER}"
mkdir -p "${API_DIR}"
chown -R "${API_USER}:${API_USER}" "${API_DIR}"

# --- 2) .env API (правь креды при необходимости) ---
if [ ! -f "${API_DIR}/.env" ]; then
  cat > "${API_DIR}/.env" <<'ENV'
# --- Crystall API env ---
PORT=4000
HOST=127.0.0.1
JWT_SECRET=change_me_super_secret_32_chars
# тот же URL, что использует фронт
DATABASE_URL=postgresql://crystall:supersecret@127.0.0.1:5432/crystall?schema=public
ENV
  chown "${API_USER}:${API_USER}" "${API_DIR}/.env"
fi

# --- 3) package.json ---
cat > "${API_DIR}/package.json" <<'JSON'
{
  "name": "crystall-api",
  "version": "1.0.0",
  "type": "commonjs",
  "main": "server.js",
  "scripts": {
    "start": "node server.js",
    "dev": "NODE_ENV=development node server.js",
    "db:seed": "node seed.js"
  },
  "dependencies": {
    "@node-rs/argon2": "^1.9.0",
    "dotenv": "^16.4.5",
    "fastify": "^4.28.1",
    "fastify-cors": "^8.4.2",
    "fastify-helmet": "^12.1.1",
    "jsonwebtoken": "^9.0.2",
    "pg": "^8.12.0",
    "zod": "^3.23.8"
  }
}
JSON
chown "${API_USER}:${API_USER}" "${API_DIR}/package.json"

# --- 4) server.js (минимальный API: health, signup, login) ---
cat > "${API_DIR}/server.js" <<'JS'
const Fastify = require('fastify');
const helmet = require('fastify-helmet');
const cors = require('fastify-cors');
const jwt = require('jsonwebtoken');
const { hash, verify } = require('@node-rs/argon2');
const { Pool } = require('pg');
require('dotenv').config();

const app = Fastify({ logger: true });
app.register(helmet, { contentSecurityPolicy: false });
app.register(cors, { origin: true, credentials: true });

const pool = new Pool({ connectionString: process.env.DATABASE_URL });
const JWT_SECRET = process.env.JWT_SECRET || 'change_me';
const PORT = process.env.PORT || 4000;
const HOST = process.env.HOST || '127.0.0.1';

// Guard
app.addHook('onRequest', async (req, reply) => {
  if (req.url.startsWith('/api/') && !req.url.startsWith('/api/auth/')) {
    const auth = req.headers.authorization || '';
    const token = auth.startsWith('Bearer ') ? auth.slice(7) : '';
    try { req.user = jwt.verify(token, JWT_SECRET); }
    catch { return reply.code(401).send({ error: 'unauthorized' }); }
  }
});

app.get('/api/health', async () => ({ ok: true, ts: Date.now() }));

app.post('/api/auth/signup', async (req, reply) => {
  const { email, password } = req.body || {};
  if (!email || !password) return reply.code(400).send({ error: 'bad_input' });
  const h = await hash(password);
  try {
    await pool.query(`INSERT INTO "User"(id,email,"passwordHash") VALUES (gen_random_uuid(), $1, $2)`, [email, h]);
    reply.send({ ok: true });
  } catch (e) {
    if (e.code === '23505') return reply.code(409).send({ error: 'exists' });
    req.log.error(e);
    reply.code(500).send({ error: 'internal' });
  }
});

app.post('/api/auth/login', async (req, reply) => {
  const { email, password } = req.body || {};
  const { rows } = await pool.query(`SELECT id, "passwordHash" FROM "User" WHERE email=$1`, [email]);
  const user = rows[0];
  if (!user) return reply.code(401).send({ error: 'bad_credentials' });
  const ok = await verify(user.passwordHash, password);
  if (!ok) return reply.code(401).send({ error: 'bad_credentials' });
  const token = jwt.sign({ sub: user.id }, JWT_SECRET, { expiresIn: '7d' });
  reply.send({ token });
});

// TODO: добавишь CRUD для budgets/categories/transactions позже

app.listen({ host: HOST, port: PORT }).then(() => {
  app.log.info(`API listening on http://${HOST}:${PORT}`);
}).catch(err => {
  app.log.error(err);
  process.exit(1);
});
JS
chown "${API_USER}:${API_USER}" "${API_DIR}/server.js"

# --- 5) SQL-схема (ENUMы + таблицы) ---
cat > "${API_DIR}/schema.sql" <<'SQL'
-- расширение для UUID
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ENUMs
DO $ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'allocationtype') THEN
    CREATE TYPE AllocationType AS ENUM ('FIXED','PERCENT');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'rollovertype') THEN
    CREATE TYPE RolloverType AS ENUM ('SAME_CATEGORY','TO_RESERVE','NONE');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'memberrole') THEN
    CREATE TYPE MemberRole AS ENUM ('OWNER','MEMBER');
  END IF;
END $;

-- Tables
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
SQL
chown "${API_USER}:${API_USER}" "${API_DIR}/schema.sql"

# --- 6) seed (опционально: демо-акк) ---
cat > "${API_DIR}/seed.js" <<'JS'
const { Pool } = require('pg');
const { hash } = require('@node-rs/argon2');
require('dotenv').config();

(async () => {
  const pool = new Pool({ connectionString: process.env.DATABASE_URL });
  const email = 'demo@crystall.local';
  const password = 'demo1234';
  const h = await hash(password);
  await pool.query(`INSERT INTO "User"(id,email,"passwordHash") VALUES (gen_random_uuid(), $1, $2) ON CONFLICT (email) DO NOTHING`, [email, h]);
  console.log('Seed done (user: demo@crystall.local / demo1234)');
  await pool.end();
})();
JS
chown "${API_USER}:${API_USER}" "${API_DIR}/seed.js"

# --- 7) Установка зависимостей ---
su -s /bin/bash -c "cd '${API_DIR}' && npm install --no-audit --no-fund" "${API_USER}"

# --- 8) Применить схему и seed в БД ---
source "${API_DIR}/.env"
psql "${DATABASE_URL%?schema=public}" -c 'SELECT 1;' >/dev/null
psql "$DATABASE_URL" -f "${API_DIR}/schema.sql"
su -s /bin/bash -c "cd '${API_DIR}' && npm run db:seed" "${API_USER}"

# --- 9) systemd unit для API ---
cat > "/etc/systemd/system/${API_UNIT}" <<UNIT
[Unit]
Description=CrystallBudget API (Fastify + PostgreSQL)
After=network-online.target postgresql-16.service
Wants=network-online.target

[Service]
User=${API_USER}
Group=${API_USER}
WorkingDirectory=${API_DIR}
EnvironmentFile=${API_DIR}/.env
ExecStart=/usr/bin/node ${API_DIR}/server.js
Restart=always
RestartSec=5
MemoryMax=300M
NoNewPrivileges=yes

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now "${API_UNIT}"

# --- 10) Обновить Caddy: /api -> API, остальное -> фронт ---
# Сначала сохраним бэкап
cp -an "${CADDYFILE}" "${CADDYFILE}.bak.$(date +%F_%H%M%S)"

cat > "${CADDYFILE}" <<CADDY
# редирект с голого IP/старых имён на основной домен
:80, :443 {
  redir https://${DOMAIN}{uri} permanent
}

# основной сайт
${DOMAIN} {
  encode zstd gzip

  @api path /api/*
  reverse_proxy @api 127.0.0.1:${API_PORT}

  # фронтенд Next (у тебя уже работает на 3000 через crystall.service)
  reverse_proxy 127.0.0.1:3000

  header {
    Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
    X-Content-Type-Options "nosniff"
    Referrer-Policy "strict-origin-when-cross-origin"
  }
}
CADDY

systemctl reload caddy

# --- 11) Отключить и удалить «старое», если было (Docker или старый API) ---
# (не трогаем фронтенд crystall.service)
systemctl disable --now crystall-api-docker 2>/dev/null || true
docker rm -f crystall-budget-app 2>/dev/null || true
docker system prune -af 2>/dev/null || true

echo "==> Done. Check:"
echo "   systemctl status ${API_UNIT} --no-pager -l"
echo "   curl -s https://${DOMAIN}/api/health | jq ."