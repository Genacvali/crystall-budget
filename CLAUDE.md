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
```

### Environment Variables
- `SECRET_KEY`: Flask secret key (required for production)
- `BUDGET_DB`: Database file path (default: "budget.db")
- `HTTPS_MODE`: Set to 'true' for production HTTPS cookie settings
- `LOG_LEVEL`: Logging level (default: INFO)

## Architecture Overview

### Single-File Flask Application
The entire backend is contained in `app.py` (~2000+ lines) with:
- Multi-user authentication system with 30-day session persistence
- SQLite database with automatic schema initialization and default data
- Currency support (RUB, USD, EUR, AMD, GEL) with session-based selection
- Rotating file logging system in `/logs/`

### Database Design
SQLite with user data isolation:
- **users**: Authentication, currency preferences
- **categories**: Budget categories (fixed amounts or income percentages)
- **expenses**: User expense records with category association
- **income**: Monthly income tracking by user
- Auto-populated default categories on first run

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
- `/` - Dashboard with budget overview and quick expense entry
- `/expenses` - Full expense CRUD operations
- `/categories` - Category management with inline editing
- `/income` - Monthly income configuration
- `/sources` - Income source management
- Authentication routes for multi-user support