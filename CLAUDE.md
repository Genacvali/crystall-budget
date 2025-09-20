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

# Development with environment variables
export SECRET_KEY="dev-secret"
export BUDGET_DB="./budget.db"
export LOG_LEVEL="DEBUG"
python app.py
```

### Database Management and Migrations
```bash
# No formal test suite - manual testing via web interface

# Database initialization and testing
python init_db.py

# Database migration (migration scripts not present - database auto-migrates via app.py)
# Run these if specific migration scripts are available:
# python migrate_db.py
# python migrate_telegram_auth.py 
# python migrate_multi_source_categories.py

# Emergency database fixes (production use only)
python emergency_fix.py

# CSRF protection fixes
python fix_csrf.py

# Endpoint security fixes
python fix_endpoints.py
python fix_endpoints_correct.py

# Verify application startup
python app.py
# Then visit http://localhost:5000 to test functionality
```

### Production Deployment
```bash
# Deploy to server (CentOS/RHEL) - script not present, manual deployment required
# ./deploy.sh

# Setup HTTPS with Let's Encrypt
./setup-https.sh

# Admin panel deployment (separate service)
cd admin_panel && ./deploy_admin.sh

# Admin panel management
cd admin_panel && ./start_admin.sh
cd admin_panel && ./stop_admin.sh
cd admin_panel && ./restart_admin.sh
cd admin_panel && ./logs_admin.sh
```

### Service Management
```bash
# Main application service
sudo systemctl start/stop/restart crystalbudget
sudo systemctl status crystalbudget

# Admin panel service  
sudo systemctl start/stop/restart admin-panel

# View logs
sudo journalctl -u crystalbudget -f
sudo journalctl -u admin-panel -f

```

## Directory Structure

```
/opt/crystall-budget/
├── app.py                          # Main Flask application (~3400 lines)
├── requirements.txt                # Python dependencies
├── init_db.py                      # Database initialization script
├── emergency_fix.py                # Emergency database repair script
├── fix_csrf.py                     # CSRF protection fixes
├── fix_endpoints.py               # Endpoint security fixes (v1)
├── fix_endpoints_correct.py       # Endpoint security fixes (v2)
├── setup-https.sh                 # HTTPS setup script
├── crystalbudget.service          # Systemd service configuration
├── nginx-crystalbudget.conf       # Nginx configuration
├── TELEGRAM_AUTH_SETUP.md         # Telegram bot setup guide
├── SECURITY_FIXES_COMPLETED.md    # Security documentation
├── .env.example                   # Environment variables template
├── budget.db                      # SQLite database (created at runtime)
├── templates/                     # Jinja2 templates
├── static/                        # Static assets (CSS, JS, PWA files)
├── admin_panel/                   # Admin interface (separate Flask app)
│   ├── admin_panel.py             # Admin application
│   ├── admin-panel.service        # Admin systemd service
│   ├── deploy_admin.sh            # Admin deployment script
│   ├── start_admin.sh             # Start admin service
│   ├── stop_admin.sh              # Stop admin service
│   ├── restart_admin.sh           # Restart admin service
│   ├── logs_admin.sh              # View admin logs
│   └── templates/                 # Admin templates
└── logs/                          # Application logs directory
```

## Architecture Overview

### Single-File Flask Application
The entire backend is in `app.py` (~3400 lines) with:
- Telegram-only authentication system (email auth disabled)
- 30-day sessions with secure cookie configuration
- SQLite database with automatic schema initialization and migration system
- Multi-currency support (RUB, USD, EUR, AMD, GEL) with live exchange rates
- PWA support with service worker and offline functionality
- Production-ready logging with rotation (10MB files, 5 backups)
- Avatar upload system with file type validation

### Database Design
SQLite with strict user isolation and automatic schema migration:
- **users**: Telegram-only authentication (telegram_id required), preferences, avatar paths
- **categories**: Budget categories with fixed/percentage limits and rollover logic
- **expenses**: User expense records with multi-currency support
- **income**: Monthly income tracking per user
- **savings_goals**: Goal tracking with progress calculation and notifications
- **shared_budgets**: Family budget collaboration with invitation codes
- **shared_budget_members**: Family budget member relationships and permissions
- **exchange_rates**: Currency exchange rate cache with expiration

### Frontend Structure
- **Templates**: HTML templates using Bootstrap 5 and Russian localization
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

### Admin Panel
Separate Flask application in `/admin_panel/` for system administration:
- `admin_panel.py` - Admin interface for user management and system monitoring
- Runs on port 5001 with its own systemd service (`admin-panel.service`)
- User management: view, delete, migrate between auth types, role management
- Data migration tools for converting email users to Telegram authentication
- System stats, database overview, and log viewing capabilities
- Deployment scripts: `deploy_admin.sh`, `start_admin.sh`, `stop_admin.sh`, `restart_admin.sh`


### Environment Variables
```bash
# Required for production
SECRET_KEY="your-secure-secret-key"
HTTPS_MODE="true"  # Enables secure cookies and HSTS headers

# Optional configuration  
BUDGET_DB="/path/to/budget.db"  # Database location (default: ./budget.db)
LOG_LEVEL="INFO"  # Logging level (DEBUG, INFO, WARNING, ERROR)

# Telegram Bot Configuration (see TELEGRAM_AUTH_SETUP.md)
TELEGRAM_BOT_TOKEN="your-bot-token"

# SMTP Configuration (for password recovery - see .env.example)
SMTP_SERVER="smtp-relay.brevo.com"
SMTP_PORT="587"
SMTP_USERNAME="your_brevo_login"
SMTP_PASSWORD="your_brevo_smtp_key"
SMTP_FROM_EMAIL="your_verified_sender@domain.com"
```

### Production Files
Essential files for CentOS/RHEL deployment:
- `app.py` - Main Flask application (~3400 lines)
- `requirements.txt` - Python dependencies (Flask 3.x, Werkzeug 3.x, requests, gunicorn)
- `templates/` - Jinja2 templates with Russian UI and Bootstrap 5
- `static/` - PWA assets, service workers, CSS, JS, and vendor libraries
- `deploy.sh` - Automated CentOS/RHEL deployment script with systemd setup (not present in current codebase)
- `setup-https.sh` - HTTPS/SSL certificate setup with Let's Encrypt
- `crystalbudget.service` - Systemd service configuration
- `nginx-crystalbudget.conf` - Nginx reverse proxy configuration
- `init_db.py` - Database initialization script
- `migrate_db.py` - Database schema migration utility (referenced but not present)
- `migrate_telegram_auth.py` - Migration script for Telegram authentication support (referenced but not present)
- `migrate_multi_source_categories.py` - Special migration for multi-source category support (referenced but not present)
- `emergency_fix.py` - Emergency database repair script for production issues
- `fix_csrf.py` - CSRF protection fixes for security
- `fix_endpoints.py` / `fix_endpoints_correct.py` - Endpoint security fixes
- `TELEGRAM_AUTH_SETUP.md` - Complete setup guide for Telegram authentication
- `SECURITY_FIXES_COMPLETED.md` - Documentation of completed security fixes
- `admin_panel/` - Administrative interface and management tools
- `.env.example` - Environment variable template for SMTP and security config

## Development Workflow

### Making Changes to the Application
1. **Always backup the database before applying fixes**: `cp budget.db budget_backup_$(date +%Y%m%d_%H%M%S).db`
2. **Test changes locally first**: Run `python app.py` and verify functionality at http://localhost:5000
3. **For database schema changes**: Create migration script following the pattern of existing migrate_*.py files
4. **For security fixes**: Document changes in SECURITY_FIXES_COMPLETED.md
5. **Production deployment**: Always test migration scripts on backup data first

### Common Development Tasks
- **Adding new database tables**: Create migration script, update init_db.py for fresh installs
- **Modifying authentication**: Review impact on both email and Telegram auth systems
- **Template changes**: All templates use Russian localization and Bootstrap 5
- **Static asset changes**: Remember PWA manifest and service worker updates for offline support
- **Admin panel changes**: Separate deployment process via admin_panel/ directory