# syntax=docker/dockerfile:1.6

# ---------- deps ----------
FROM node:20-alpine AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app
ENV NPM_CONFIG_CACHE=/root/.npm
COPY package.json package-lock.json* ./
RUN --mount=type=cache,target=/root/.npm \
    --mount=type=cache,target=/app/.npm \
    if [ -f package-lock.json ]; then \
      npm ci --no-audit --no-fund --progress=false --ignore-scripts; \
    else \
      npm install --no-audit --no-fund --progress=false --ignore-scripts; \
    fi

# ---------- builder ----------
FROM node:20-alpine AS builder
RUN apk add --no-cache libc6-compat openssl python3 make g++
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# собрать нативный бинарь argon2
RUN npm rebuild argon2 --unsafe-perm --build-from-source || npm rebuild argon2 --unsafe-perm || true
RUN npx prisma generate
RUN npm run build

# ---------- migrator (SQLite) ----------
FROM node:20-alpine AS migrator
RUN apk add --no-cache libc6-compat openssl python3 make g++
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# собрать argon2 и здесь, т.к. тут запускается seed
RUN npm rebuild argon2 --unsafe-perm --build-from-source || npm rebuild argon2 --unsafe-perm || true
ENTRYPOINT ["sh","-lc"]
# применяем миграции к файлу БД и, если есть, сидим
CMD 'npx prisma migrate deploy --schema prisma/schema.prisma && node prisma/seed.js || true'

# ---------- runner ----------
FROM node:20-alpine AS runner
# Устанавливаем OpenSSL 1.1 для совместимости с Prisma
RUN apk add --no-cache openssl1.1-compat libc6-compat
WORKDIR /app
ENV NODE_ENV=production PORT=3000 HOST=0.0.0.0 NODE_OPTIONS=--max-old-space-size=256
# standalone + статика
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
COPY --from=builder /app/prisma ./prisma
# на всякий случай создадим директорию БД
RUN mkdir -p /app/data
EXPOSE 3000
CMD ["node","server.js"]