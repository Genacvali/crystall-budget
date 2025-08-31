# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

- **Development server**: `npm run dev`
- **Build**: `npm run build`
- **Start production**: `npm start`
- **Lint**: `npm run lint`
- **Database seed**: `npm run seed`
- **Prisma generate**: `npx prisma generate`
- **Database migrations**: `npx prisma migrate deploy`

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

CrystallBudget is a PWA budget management application built with Next.js 14 and Prisma.

### Core Technologies
- **Frontend**: Next.js 14 App Router, TypeScript, Tailwind CSS
- **Database**: PostgreSQL 16 with Prisma ORM
- **Authentication**: NextAuth.js with Argon2 password hashing
- **PWA**: next-pwa with custom caching strategies
- **Deployment**: Systemd services with Caddy reverse proxy

### Key Directory Structure
```
├── app/                 # Next.js 14 App Router pages and API routes
├── src/
│   ├── components/      # React components (forms, layout, ui, charts)
│   ├── lib/            # Core utilities (auth, db, security, types)
│   └── i18n/           # Internationalization (en, ru)
├── prisma/             # Database schema and migrations
└── public/             # Static files and PWA manifest
```

### Database Schema Architecture

The application uses a multi-tenant household-based structure with PostgreSQL enums:

- **Users** belong to **Households** via **HouseholdMembers** (roles: OWNER/MEMBER)
- **Budgets** have flexible periods and belong to households
- **Categories** are household-scoped with icons and colors
- **Allocations** link budgets to categories with FIXED amounts or PERCENTages
- **Transactions** track income/expenses with account and category relationships
- **Accounts** store balance information per household

Key features:
- Dynamic budget allocation based on actual vs planned income
- Rollover rules: SAME_CATEGORY, TO_RESERVE, or NONE
- All monetary values stored as integers in kopecks/cents
- PostgreSQL enums for type safety: AllocationType, RolloverType, Currency, MemberRole

### Authentication & Security

- NextAuth.js with custom credentials provider
- Passwords hashed with Argon2 (@node-rs/argon2)
- JWT sessions with 30-day expiration
- Protected routes via middleware (src/middleware.ts)
- Custom session types include household membership

### PWA Configuration

- Service worker caching for fonts and images
- Standalone output mode for production deployment
- Custom runtime caching strategies in next.config.js
- Manifest and icons in public/ directory
- HTTPS required for PWA features (handled by Caddy + Let's Encrypt)

### API Design

API routes follow RESTful patterns:
- `/api/users` - User registration
- `/api/budgets` - Budget CRUD operations  
- `/api/categories` - Category management
- `/api/transactions` - Transaction creation
- `/api/households` - Household management

### Development Notes

- Uses `@` path alias for src/ directory
- Argon2 configured as external package for server components
- Prisma client singleton pattern in lib/db.ts
- TypeScript strict mode enabled
- PWA disabled in development mode
- Production runs with memory limits: Node.js 256MB, systemd MemoryMax=600M