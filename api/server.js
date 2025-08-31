const Fastify = require('fastify');
const cors = require('@fastify/cors');
const helmet = require('@fastify/helmet');
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

// guard на /api/* кроме /api/auth/* и /api/health
app.addHook('onRequest', async (req, reply) => {
  if (req.url.startsWith('/api/') && !req.url.startsWith('/api/auth/') && !req.url.startsWith('/api/health')) {
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
  const passwordHash = await hash(password);
  try {
    await pool.query(`INSERT INTO "User"(id,email,"passwordHash") VALUES (gen_random_uuid(), $1, $2)`, [email, passwordHash]);
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

app.listen({ host: HOST, port: PORT }).then(() => {
  app.log.info(`API listening on http://${HOST}:${PORT}`);
}).catch(err => {
  app.log.error(err);
  process.exit(1);
});