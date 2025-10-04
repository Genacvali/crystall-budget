#!/bin/bash
# Create baseline migration for existing production database
# Use this script ONCE when first setting up migrations on production

set -e

# Configuration
PROD_PATH="/opt/crystall-budget"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${YELLOW}📋 CrystalBudget Production Baseline${NC}"
echo "====================================="
echo ""
echo -e "${YELLOW}⚠️  WARNING: Use this script ONLY ONCE when first setting up migrations!${NC}"
echo -e "${YELLOW}⚠️  If you already have migrations, use prod_migrate.sh instead.${NC}"
echo ""
read -p "Is this the FIRST TIME setting up migrations on this database? (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
    echo -e "${RED}Cancelled. Use prod_migrate.sh for normal migrations.${NC}"
    exit 1
fi

# Change to project directory
cd "$PROD_PATH" || exit 1
echo -e "Working directory: ${GREEN}$PROD_PATH${NC}"

# Activate virtual environment
if [ ! -f ".venv/bin/activate" ]; then
    echo -e "${RED}❌ Virtual environment not found!${NC}"
    exit 1
fi

echo -e "${YELLOW}Activating virtual environment...${NC}"
source .venv/bin/activate

# Check if migrations directory exists
if [ ! -d "migrations" ]; then
    echo -e "${RED}❌ Migrations directory not found!${NC}"
    echo -e "Run: ${BLUE}flask db init${NC}"
    exit 1
fi

# Check current migration status
echo -e "${BLUE}Checking current migration status...${NC}"
if flask db current 2>/dev/null | grep -q "None"; then
    echo -e "${GREEN}✅ No migrations applied yet - good for baseline${NC}"
else
    echo -e "${YELLOW}⚠️  Database already has migrations!${NC}"
    flask db current
    read -p "Continue anyway? (yes/no): " -r
    echo
    if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
        echo -e "${RED}Cancelled${NC}"
        exit 1
    fi
fi

# Step 1: Backup database
echo -e "${YELLOW}Step 1/3: Creating database backup...${NC}"
./scripts/backup_db.sh || {
    echo -e "${RED}❌ Backup failed! Aborting.${NC}"
    exit 1
}

# Step 2: Create baseline migration
echo -e "${YELLOW}Step 2/3: Creating baseline migration...${NC}"
echo -e "${BLUE}This will create a migration that matches your current database schema${NC}"
echo ""

# Generate migration from current models
if flask db migrate -m "baseline production schema"; then
    echo -e "${GREEN}✅ Baseline migration created${NC}"

    # Find the created migration file
    LATEST_MIGRATION=$(ls -t migrations/versions/*.py 2>/dev/null | head -1)
    if [ -n "$LATEST_MIGRATION" ]; then
        echo -e "${BLUE}Migration file: $LATEST_MIGRATION${NC}"
        echo ""
        echo -e "${YELLOW}Preview of migration:${NC}"
        head -30 "$LATEST_MIGRATION"
        echo ""
    fi
else
    echo -e "${RED}❌ Failed to create baseline migration${NC}"
    exit 1
fi

# Step 3: Stamp database
echo -e "${YELLOW}Step 3/3: Stamping database with baseline...${NC}"
echo -e "${BLUE}This tells Alembic that the database is at this migration level${NC}"
echo ""

read -p "Stamp database with baseline? (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
    echo -e "${RED}Cancelled${NC}"
    echo -e "${YELLOW}You can stamp later with: ${BLUE}flask db stamp head${NC}"
    exit 1
fi

if flask db stamp head; then
    echo -e "${GREEN}✅ Database stamped successfully${NC}"

    # Show current status
    echo ""
    echo -e "${BLUE}Current migration status:${NC}"
    flask db current
    flask db history
else
    echo -e "${RED}❌ Failed to stamp database${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Baseline setup complete!${NC}"
echo ""
echo -e "${BLUE}What this means:${NC}"
echo "- Your database schema is now under version control"
echo "- Future changes should use: flask db migrate -m 'description'"
echo "- To apply migrations: ./scripts/prod_migrate.sh"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Commit the baseline migration to git:"
echo -e "   ${BLUE}git add migrations/versions/${NC}"
echo -e "   ${BLUE}git commit -m 'Add baseline migration'${NC}"
echo "2. Make model changes and create migrations:"
echo -e "   ${BLUE}flask db migrate -m 'Add new feature'${NC}"
echo "3. Apply migrations on production:"
echo -e "   ${BLUE}./scripts/prod_migrate.sh${NC}"
