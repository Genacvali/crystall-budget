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

# Database auto-migrates on app startup - no separate migration needed
```

### Running the Application
```bash
# Development server
python app.py

# Production with Gunicorn
gunicorn -w 2 -b 0.0.0.0:5000 app:app
```

### Testing and Code Quality
```bash
# No formal test suite - manual testing via web interface
# Test database initialization
python init_db.py

# Emergency database fixes (production)
python emergency_fix.py

# Set up Telegram authentication (see TELEGRAM_AUTH_SETUP.md)
export TELEGRAM_BOT_TOKEN="your-bot-token"

# Verify application startup
python app.py
# Then visit http://localhost:5000 to test functionality

# Check for syntax errors and basic linting
python -m py_compile app.py
python -m py_compile admin_panel/admin_panel.py
```

### Production Deployment
```bash
# Admin panel deployment (separate service)
cd admin_panel && ./deploy_admin.sh

# Note: Main app deployment scripts not present in current codebase
# Manual deployment requires:
# 1. Set up systemd service (crystalbudget.service)
# 2. Configure nginx reverse proxy
# 3. Set production environment variables
# 4. Use gunicorn for WSGI serving
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

## Architecture Overview

### Single-File Flask Application
The entire backend is in `app.py` (~4737 lines) with:
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
- **Templates**: 18+ HTML templates using Bootstrap 5 and Russian localization
- **Components**: Reusable template components in `/templates/components/`
- **PWA**: Complete Progressive Web App with manifest, service worker, offline support
- **Mobile-first**: Optimized for iOS Safari and Android with swipe gestures
- **Static assets**: 
  - PWA files (manifest.json, manifest.webmanifest)
  - Service worker (sw.js) for offline functionality
  - JavaScript modules in `/static/js/` with modular entry points:
    - `app.js` - Main application logic
    - `dashboard-cats.js` - Dashboard category management
    - `progress_bars.js` - Progress bar animations
    - `offline.js` - Offline functionality
    - `entries/` - Page-specific entry points (dashboard.entry.js, expenses.entry.js)
    - `modules/` - Reusable modules (ui.js, forms.js, swipe.js)
  - CSS files in `/static/css/` with responsive themes
  - Favicon and icons in `/static/icons/`
  - User avatars stored in `/static/avatars/`

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
- Deployment scripts: `deploy_admin.sh`, `start_admin.sh`, `stop_admin.sh`, `restart_admin.sh`, `logs_admin.sh`


### Environment Variables
```bash
# Required for production
SECRET_KEY="your-secure-secret-key"
HTTPS_MODE="true"  # Enables secure cookies and HSTS headers
TELEGRAM_BOT_TOKEN="your-telegram-bot-token"  # Required for Telegram authentication

# Optional configuration  
BUDGET_DB="/path/to/budget.db"  # Database location (default: ./budget.db)
LOG_LEVEL="INFO"  # Logging level (DEBUG, INFO, WARNING, ERROR)

```

### Important File Locations
Current codebase structure:
- `app.py` - Main Flask application (~4737 lines) with embedded Telegram authentication
- `requirements.txt` - Python dependencies (Flask 3.x, Werkzeug 3.x, requests, gunicorn, python-dotenv)
- `templates/` - Jinja2 templates with Russian UI, including reusable components
- `static/` - Frontend assets:
  - PWA manifests and service worker
  - CSS themes and dashboard styles 
  - JavaScript modules for dashboard and progress bars
  - User avatars and app icons
- `init_db.py` - Database initialization script
- `admin_panel/` - Administrative interface with deployment scripts:
  - `admin_panel.py` - Admin Flask app
  - `deploy_admin.sh`, `start_admin.sh`, `stop_admin.sh`, `restart_admin.sh`, `logs_admin.sh`
  - `admin-panel.service` - Admin systemd service
  - `nginx-admin-panel.conf` - Admin nginx config
- `README.md` - Russian documentation with v1.1 features and setup instructions

### Missing Deployment Files
These files are referenced but not present in current codebase:
- `deploy.sh` - Main app deployment script
- `setup-https.sh` - HTTPS/SSL setup script  
- `crystalbudget.service` - Main app systemd service
- `nginx-crystalbudget.conf` - Main app nginx config
- `emergency_fix.py` - Database repair script
- `TELEGRAM_AUTH_SETUP.md` - Telegram setup guide