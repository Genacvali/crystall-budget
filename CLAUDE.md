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
- Multi-user authentication with 30-day sessions
- SQLite database with automatic schema initialization
- Multi-currency support (RUB, USD, EUR, AMD, GEL)
- PWA support with offline functionality

### Database Design
SQLite with user isolation:
- **users**: Authentication and preferences
- **categories**: Budget categories (fixed/percentage limits)
- **expenses**: User expense records
- **income**: Monthly income tracking
- **savings_goals**: Goal tracking with progress
- **shared_budgets**: Family budget collaboration

### Frontend Structure
- **Templates**: 16 HTML templates with Bootstrap 5
- **PWA**: Service worker, manifest, offline support
- **Russian interface**: All UI text in Russian
- **Mobile-first**: Optimized for mobile devices

### Key Features
- Fixed and percentage-based budget categories
- Budget rollover system
- Multi-currency with live exchange rates
- Savings goals with progress tracking
- Family budget sharing
- Comprehensive analytics and charts

### Production Files
Essential files for production deployment:
- `app.py` - Main application
- `requirements.txt` - Dependencies
- `templates/` - HTML templates
- `static/` - CSS, JS, PWA files
- `deploy.sh` - Deployment script
- `setup-https.sh` - SSL setup
- `crystalbudget.service` - Systemd service
- `nginx-crystalbudget.conf` - Nginx configuration