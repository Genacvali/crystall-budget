# syntax=docker/dockerfile:1.6

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
# Добавляем тулчейн для сборки нативных модулей
RUN apk add --no-cache libc6-compat openssl python3 make g++
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Сборка бинари для argon2 (после копирования исходников)
RUN npm rebuild argon2 --unsafe-perm --build-from-source || npm rebuild argon2 --unsafe-perm || true

RUN npx prisma generate
RUN npm run build

# ---------- migrator ----------
FROM node:20-alpine AS migrator
RUN apk add --no-cache libc6-compat openssl python3 make g++
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Соберём бинари argon2 и здесь тоже, т.к. здесь запускается seed
RUN npm rebuild argon2 --unsafe-perm --build-from-source || npm rebuild argon2 --unsafe-perm || true

ENTRYPOINT ["npx","prisma"]
CMD ["migrate","deploy","--schema","prisma/schema.prisma"]

# ---------- runner ----------
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    PORT=3000 \
    HOST=0.0.0.0 \
    NODE_OPTIONS=--max-old-space-size=256
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
COPY --from=builder /app/prisma ./prisma
EXPOSE 3000
CMD ["node","server.js"]