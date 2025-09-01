# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

- **API start**: `cd api && npm start`
- **Web development**: `cd web && npm run dev`
- **Web build**: `cd web && npm run build`
- **Web start**: `cd web && npm start`

## Architecture Overview

CrystallBudget is a minimal budget management application with separated API and web frontend.

### Core Technologies
- **Backend API**: Fastify with PostgreSQL direct queries
- **Frontend**: Next.js 14 App Router, TypeScript
- **Database**: PostgreSQL with UUID primary keys
- **Authentication**: JWT tokens with @node-rs/argon2 password hashing
- **Deployment**: Systemd services with Caddy reverse proxy

### Key Directory Structure
```
├── api/
│   ├── server.js        # Fastify API server
│   ├── package.json     # API dependencies
│   └── .env.example     # Environment template
├── web/
│   ├── app/             # Next.js 14 App Router pages
│   ├── lib/            # API client utilities
│   ├── package.json     # Web dependencies
│   └── next.config.js   # Next.js configuration
├── Caddyfile            # Reverse proxy configuration
├── crystall-api.service # API systemd service
└── crystall-web.service # Web systemd service
```

### Authentication & Security

- JWT-based authentication via Fastify API
- Passwords hashed with @node-rs/argon2
- JWT tokens with 7-day expiration
- API endpoints protected by JWT middleware
- Frontend stores JWT in localStorage

### API Design

Fastify backend serves API endpoints with JWT authentication:
- `/api/health` - Health check endpoint
- `/api/auth/signup` - User registration
- `/api/auth/login` - User authentication (returns JWT)
- `/api/me` - Get current user info (protected route example)

### Development Notes

- API runs on port 4000, Web on port 3000
- Uses `@/lib/api` path alias for web API client
- Direct PostgreSQL queries in Fastify backend
- Minimal setup without migrations
- Production deployment via systemd services
- Caddy reverse proxy routes /api/* to Fastify, everything else to Next.js

### Database Setup

Manual table creation required (no migrations):
```sql
create extension if not exists pgcrypto;
create table if not exists "User"(
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  "passwordHash" text not null
);
```

### Deployment Architecture

- **API Service**: systemd `crystall-api.service` running Fastify on 127.0.0.1:4000
- **Web Service**: systemd `crystall-web.service` running Next.js on 127.0.0.1:3000
- **Database**: PostgreSQL on localhost:5432
- **Reverse Proxy**: Caddy handles HTTPS and routes requests