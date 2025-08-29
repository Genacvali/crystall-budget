# syntax=docker/dockerfile:1.6

FROM node:20-alpine AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

ENV NPM_CONFIG_CACHE=/root/.npm

COPY package.json package-lock.json* ./

# ВАЖНО: игнорируем ВСЕ скрипты (включая твой "postinstall")
RUN --mount=type=cache,target=/root/.npm \
    --mount=type=cache,target=/app/.npm \
    if [ -f package-lock.json ]; then \
      npm ci --no-audit --no-fund --progress=false --ignore-scripts; \
    else \
      npm install --no-audit --no-fund --progress=false --ignore-scripts; \
    fi

FROM node:20-alpine AS builder
# Prisma на Alpine требует openssl
RUN apk add --no-cache libc6-compat openssl
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Теперь schema есть — вручную генерим клиент и билдим
RUN npx prisma generate
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production PORT=3000
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]