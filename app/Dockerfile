# syntax=docker/dockerfile:1.6

# ---------- deps ----------
FROM node:20-slim AS deps
WORKDIR /app
ENV NODE_ENV=production NPM_CONFIG_CACHE=/root/.npm
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*
COPY package.json package-lock.json* ./
RUN --mount=type=cache,target=/root/.npm \
    if [ -f package-lock.json ]; then \
      npm ci --no-audit --no-fund --progress=false --ignore-scripts; \
    else \
      npm install --no-audit --no-fund --progress=false --ignore-scripts; \
    fi

# ---------- builder ----------
FROM node:20-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npx prisma generate
RUN npm run build

# ---------- migrator (SQLite) ----------
FROM node:20-slim AS migrator
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENTRYPOINT ["sh","-lc"]
# применяем миграции к файлу БД и, если есть, сидим
CMD 'npx prisma migrate deploy --schema prisma/schema.prisma && node prisma/seed.js || true'

# ---------- runner ----------
FROM node:20-slim AS runner
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