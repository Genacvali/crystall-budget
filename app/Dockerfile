# syntax=docker/dockerfile:1.6
FROM node:20-alpine AS base

# Install dependencies only when needed
FROM base AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

ENV NPM_CONFIG_CACHE=/root/.npm \
    PRISMA_SKIP_POSTINSTALL_GENERATE=true

COPY package.json package-lock.json* ./
# Кэшируем npm-кэш вне слоя, сборка быстрее и меньше мусора
RUN --mount=type=cache,target=/root/.npm \
    --mount=type=cache,target=/app/.npm \
    if [ -f package-lock.json ]; then \
      npm ci --no-audit --no-fund --progress=false; \
    else \
      npm install --no-audit --no-fund --progress=false; \
    fi

# Rebuild the source code only when needed
FROM base AS builder
RUN apk add --no-cache libc6-compat openssl
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# теперь есть prisma/schema.prisma
RUN npx prisma generate && npm run build

# Production image, copy all the files and run next
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production
# Disable telemetry during runtime.
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]