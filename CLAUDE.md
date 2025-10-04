# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Paths

**Production Configuration:**
- Project directory: `/opt/crystall-budget`
- Database: `/var/lib/crystalbudget/budget.db` (URI: `sqlite:////var/lib/crystalbudget/budget.db`)
- Backups: `/var/lib/crystalbudget/backups/`
- Service name: `crystalbudget`
- Service port: `5000` (127.0.0.1:5000, proxied via nginx)
- Development/Testing port: `5030` (when running with MODAL_SYSTEM_ENABLED=true PORT=5030)

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

#### Migration Commands
```bash
# Check current migration status
flask db current

# View migration history
flask db history

# Create new migration (auto-generate from models)
flask db migrate -m "Description of changes"

# Apply all pending migrations
flask db upgrade

# Rollback one migration
flask db downgrade -1

# Rollback to specific revision
flask db downgrade <revision_id>

# Show SQL without applying (dry-run)
flask db upgrade --sql

# Create empty migration (for data migrations)
flask db revision -m "Description"
```

#### Production Migration Workflow
```bash
# First-time setup on existing production database
./scripts/prod_baseline.sh

# Apply migrations to production (with automatic backup)
./scripts/prod_migrate.sh

# Manual backup before risky operations
./scripts/backup_db.sh
```

#### Important Notes
- **SQLite-specific**: Project configured with `render_as_batch=True` for proper ALTER operations
- **Type checking**: `compare_type=True` detects column type changes
- **Default checking**: `compare_server_default=True` detects default value changes
- **Always backup** before production migrations (scripts do this automatically)
- **Test migrations** on staging/dev before production
- See `docs/MIGRATIONS.md` for detailed migration guide

### Testing and Code Quality
```bash
# Run full test suite (preferred method)
./scripts/run-tests.sh

# Run specific test suites
./scripts/run-tests.sh --suite api        # API tests only
./scripts/run-tests.sh --suite e2e        # E2E tests only  
./scripts/run-tests.sh --suite smoke      # Smoke test validation
./scripts/run-tests.sh --suite all        # All automated tests

# Additional test script options
./scripts/run-tests.sh --verbose          # Enable verbose output
./scripts/run-tests.sh --stop-on-fail     # Stop on first failure

# CI-compatible test runner (for production environments)
APP_PORT=5000 APP_CONFIG=testing ./scripts/ci-check.sh --suite all --no-e2e

# Fast CI tests (no server startup)
APP_PORT=5000 APP_CONFIG=testing ./scripts/ci-check.sh --suite api --fast

# Manual testing and verification
python app.py  # Then visit http://localhost:5000

# Syntax checking
python -m py_compile app.py
find app/ -name "*.py" -exec python -m py_compile {} \;

# Install test dependencies
pip install -r requirements-test.txt
playwright install chromium  # For E2E tests
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
- **diagnostics.py**: Application diagnostics and debugging tools
- **monitoring.py**: Modal system performance monitoring
- **telemetry.py**: Event tracking and telemetry collection
- **features.py**: Feature flag management for modal system
- **bundles.py**: Bundle configuration for frontend assets
- **assets.py**: Asset management helpers for templates
- **screenshots.py**: Screenshot capture and comparison utilities

#### Authentication Module (`app/modules/auth/`)
- **models.py**: User model with Flask-Login integration
- **routes.py**: Authentication endpoints (login, register, profile, theme settings)
- **service.py**: Authentication business logic and Telegram integration
- **schemas.py**: Data validation schemas

#### Budget Module (`app/modules/budget/`)
- **models.py**: Category, Expense, Income, ExchangeRate, IncomeSource models
- **routes.py**: Budget management endpoints (dashboard, expenses, categories, income)
- **service.py**: Budget calculation and management logic
- **schemas.py**: Budget-related data validation

#### Goals Module (`app/modules/goals/`)
- **models.py**: SavingsGoal, SharedBudget, SharedBudgetMember models
- **routes.py**: Goal management endpoints and family budget sharing
- **service.py**: Goal tracking and progress calculation
- **schemas.py**: Goal-related data validation

#### Issues Module (`app/modules/issues/`)
- **models.py**: Issue and IssueComment models for user feedback
- **routes.py**: Issue reporting and management endpoints
- **service.py**: Issue handling logic

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
- **income_sources**: Income source tracking
- **issues**: User feedback and issue reporting
- **issue_comments**: Comments on reported issues

### Frontend Structure
- **Templates**: 76 HTML templates using Bootstrap 5 and Russian localization
- **Components**: Reusable template components in `/templates/components/` including modals
- **PWA**: Complete Progressive Web App with manifest, service worker, offline support
- **Mobile-first**: Optimized for iOS Safari and Android with swipe gestures
- **Static assets**:
  - PWA files (manifest.json, manifest.webmanifest)
  - Service worker (sw.js) for offline functionality
  - JavaScript modules in `/static/js/`:
    - `app.js` - Main application logic and initialization
    - `modals.js` - Modal system for dynamic content loading
    - `dashboard-cats.js` - Dashboard category management
    - `progress_bars.js` - Progress bar animations
    - `offline.js` - Offline functionality
    - `accessibility.js` - Accessibility features
    - `kanban.js` - Kanban board functionality
    - `nav-ff.js` - Navigation and feature flags
    - `entries/` - Page-specific entry points (dashboard.entry.js, expenses.entry.js, etc.)
    - `modules/` - Reusable modules (ui.js, forms.js, swipe.js, etc.)
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
- Dynamic modal system for settings, goals, and forms
- Health check endpoint (`/healthz`) for monitoring
- Modal performance monitoring dashboard (`/monitoring/modal-system`)
- Telemetry API for frontend event tracking (`/api/telemetry/modal`)

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


### Flask CLI Commands
```bash
# Database management
flask db-cli init-db                    # Initialize database with schema
flask db-cli seed-categories --user-id=1 # Add default categories for user

# User management  
flask user-cli list-users               # List all users
flask user-cli user-stats --user-id=1   # Show user statistics
flask user-cli create-user --name="Test" --email="test@example.com" --password="pass123"

# Budget operations
flask budget-cli recalc-month --user-id=1 --ym=2024-01  # Recalculate budget for month
flask budget-cli sync-currencies --user-id=1            # Update exchange rates

# Development utilities
flask dev-cli create-test-expenses --user-id=1 --count=20  # Generate test data

# Screenshot management (UI testing)
flask screenshot capture auth --url=http://localhost:5030 --variants=desktop,mobile
flask screenshot compare before.png after.png --threshold=0.1
flask screenshot auto-dashboard          # Capture dashboard in all states
```

### Environment Variables
```bash
# Required for production
SECRET_KEY="your-secure-secret-key"
HTTPS_MODE="true"  # Enables secure cookies and HSTS headers
TELEGRAM_BOT_TOKEN="your-telegram-bot-token"  # Required for Telegram authentication

# Optional configuration
BUDGET_DB="sqlite:////var/lib/crystalbudget/budget.db"  # Database URI (SQLAlchemy format)
LOG_LEVEL="INFO"  # Logging level (DEBUG, INFO, WARNING, ERROR)
LOG_DIR="/var/lib/crystalbudget/logs"  # Directory for application logs (default: /var/lib/crystalbudget/logs)
APP_CONFIG="testing"  # Configuration mode (development/production/testing)
DIAGNOSTICS_ENABLED="false"  # Enable diagnostics mode
MODAL_SYSTEM_ENABLED="true"  # Kill-switch for modal system (default: true)
TELEGRAM_LOGIN_ENABLED="false"  # Enable/disable Telegram login widget (default: true, set to false if domain not configured in @BotFather)

```

### Key Implementation Details

#### Application Factory Pattern
- **Entry Point**: `app.py` - Minimal entry point that creates app instance
- **Factory**: `app/__init__.py:create_app()` - Configures and returns Flask app with optional config name parameter
- **Blueprint Registration**: All modules register as Flask blueprints (`auth`, `budget`, `goals`, `issues`, `api_v1`)
- **Configuration**: Supports multiple configs via `APP_CONFIG` environment variable (development/production/testing)
- **Backward Compatibility**: Legacy route endpoints are maintained for existing integrations at app root
- **Testing Support**: Special testing configuration with CSRF disabled and auto-authentication via request loader
- **Modal Routes**: Dynamic modal content endpoints registered at `/modals/*` for goals and settings
- **Monitoring**: Built-in endpoints for health checks, modal performance monitoring, and telemetry collection

#### Database Migrations
- **Migration Directory**: `migrations/` - Alembic migration files
- **Configuration**: `migrations/alembic.ini` - Migration settings with timestamp naming
- **SQLite Batch Mode**: Enabled via `render_as_batch=True` in `app/__init__.py:74-80`
- **Type Comparison**: Enabled via `compare_type=True` to detect column type changes
- **Default Comparison**: Enabled via `compare_server_default=True` to detect default value changes
- **Version Control**: All schema changes must go through migration system
- **Production Scripts**: `scripts/prod_baseline.sh`, `scripts/prod_migrate.sh`, `scripts/backup_db.sh`
- **Documentation**: See `docs/MIGRATIONS.md` for complete workflow guide

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
│   ├── goals/              # Goals tracking module
│   └── issues/             # Issue reporting module
└── api/                    # API endpoints
    └── v1/                 # API version 1

migrations/                  # Database migrations
templates/                   # Jinja2 templates
static/                     # Frontend assets  
admin_panel/                # Administrative interface
tests/                      # Test suite (API, E2E, smoke)
scripts/                    # Test and CI scripts
app.py                      # Application entry point
requirements.txt            # Python dependencies
requirements-test.txt       # Test dependencies
crystalbudget.service       # Systemd service file
```

### Service Files
- `crystalbudget.service` - Main application systemd service
  - Gunicorn WSGI server with 3 workers, 2 threads per worker
  - Binds to 127.0.0.1:5000 (localhost only)
  - Uses `/opt/crystall-budget/.venv/bin/gunicorn`
  - Security hardening: NoNewPrivileges, PrivateTmp, ProtectSystem
  - Runs as `admin:admin` user
- `admin_panel/admin-panel.service` - Admin panel systemd service (port 5001)

**Note**: Production service requires nginx reverse proxy in front of Gunicorn for HTTPS termination and public access.

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
- **Model Changes**: Always create migrations for schema changes via `flask db migrate`
- **Data Changes**: Create empty migrations via `flask db revision` and add data logic
- **Testing**: Use in-memory SQLite for testing configuration
- **Production**: Use `scripts/prod_migrate.sh` for safe production migrations with auto-backup
- **Baseline**: For existing prod DB without migrations, use `scripts/prod_baseline.sh` once

#### Code Organization Patterns
- **Models**: SQLAlchemy models with relationships and validation
- **Routes**: Flask blueprint routes handling HTTP requests/responses
- **Services**: Business logic separated from route handlers
- **Schemas**: Data validation using schemas (likely Marshmallow or similar)

#### Testing Strategy
- **API Tests**: Located in `tests/api/` - test API endpoints and business logic
- **E2E Tests**: Located in `tests/e2e/` - browser-based user flow testing with Playwright
- **Smoke Tests**: Basic validation that app starts and core endpoints respond
- **Screenshot Testing**: UI regression testing with visual comparisons
- **Test Configuration**: Uses `TestingConfig` with CSRF disabled and auto-authentication
- **Test Endpoints**: `/modal-test` and `/qa-modal-test` for manual UI testing

#### Important Debugging Endpoints
- `/healthz` - Health check endpoint (validates DB connection and migrations)
- `/monitoring/modal-system` - Modal system performance dashboard (auth required)
- `/monitoring/modal-system/api` - JSON API for modal metrics (auth required)
- `/api/telemetry/modal` - POST endpoint for client-side telemetry collection
- `/modal-test` - Modal system testing page
- `/qa-modal-test` - QA testing page for unified modal system

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