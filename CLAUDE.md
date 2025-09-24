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

# Initialize database with migrations
flask db upgrade

# Generate new migration (when models change)
flask db migrate -m "Description of changes"
```

### Running the Application
```bash
# Development server (default port 5000)
python app.py

# Production with Gunicorn
gunicorn -w 2 -b 0.0.0.0:5000 app:app

# Admin panel (runs on port 5001)
cd admin_panel && python admin_panel.py
```

### Database Management
```bash
# Create new migration
flask db migrate -m "Description"

# Apply migrations
flask db upgrade

# Downgrade migration
flask db downgrade

# View migration history
flask db history

# Check current migration
flask db current
```

### Testing and Code Quality
```bash
# No formal test suite - manual testing via web interface
# Verify application startup
python app.py
# Then visit http://localhost:5000 to test functionality

# Check for syntax errors and basic linting
python -m py_compile app.py
python -c "import py_compile; py_compile.compile('app.py', doraise=True)"

# Check all Python files in app module
find app/ -name "*.py" -exec python -m py_compile {} \;
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

### Modular Flask Application
The application uses Flask application factory pattern with modular blueprints:
- **Application Factory**: `app/__init__.py` - Creates and configures Flask app instance
- **Modular Structure**: Organized into blueprints (`auth`, `budget`, `goals`, `api`)
- **Database**: Flask-SQLAlchemy with Alembic migrations
- **Authentication**: Flask-Login with Telegram-based auth system  
- **Caching**: Flask-Caching with configurable backends
- **Extensions**: Centralized extension management in `app/core/extensions.py`
- **Configuration**: Environment-based config classes in `app/core/config.py`

### Module Structure
The application is organized into focused modules:

#### Core (`app/core/`)
- **config.py**: Environment-based configuration classes (Development/Production/Testing)
- **extensions.py**: Flask extension initialization (SQLAlchemy, Login Manager, etc.)
- **errors.py**: Centralized error handling and custom error pages
- **events.py**: Application event handlers and lifecycle management
- **filters.py**: Custom Jinja2 template filters
- **cli.py**: Flask CLI commands for database management
- **caching.py**: Cache management utilities
- **money.py**: Currency handling and exchange rate utilities
- **time.py**: Time zone and datetime utilities

#### Authentication Module (`app/modules/auth/`)
- **models.py**: User model with Flask-Login integration
- **routes.py**: Authentication endpoints (login, register, profile)
- **service.py**: Authentication business logic
- **schemas.py**: Data validation schemas

#### Budget Module (`app/modules/budget/`)
- **models.py**: Category, Expense, Income, ExchangeRate models
- **routes.py**: Budget management endpoints
- **service.py**: Budget calculation and management logic
- **schemas.py**: Budget-related data validation

#### Goals Module (`app/modules/goals/`)
- **models.py**: SavingsGoal, SharedBudget models
- **routes.py**: Goal management endpoints  
- **service.py**: Goal tracking and progress calculation
- **schemas.py**: Goal-related data validation

#### API (`app/api/v1/`)
- **__init__.py**: API v1 blueprint registration
- **budget.py**: Budget-related API endpoints
- **goals.py**: Goals-related API endpoints
- **schemas.py**: API response schemas

### Database Design
SQLAlchemy models with Alembic migrations:
- **users**: User authentication and preferences
- **categories**: Budget categories with limits and rollover logic
- **expenses**: User expense records with multi-currency support
- **income**: Monthly income tracking per user
- **savings_goals**: Goal tracking with progress calculation
- **shared_budgets**: Family budget collaboration
- **shared_budget_members**: Budget sharing relationships
- **exchange_rates**: Currency exchange rate cache

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
- CSRF protection with Flask-WTF integration
- Template endpoint compatibility (non-blueprint structure)

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

### Key Implementation Details

#### Application Factory Pattern
- **Entry Point**: `app.py` - Minimal entry point that creates app instance
- **Factory**: `app/__init__.py:create_app()` - Configures and returns Flask app
- **Blueprint Registration**: All modules register as Flask blueprints
- **Backward Compatibility**: Legacy route endpoints are maintained for existing integrations

#### Database Migrations
- **Migration Directory**: `migrations/` - Alembic migration files
- **Configuration**: `migrations/alembic.ini` - Migration settings
- **Version Control**: All schema changes must go through migration system

#### Configuration Management
- **Environment-Based**: Development/Production/Testing configurations
- **Security**: Production config validates required environment variables
- **Database**: Configurable via `BUDGET_DB` environment variable
- **Sessions**: 30-day lifetime with secure cookie configuration

### Important File Locations
```
app/
├── __init__.py              # Application factory
├── core/                    # Core utilities and configuration
│   ├── config.py           # Environment-based config classes
│   ├── extensions.py       # Flask extensions initialization
│   └── [other core modules]
├── modules/                 # Feature modules
│   ├── auth/               # Authentication module
│   ├── budget/             # Budget management module
│   └── goals/              # Goals tracking module
└── api/                    # API endpoints
    └── v1/                 # API version 1

migrations/                  # Database migrations
templates/                   # Jinja2 templates
static/                     # Frontend assets  
admin_panel/                # Administrative interface
app.py                      # Application entry point
requirements.txt            # Python dependencies
crystalbudget.service       # Systemd service file
```

### Service Files
- `crystalbudget.service` - Main application systemd service (uses Gunicorn WSGI server)
- `admin_panel/admin-panel.service` - Admin panel systemd service

### Development Workflow

#### Adding New Features
1. Create new module in `app/modules/` or extend existing module
2. Define SQLAlchemy models in `models.py`
3. Generate migration: `flask db migrate -m "Add feature"`
4. Apply migration: `flask db upgrade`
5. Implement routes, services, and schemas
6. Register blueprint in `app/__init__.py` if new module
7. Add templates and static assets as needed

#### Working with Database
- **Model Changes**: Always create migrations for schema changes
- **Data Changes**: Use Flask CLI commands or write migration scripts
- **Testing**: Use in-memory SQLite for testing configuration

#### Code Organization Patterns
- **Models**: SQLAlchemy models with relationships and validation
- **Routes**: Flask blueprint routes handling HTTP requests/responses
- **Services**: Business logic separated from route handlers
- **Schemas**: Data validation using schemas (likely Marshmallow or similar)

### Service Installation
```bash
# Install main application service
sudo cp crystalbudget.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable crystalbudget
sudo systemctl start crystalbudget

# Install admin panel service  
sudo cp admin_panel/admin-panel.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable admin-panel
sudo systemctl start admin-panel
```