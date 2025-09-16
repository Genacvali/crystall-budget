# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database (optional - app.py auto-creates DB)
python init_db.py

# Migrate existing database to new schema
python migrate_db.py
```

### Running the Application
```bash
# Development server
python app.py

# Production with Gunicorn
gunicorn -w 2 -b 0.0.0.0:5000 app:app
```

### Production Deployment
```bash
# Deploy to server
./deploy.sh

# Setup HTTPS
./setup-https.sh
```

## Architecture Overview

### Single-File Flask Application
The entire backend is in `app.py` (~3400 lines) with:
- Multi-user authentication with 30-day sessions and secure cookie configuration
- SQLite database with automatic schema initialization and migration system
- Multi-currency support (RUB, USD, EUR, AMD, GEL) with live exchange rates
- PWA support with service worker and offline functionality
- Production-ready logging with rotation (10MB files, 5 backups)
- Avatar upload system with file type validation

### Database Design
SQLite with strict user isolation and automatic schema migration:
- **users**: Authentication, preferences, avatar paths
- **categories**: Budget categories with fixed/percentage limits and rollover logic
- **expenses**: User expense records with multi-currency support
- **income**: Monthly income tracking per user
- **savings_goals**: Goal tracking with progress calculation and notifications
- **shared_budgets**: Family budget collaboration with invitation codes
- **shared_budget_members**: Family budget member relationships and permissions
- **exchange_rates**: Currency exchange rate cache with expiration

### Frontend Structure
- **Templates**: 16 HTML templates using Bootstrap 5 and Russian localization
- **PWA**: Complete Progressive Web App with manifest, service worker, offline support
- **Mobile-first**: Optimized for iOS Safari and Android with swipe gestures
- **Static assets**: PWA files, favicon, service workers in `/static/`

### Key Features
- Fixed and percentage-based budget categories with automatic rollover
- Multi-currency support with automatic exchange rate updates
- Savings goals with progress tracking and completion notifications  
- Family budget sharing via invitation codes
- Comprehensive analytics with charts and period comparison
- Mobile swipe actions for quick edit/delete operations
- Automatic database schema migration system
- Security features: CSP headers, HSTS, secure cookies, password hashing

### Development vs Production Configuration
- **Development**: Insecure default secret key with warning, HTTP cookies
- **Production**: Environment-based secret key, HTTPS-only cookies, enhanced security headers
- **Logging**: Configurable log levels via LOG_LEVEL environment variable
- **Database**: Configurable path via BUDGET_DB environment variable

### Production Files
Essential files for CentOS/RHEL deployment:
- `app.py` - Main Flask application (3381 lines)
- `requirements.txt` - Python dependencies (Flask 3.x, Werkzeug 3.x, requests, gunicorn)
- `templates/` - 16 Jinja2 templates with Russian UI
- `static/` - PWA assets and service workers
- `deploy.sh` - Automated CentOS/RHEL deployment script with systemd setup
- `setup-https.sh` - HTTPS/SSL certificate setup
- `crystalbudget.service` - Systemd service configuration
- `nginx-crystalbudget.conf` - Nginx reverse proxy configuration
- `init_db.py` - Database initialization script
- `migrate_db.py` - Database schema migration utility