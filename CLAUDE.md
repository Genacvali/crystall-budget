# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```bash
# Development server (legacy single-file)
python app.py

# Development server (modular architecture) 
python -m app

# Management utility (preferred for development)
python manage.py run

# Production with Gunicorn
gunicorn -w 2 -b 0.0.0.0:5000 app:app  # legacy
gunicorn -w 2 -b 0.0.0.0:5000 "app:create_app()"  # modular

# Production deployment
./deploy.sh

# HTTPS setup after deployment
./setup-https.sh
```

### Database Management
```bash
# Initialize database (modular)
python manage.py init-db

# Run migrations (for both architectures)
python migrate_to_modular.py
python migrate_new_tables.py

# Seed with test data
python manage.py seed

# Database operations (SQLite CLI)
sqlite3 budget.db ".schema"
sqlite3 budget.db "SELECT * FROM users;"
```

### Environment Variables
- `SECRET_KEY`: Flask secret key (required for production)
- `BUDGET_DB`: Database file path (default: "budget.db") 
- `HTTPS_MODE`: Set to 'true' for production HTTPS cookie settings
- `LOG_LEVEL`: Logging level (default: INFO)

### Testing and Debugging
```bash
# Check application health
curl http://localhost:5000/health

# View logs (rotating logs in /logs/ directory)
tail -f logs/crystalbudget.log

# Check systemd service status (production)
sudo systemctl status crystalbudget

# Development log viewer (debug mode only)
curl http://localhost:5000/logs
```

## Architecture Overview

### Dual Architecture Support
CrystalBudget supports two architectures:
1. **Legacy Single-File** (`app.py` ~2000+ lines) - Original monolithic Flask application
2. **Modular Architecture** (`app/` directory) - New blueprints-based structure for better maintainability

Both architectures share the same database schema and functionality, with the modular version being preferred for new development.

### Modular Structure (`app/` directory)
```
app/
├── __init__.py          # Application factory with create_app()
├── config.py           # Configuration management  
├── db.py               # Database initialization and schema
├── extensions.py       # Flask extensions setup
├── security.py         # Security headers and middleware
├── services/           # Business logic services
│   ├── currency.py     # Currency conversion and rates
│   └── validation.py   # Input validation helpers
├── api/               # API endpoints
├── blueprints/        # Feature-based blueprints
│   ├── auth/          # Authentication (login, register, logout)
│   ├── dashboard/     # Main dashboard and quick expense entry
│   ├── expenses/      # Expense CRUD operations
│   ├── categories/    # Category management
│   ├── income/        # Income tracking and sources
│   ├── goals/         # Savings goals
│   └── shared/        # Family budget sharing
└── templates/         # Jinja2 templates organized by blueprint
```

### Database Design
SQLite with user data isolation and automatic schema creation:
- **users**: Authentication, currency preferences, theme settings
- **categories**: Budget categories (fixed amounts or percentage-based)
- **expenses**: User expense records with category linking
- **income**: Monthly income tracking with multi-source support  
- **income_sources**: Income source management with percentage allocation
- **source_category_rules**: Automatic income-to-category distribution rules
- **savings_goals**: Goal tracking with progress monitoring
- **shared_budgets**: Family budget collaboration with invite codes
- **shared_budget_members**: Budget membership with role-based access
- **exchange_rates**: Multi-currency rate caching with hourly refresh

Auto-populated default categories on first run with Russian labels.

### Frontend Architecture  
- **PWA-enabled**: Service worker (`static/service-worker.js`), manifest, offline support
- **Mobile-first**: Optimized for iPhone Safari and Android Chrome
- **Bootstrap 5**: Responsive design with multiple CSS themes (`static/css/`)
- **Russian interface**: All UI text and messages in Russian
- **Chart.js integration**: Analytics and expense visualization (`static/js/`)
- **Swipe gestures**: Mobile-friendly edit/delete actions

### Key Financial Features
- **Category types**: Fixed limits (5000₽) or percentage-based (30% of income)
- **Rollover system**: Unused budgets automatically carry forward to next months
- **Multi-currency**: Per-user currency selection (₽, $, €, ֏, ₾) with live rates  
- **Decimal precision**: All financial calculations use Python's Decimal module
- **Income distribution**: Automatic percentage-based allocation from sources to categories

### Route Structure Overview
**Core Application:**
- `/` - Smart redirect to dashboard or login
- `/dashboard` - Main budget overview with quick expense entry
- `/expenses` - Full expense CRUD with filtering and swipe actions
- `/categories` - Category management with inline editing
- `/income` - Monthly income and source management
- `/goals` - Savings goals with progress tracking
- `/shared-budgets` - Family budget collaboration

**API Endpoints:**
- `/api/expenses/chart-data` - Chart.js analytics data (monthly/category breakdowns)
- `/api/expenses/compare` - Period comparison with percentage changes
- `/api/exchange-rates` - Multi-currency rates with caching
- `/health` - Application health check

**Authentication:**
- `/register`, `/login`, `/logout` - Session-based auth with 30-day persistence
- `/set-currency` - Per-user currency selection

## Key Implementation Details

### Migration Between Architectures
- Use `migrate_to_modular.py` to migrate from single-file to modular architecture
- Both versions share the same database schema and can run side-by-side during transition
- The `manage.py` utility provides unified commands for both architectures

### Session Management & Security
- Flask sessions with 30-day permanent lifetime
- Production security headers: CSP, HSTS, XSS protection, frame options
- Secure cookie settings: HttpOnly, Secure (HTTPS), SameSite=Lax
- User isolation: all database queries filtered by session user_id

### Logging System  
- Rotating file logs in `/logs/crystalbudget.log` (10MB max, 5 files)
- Configurable log levels via LOG_LEVEL environment variable
- Separate Gunicorn access/error logs in production

### Deployment Architecture
- **Development**: Direct Python execution or manage.py
- **Production**: Gunicorn WSGI server with Nginx reverse proxy
- **System Integration**: systemd service (`crystalbudget.service`)
- **SSL/HTTPS**: Let's Encrypt via `setup-https.sh` script

### Currency & Internationalization
- **Russian Interface**: All UI text, messages, and default categories in Russian
- **Multi-currency support**: Live exchange rates with automatic hourly updates
- **Default categories** (auto-created):
  - Продукты (30% от дохода) - Groceries
  - Транспорт (5000₽ фикс.) - Transport
  - Развлечения (15% от дохода) - Entertainment
  - Коммунальные (8000₽ фикс.) - Utilities  
  - Здоровье (3000₽ фикс.) - Health
  - Одежда (10% от дохода) - Clothing

## Development Workflow

### Working with the Modular Architecture
When developing new features, prefer the modular architecture:
1. Create new blueprints in `app/blueprints/`
2. Add business logic to `app/services/`  
3. Use the application factory pattern from `app/__init__.py`
4. Run via `python manage.py run` for development

### Database Changes
1. Update schema in `app/db.py` (init_db function)
2. Create migration script following `migrate_*.py` pattern
3. Test migration on copy of production database
4. Update CLAUDE.md with new table/column documentation

### Adding New Features
1. Follow the blueprint pattern established in `app/blueprints/`
2. Organize templates by blueprint in `app/templates/`
3. Add API endpoints to `app/api/` if needed
4. Update route documentation in this file