# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

- **Development**: `./manage.py dev`
- **Deploy**: `./deploy.py`
- **Start service**: `./manage.py start`
- **Stop service**: `./manage.py stop`
- **Service status**: `./manage.py status`
- **View logs**: `./manage.py logs`

## Architecture Overview

CrystallBudget is a minimal budget management Flask API application.

### Core Technologies
- **Backend API**: Flask with PostgreSQL direct queries
- **Database**: PostgreSQL with UUID primary keys
- **Authentication**: JWT tokens with argon2-cffi password hashing
- **Deployment**: Single systemd service

### Key Directory Structure
```
├── app.py              # Flask API server
├── requirements.txt    # Python dependencies
├── .env.example       # Environment template
├── deploy.py          # Single deployment script
└── manage.py          # Start/stop management script
```

### Authentication & Security

- JWT-based authentication via Flask API
- Passwords hashed with argon2-cffi
- JWT tokens with 7-day expiration
- API endpoints protected by JWT middleware

### API Design

Flask backend serves API endpoints with JWT authentication:
- `/api/health` - Health check endpoint
- `/api/auth/signup` - User registration
- `/api/auth/login` - User authentication (returns JWT)
- `/api/me` - Get current user info (protected route example)

### Development Notes

- API runs on port 4000
- Direct PostgreSQL queries in Flask backend
- Minimal setup without migrations
- Production deployment via single systemd service

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

- **API Service**: systemd `crystall-budget.service` running Flask on 127.0.0.1:4000
- **Database**: PostgreSQL on localhost:5432