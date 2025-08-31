// server.js
const Fastify = require('fastify');
const cors = require('@fastify/cors');
const helmet = require('@fastify/helmet');
const jwt = require('jsonwebtoken');
const { hash, verify } = require('@node-rs/argon2');
const { Pool } = require('pg');
require('dotenv').config();

const app = Fastify({ logger: true });

// Без CSP (иначе Next иногда ругается), HSTS/прочее пусть делает Caddy
app.register(helmet, { contentSecurityPolicy: false });

// Разрешим CORS c куками/заголовками по умолчанию
app.register(cors, {
  origin: true,
  credentials: true,
  methods: ['GET','POST','PUT','PATCH','DELETE','OPTIONS'],
  allowedHeaders: ['Content-Type','Authorization']
});

const pool = new Pool({ connectionString: process.env.DATABASE_URL });

const JWT_SECRET = process.env.JWT_SECRET || 'change_me_super_secret_32_chars';
const PORT = Number(process.env.PORT || 4000);
const HOST = process.env.HOST || '127.0.0.1';

// ===== Глобальный гард авторизации =====
// Открытые пути: health и всё под /api/auth/*
const openPaths = [/^\/api\/health\b/, /^\/api\/auth\/.*/];

app.addHook('onRequest', async (req, reply) => {
  // Разрешаем preflight-запросы без проверки
  if (req.method === 'OPTIONS') {
    reply.header('Access-Control-Allow-Origin', req.headers.origin || '*');
    reply.header('Access-Control-Allow-Credentials', 'true');
    reply.header('Access-Control-Allow-Methods', 'GET,POST,PUT,PATCH,DELETE,OPTIONS');
    reply.header('Access-Control-Allow-Headers', 'Content-Type, Authorization');
    return reply.code(204).send();
  }

  // Интересуют только /api/*
  if (!req.url.startsWith('/api/')) return;

  // Открытые эндпоинты пропускаем
  if (openPaths.some(rx => rx.test(req.url))) return;

  // Bearer проверка
  const auth = req.headers.authorization || '';
  const token = auth.startsWith('Bearer ') ? auth.slice(7) : '';
  if (!token) {
    return reply.code(401).send({ error: 'unauthorized' });
  }
  try {
    req.user = jwt.verify(token, JWT_SECRET);
  } catch {
    return reply.code(401).send({ error: 'unauthorized' });
  }
});

// ===== Health =====
app.get('/api/health', async () => ({ ok: true, ts: Date.now() }));

// ===== Auth =====
app.post('/api/auth/signup', async (req, reply) => {
  const { email, password } = req.body || {};
  if (!email || !password) return reply.code(400).send({ error: 'bad_input' });
  try {
    const passwordHash = await hash(password);
    await pool.query(
      `INSERT INTO "User"(id,email,"passwordHash") VALUES (gen_random_uuid(), $1, $2)`,
      [email, passwordHash]
    );
    reply.send({ ok: true });
  } catch (e) {
    if (e.code === '23505') return reply.code(409).send({ error: 'exists' });
    req.log.error({ err: e }, 'signup failed');
    reply.code(500).send({ error: 'internal' });
  }
});

app.post('/api/auth/login', async (req, reply) => {
  const { email, password } = req.body || {};
  const { rows } = await pool.query(
    `SELECT id, "passwordHash" FROM "User" WHERE email=$1`,
    [email]
  );
  const user = rows[0];
  if (!user) return reply.code(401).send({ error: 'bad_credentials' });

  const ok = await verify(user.passwordHash, password);
  if (!ok) return reply.code(401).send({ error: 'bad_credentials' });

  const token = jwt.sign({ sub: user.id }, JWT_SECRET, { expiresIn: '7d' });
  reply.send({ token });
});

// ===== 404 для неизвестных маршрутов API =====
app.setNotFoundHandler((req, reply) => {
  if (req.url.startsWith('/api/')) {
    return reply.code(404).send({ error: 'not_found' });
  }
  // Для не-API отдаём простой текст (фронт отдаёт Next / Caddy)
  reply.code(404).type('text/plain').send('Not found');
});

// ===== Глобальный обработчик ошибок =====
app.setErrorHandler((err, req, reply) => {
  req.log.error({ err }, 'unhandled error');
  reply.code(500).send({ error: 'internal' });
});

// ===== Запуск =====
const start = async () => {
  try {
    await app.listen({ host: HOST, port: PORT });
    app.log.info(`API listening on http://${HOST}:${PORT}`);
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
};
start();

// Корректное закрытие пула при остановке
const shutdown = async () => {
  app.log.info('Shutting down...');
  try { await pool.end(); } catch {}
  process.exit(0);
};
process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);