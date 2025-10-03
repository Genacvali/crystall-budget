#!/bin/bash
# Deployment script for production database migration
# This script applies all pending migrations to production database

set -e  # Exit on error

echo "🚀 CrystalBudget Production Deployment"
echo "======================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_ROOT/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Ensure we're in project root
cd "$PROJECT_ROOT"

# Step 1: Check if virtual environment exists
echo -e "${YELLOW}[1/7]${NC} Checking virtual environment..."
if [ ! -d ".venv" ]; then
    echo -e "${RED}Error: Virtual environment not found!${NC}"
    echo "Please create it first: python3 -m venv .venv"
    exit 1
fi
source .venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo ""

# Step 2: Check database path
echo -e "${YELLOW}[2/7]${NC} Checking database configuration..."
if [ -z "$BUDGET_DB" ]; then
    export BUDGET_DB="sqlite:////opt/crystall-budget/instance/budget.db"
    echo "Using default database: $BUDGET_DB"
else
    echo "Using configured database: $BUDGET_DB"
fi

# Extract database file path from URI
DB_FILE=$(echo "$BUDGET_DB" | sed 's|sqlite:///||')
if [ ! -f "$DB_FILE" ]; then
    echo -e "${RED}Error: Database file not found: $DB_FILE${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Database found: $DB_FILE${NC}"
echo ""

# Step 3: Create backup
echo -e "${YELLOW}[3/7]${NC} Creating database backup..."
mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/budget_${TIMESTAMP}.db"
cp "$DB_FILE" "$BACKUP_FILE"
echo -e "${GREEN}✓ Backup created: $BACKUP_FILE${NC}"
echo ""

# Step 4: Check current migration state
echo -e "${YELLOW}[4/7]${NC} Checking current migration state..."
CURRENT_MIGRATION=$(flask db current 2>&1 | grep -E "^[a-f0-9_]+" | awk '{print $1}' || echo "none")
echo "Current migration: $CURRENT_MIGRATION"
echo ""

# Step 5: Show pending migrations
echo -e "${YELLOW}[5/7]${NC} Checking for pending migrations..."
flask db upgrade --sql > /tmp/pending_migrations.sql 2>&1 || true
if [ -s /tmp/pending_migrations.sql ]; then
    echo -e "${YELLOW}Pending SQL changes:${NC}"
    echo "----------------------------------------"
    head -50 /tmp/pending_migrations.sql
    echo "----------------------------------------"
    echo ""
else
    echo -e "${GREEN}✓ No pending migrations${NC}"
    echo ""
fi

# Step 6: Apply migrations
echo -e "${YELLOW}[6/7]${NC} Applying migrations..."
read -p "Continue with migration? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo -e "${RED}Deployment cancelled${NC}"
    exit 1
fi

echo "Running: flask db upgrade"
flask db upgrade

NEW_MIGRATION=$(flask db current 2>&1 | grep -E "^[a-f0-9_]+" | awk '{print $1}' || echo "none")
echo -e "${GREEN}✓ Migrations applied${NC}"
echo "New migration: $NEW_MIGRATION"
echo ""

# Step 7: Verify database integrity
echo -e "${YELLOW}[7/7]${NC} Verifying database integrity..."
sqlite3 "$DB_FILE" "PRAGMA integrity_check;" | head -5
echo -e "${GREEN}✓ Database integrity OK${NC}"
echo ""

# Summary
echo "======================================"
echo -e "${GREEN}✓ Deployment completed successfully!${NC}"
echo ""
echo "Summary:"
echo "  - Backup: $BACKUP_FILE"
echo "  - Migration: $CURRENT_MIGRATION → $NEW_MIGRATION"
echo "  - Database: $DB_FILE"
echo ""
echo "Next steps:"
echo "  1. Restart the application: sudo systemctl restart crystalbudget"
echo "  2. Check logs: sudo journalctl -u crystalbudget -f"
echo "  3. Test the application"
echo ""
echo "To rollback (if needed):"
echo "  sudo systemctl stop crystalbudget"
echo "  cp $BACKUP_FILE $DB_FILE"
echo "  sudo systemctl start crystalbudget"
echo ""
