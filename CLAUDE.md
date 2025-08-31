# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

- **Development server**: `npm run dev`
- **Build**: `npm run build`
- **Start production**: `npm start`
- **Lint**: `npm run lint`
- **Database seed**: `npm run seed`
- **Prisma generate**: `npm run prisma:generate` (or `npx prisma generate`)
- **Database migrations**: `npm run prisma:migrate` (or `npx prisma migrate deploy`)

## Production Deployment (CentOS 9)

The application is deployed on CentOS 9 with the following services:
- **PostgreSQL 16** running on localhost:5432
- **Node.js 20 LTS** application on localhost:3000
- **Caddy** reverse proxy with automatic HTTPS via sslip.io

### Application Updates
```bash
cd /opt/crystall
sudo -u crystall git pull
sudo -u crystall npm ci --no-audit --no-fund
sudo -u crystall npx prisma migrate deploy
sudo -u crystall npm run build
sudo systemctl restart crystall
```

### Service Management
- **Application**: `sudo systemctl status crystall`
- **Database**: `sudo systemctl status postgresql-16`
- **Reverse Proxy**: `sudo systemctl status caddy`

## Architecture Overview

CrystallBudget is a PWA budget management application with separated frontend and backend.

### Core Technologies
- **Frontend**: Next.js 14 App Router, TypeScript, Tailwind CSS
- **Backend API**: Fastify with PostgreSQL direct queries
- **Database**: PostgreSQL 16 with UUID primary keys and enums
- **Authentication**: JWT tokens with Argon2 password hashing
- **PWA**: next-pwa with custom caching strategies
- **Deployment**: Systemd services with Caddy reverse proxy

### Key Directory Structure
```
├── app/                 # Next.js 14 App Router pages (no API routes)
├── src/
│   ├── components/      # React components (forms, layout, ui, charts)
│   ├── lib/            # Core utilities (auth, types, API client)
│   └── i18n/           # Internationalization (en, ru)
├── public/             # Static files and PWA manifest
└── deploy-crystall-pg.sh # Deployment script for CentOS 9
```

### Database Schema Architecture

The application uses a multi-tenant household-based structure with PostgreSQL enums:

- **Users** belong to **Households** via **HouseholdMembers** (roles: OWNER/MEMBER)
- **Budgets** have flexible periods and belong to households
- **Categories** are household-scoped with icons and colors
- **Allocations** link budgets to categories with FIXED amounts or PERCENTages
- **Transactions** track income/expenses with category relationships

Key features:
- Dynamic budget allocation based on actual vs planned income
- Rollover rules: SAME_CATEGORY, TO_RESERVE, or NONE
- All monetary values stored as integers in kopecks/cents
- PostgreSQL enums for type safety: AllocationType, RolloverType, MemberRole
- UUID primary keys with pgcrypto extension

### Authentication & Security

- JWT-based authentication via Fastify API
- Passwords hashed with Argon2 (@node-rs/argon2)
- JWT tokens with 7-day expiration
- API endpoints protected by JWT middleware
- Frontend stores JWT in localStorage

### PWA Configuration

- Service worker caching for fonts and images
- Standalone output mode for production deployment
- Custom runtime caching strategies in next.config.js
- Manifest and icons in public/ directory
- HTTPS required for PWA features (handled by Caddy + Let's Encrypt)

### API Design

Fastify backend serves API endpoints with JWT authentication:
- `/api/health` - Health check endpoint
- `/api/auth/signup` - User registration
- `/api/auth/login` - User authentication (returns JWT)
- Frontend communicates with backend via Bearer token authentication

### Development Notes

- Uses `@` path alias for src/ directory
- Separated architecture: Fastify API (port 4000) + Next.js frontend (port 3000)
- Direct PostgreSQL queries in Fastify backend (no Prisma)
- JWT authentication replaces NextAuth.js
- TypeScript strict mode enabled
- PWA disabled in development mode
- Production runs with memory limits: API 300MB, Frontend 256MB
- Supports bilingual interface (Russian/English) via i18n in src/i18n/
- Caddy reverse proxy routes /api/* to Fastify, everything else to Next.js

### Deployment Architecture

- **API Service**: systemd `crystall-api.service` running Fastify on 127.0.0.1:4000
- **Frontend Service**: systemd `crystall.service` running Next.js on 127.0.0.1:3000
- **Database**: PostgreSQL 16 on localhost:5432
- **Reverse Proxy**: Caddy handles HTTPS and routes requests
- **Deploy Script**: `deploy-crystall-pg.sh` sets up the complete stack