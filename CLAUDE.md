# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```bash
# Development server
python app.py

# Production with Gunicorn
gunicorn -w 2 -b 0.0.0.0:5000 app:app

# Production deployment (uses deploy.sh script)
./deploy.sh

# HTTPS setup after deployment
./setup-https.sh
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

# Database operations (SQLite CLI)
sqlite3 budget.db ".schema"
sqlite3 budget.db "SELECT * FROM users;"
```

## Architecture Overview

### Single-File Flask Application
The entire backend is contained in `app.py` (~2000+ lines) with:
- Multi-user authentication system with 30-day session persistence
- SQLite database with automatic schema initialization and default data
- Currency support (RUB, USD, EUR, AMD, GEL) with session-based selection
- Rotating file logging system in `/logs/`

### Database Design
SQLite with user data isolation and automatic schema creation:
- **users**: Authentication (password_hash), currency preferences, timestamps
- **categories**: Budget categories (name, limit_type: 'fixed'/'percentage', amount, user_id)
- **expenses**: User expense records (amount, description, category_id, date, user_id)
- **income**: Monthly income tracking (amount, month, year, user_id)
- **income_daily**: Daily income breakdown for advanced tracking
- **income_sources**: Income source management with percentages
- **source_category_rules**: Rules linking income sources to category allocations
- Auto-populated default categories on first run with Russian labels

### Frontend Structure
- **PWA-enabled**: Service worker, manifest, offline support
- **Mobile-first**: Optimized for iPhone Safari and Android
- **Bootstrap 5**: Responsive design with multiple CSS themes
- **Russian interface**: All UI text and messages in Russian
- **Inline editing**: Direct category editing in the interface

### Key Financial Features
- **Category types**: Fixed limits (e.g., 5000₽) or percentage-based (e.g., 30% of income)
- **Rollover system**: Unused category budgets carry forward to next months
- **Multi-currency**: Per-user currency selection with proper symbols
- **Decimal precision**: Financial calculations using Python's Decimal module

### Route Structure
**Core Application:**
- `/` - Redirects to dashboard or login
- `/dashboard` - Main budget overview with quick expense entry
- `/expenses` - Full expense CRUD operations with filtering
- `/categories` - Category management with inline editing
- `/income` - Monthly income configuration and tracking
- `/sources` - Income source management with percentage allocation

**Authentication & User Management:**
- `/register` - User registration with password hashing
- `/login` - Session-based authentication (30-day persistence)
- `/logout` - Session cleanup
- `/set-currency` - Per-user currency selection

**API Endpoints:**
- `/quick-expense` - POST endpoint for dashboard expense entry
- `/health` - Application health check
- `/favicon.ico` - Static favicon handler
- `/logs` - Development log viewer (debug mode only)

**Advanced Features:**
- `/rules/upsert/<category_id>` - Category-source allocation rules
- `/rules/bulk-update` - Bulk rule updates for income distribution

## Key Implementation Details

### Financial Calculations
- Uses Python's `Decimal` class for precision in financial calculations
- Supports both fixed amount categories (e.g., 5000₽) and percentage-based (e.g., 30% of income)
- Rollover system: unused budget amounts carry forward to subsequent months
- Multi-currency support with proper symbol display (₽, $, €, ֏, ₾)

### Session Management
- Flask sessions with 30-day permanent lifetime
- Secure cookie settings for production (HTTPS_MODE environment variable)
- User isolation: all database queries filtered by session user_id

### Logging System
- Rotating file logs in `/logs/crystalbudget.log` (max 10MB per file, 5 files)
- Configurable log levels via LOG_LEVEL environment variable
- Separate access and error logs for Gunicorn in production

### Deployment Architecture
- **Development**: Direct `python app.py` execution
- **Production**: Gunicorn WSGI server with 2 workers
- **System Integration**: systemd service (`crystalbudget.service`)
- **Web Server**: Nginx reverse proxy configuration included
- **SSL/HTTPS**: Let's Encrypt integration via `setup-https.sh`

### PWA Features
- Service worker for offline functionality (`static/service-worker.js`)
- Web app manifest for mobile app-like experience
- Multiple CSS themes: clean, modern, improved, ff-theme
- Bootstrap 5 responsive design optimized for mobile devices