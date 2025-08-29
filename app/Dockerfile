# syntax=docker/dockerfile:1.6

############################################
# deps: ставим node_modules без postinstall
############################################
FROM node:20-alpine AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

# ВАЖНО: отключаем prisma generate на стадии deps
ENV PRISMA_SKIP_POSTINSTALL_GENERATE=true \
    NPM_CONFIG_CACHE=/root/.npm

COPY package.json package-lock.json* ./

# Кэшируем npm кэш, чтобы слои были меньше и сборки быстрее
RUN --mount=type=cache,target=/root/.npm \
    --mount=type=cache,target=/app/.npm \
    if [ -f package-lock.json ]; then \
      npm ci --no-audit --no-fund --progress=false; \
    else \
      npm install --no-audit --no-fund --progress=false; \
    fi

############################################
# builder: тут уже есть prisma/, генерим клиент и билдим app
############################################
FROM node:20-alpine AS builder
# Для prisma на Alpine нужны эти пакеты
RUN apk add --no-cache libc6-compat openssl
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Теперь у нас есть prisma/schema.prisma → можно генерировать
RUN npx prisma generate
RUN npm run build

############################################
# runner: лёгкий рантайм без dev-зависимостей
############################################
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    PORT=3000

# Если ты используешь Next.js standalone-вывод:
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000
CMD ["node", "server.js"]