#!/bin/bash
# Sync existing production database with migration state
# Use this when database already has tables but alembic_version is missing/outdated

set -e

echo "🔧 CrystalBudget Migration Sync"
echo "================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Activate venv
if [ ! -d ".venv" ]; then
    echo -e "${RED}Error: Virtual environment not found!${NC}"
    exit 1
fi
source .venv/bin/activate

# Check database path
if [ -z "$BUDGET_DB" ]; then
    export BUDGET_DB="sqlite:////var/lib/crystalbudget/budget.db"
fi
DB_FILE=$(echo "$BUDGET_DB" | sed 's|sqlite:///||')

echo -e "${YELLOW}Database:${NC} $DB_FILE"
echo ""

# Check what tables exist
echo -e "${YELLOW}[1/4]${NC} Checking existing tables..."
TABLES=$(sqlite3 "$DB_FILE" ".tables" 2>/dev/null || echo "")
echo "Existing tables: $TABLES"
echo ""

# Check alembic_version
echo -e "${YELLOW}[2/4]${NC} Checking migration state..."
CURRENT_VERSION=$(sqlite3 "$DB_FILE" "SELECT version_num FROM alembic_version LIMIT 1;" 2>/dev/null || echo "none")
echo "Current alembic version: $CURRENT_VERSION"
echo ""

# Analyze database state
echo -e "${YELLOW}[3/4]${NC} Analyzing database state..."
HAS_USERS=$(sqlite3 "$DB_FILE" "SELECT name FROM sqlite_master WHERE type='table' AND name='users';" 2>/dev/null || echo "")
HAS_CATEGORIES=$(sqlite3 "$DB_FILE" "SELECT name FROM sqlite_master WHERE type='table' AND name='categories';" 2>/dev/null || echo "")
HAS_EXPENSES=$(sqlite3 "$DB_FILE" "SELECT name FROM sqlite_master WHERE type='table' AND name='expenses';" 2>/dev/null || echo "")
HAS_SHARED_BUDGETS=$(sqlite3 "$DB_FILE" "SELECT name FROM sqlite_master WHERE type='table' AND name='shared_budgets';" 2>/dev/null || echo "")
HAS_INCOME_SOURCES=$(sqlite3 "$DB_FILE" "SELECT name FROM sqlite_master WHERE type='table' AND name='income_sources';" 2>/dev/null || echo "")

# Check for shared_budget_id column in users
HAS_SHARED_BUDGET_ID=$(sqlite3 "$DB_FILE" "PRAGMA table_info(users);" 2>/dev/null | grep -i "shared_budget_id" || echo "")

echo "Tables found:"
echo "  - users: ${HAS_USERS:-❌}"
echo "  - categories: ${HAS_CATEGORIES:-❌}"
echo "  - expenses: ${HAS_EXPENSES:-❌}"
echo "  - shared_budgets: ${HAS_SHARED_BUDGETS:-❌}"
echo "  - income_sources: ${HAS_INCOME_SOURCES:-❌}"
echo ""
echo "Schema checks:"
echo "  - users.shared_budget_id: ${HAS_SHARED_BUDGET_ID:-❌}"
echo ""

# Determine target migration
TARGET_MIGRATION=""
if [ -n "$HAS_SHARED_BUDGET_ID" ]; then
    TARGET_MIGRATION="add_shared_budget_to_users"
    echo -e "${GREEN}✓ Database schema matches: add_shared_budget_to_users (latest)${NC}"
elif [ -n "$HAS_SHARED_BUDGETS" ]; then
    TARGET_MIGRATION="515954c99c28"
    echo -e "${YELLOW}! Database schema matches: 515954c99c28 (needs upgrade)${NC}"
elif [ -n "$HAS_INCOME_SOURCES" ]; then
    TARGET_MIGRATION="d06c52a8b6a7"
    echo -e "${YELLOW}! Database schema matches: d06c52a8b6a7 (needs upgrade)${NC}"
elif [ -n "$HAS_USERS" ]; then
    TARGET_MIGRATION="1b77062a812f"
    echo -e "${YELLOW}! Database schema matches: 1b77062a812f (needs upgrade)${NC}"
else
    echo -e "${RED}✗ Database appears empty or corrupted${NC}"
    exit 1
fi
echo ""

# Stamp database
echo -e "${YELLOW}[4/4]${NC} Stamping database with migration: $TARGET_MIGRATION"
echo ""
read -p "Continue? This will mark the database as being at this migration. (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Cancelled"
    exit 0
fi

# Create alembic_version table if missing
sqlite3 "$DB_FILE" "CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL, CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num));" 2>/dev/null || true

# Stamp the database
flask db stamp "$TARGET_MIGRATION"

NEW_VERSION=$(sqlite3 "$DB_FILE" "SELECT version_num FROM alembic_version LIMIT 1;" 2>/dev/null || echo "none")
echo ""
echo "================================"
echo -e "${GREEN}✓ Database stamped successfully!${NC}"
echo ""
echo "Migration state: $CURRENT_VERSION → $NEW_VERSION"
echo ""

if [ "$TARGET_MIGRATION" = "add_shared_budget_to_users" ]; then
    echo -e "${GREEN}✓ Database is up to date!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Restart application: sudo systemctl restart crystalbudget"
    echo "  2. Test the application"
else
    echo -e "${YELLOW}! Database needs upgrade${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Run: ./scripts/deploy_prod.sh"
    echo "  2. This will upgrade from $TARGET_MIGRATION to latest"
fi
echo ""
