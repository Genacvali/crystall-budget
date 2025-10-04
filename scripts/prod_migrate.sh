#!/bin/bash
# Production database migration script for CrystalBudget
# This script safely applies database migrations to production

set -e

# Configuration
PROD_PATH="/opt/crystalbudget/crystall-budget"
DB_PATH="/var/lib/crystalbudget/budget.db"
SERVICE_NAME="crystalbudget"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🚀 CrystalBudget Production Migration${NC}"
echo "====================================="

# Check if running as correct user
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}⚠️  Do not run this script as root!${NC}"
    echo -e "Run as the application user (e.g., 'admin')"
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

# Check current migration status
echo -e "${BLUE}Current migration status:${NC}"
flask db current || echo -e "${YELLOW}No migration history found${NC}"

echo ""
echo -e "${BLUE}Pending migrations:${NC}"
flask db heads

echo ""
echo -e "${YELLOW}⚠️  WARNING: This will modify the production database!${NC}"
read -p "Continue? (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
    echo -e "${RED}Migration cancelled${NC}"
    exit 1
fi

# Step 1: Backup database
echo -e "${YELLOW}Step 1/4: Creating database backup...${NC}"
./scripts/backup_db.sh || {
    echo -e "${RED}❌ Backup failed! Aborting migration.${NC}"
    exit 1
}

# Step 2: Stop the service
echo -e "${YELLOW}Step 2/4: Stopping application...${NC}"
if systemctl is-active --quiet "$SERVICE_NAME"; then
    sudo systemctl stop "$SERVICE_NAME"
    echo -e "${GREEN}✅ Service stopped${NC}"
else
    echo -e "${YELLOW}Service was not running${NC}"
fi

# Step 3: Apply migrations
echo -e "${YELLOW}Step 3/4: Applying migrations...${NC}"
echo ""

# Show what will be applied
echo -e "${BLUE}Migration plan:${NC}"
flask db upgrade --sql | head -50

echo ""
read -p "Apply these migrations? (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
    echo -e "${RED}Migration cancelled${NC}"
    sudo systemctl start "$SERVICE_NAME"
    exit 1
fi

# Apply migrations
if flask db upgrade; then
    echo -e "${GREEN}✅ Migrations applied successfully${NC}"

    # Show new status
    echo -e "${BLUE}New migration status:${NC}"
    flask db current
else
    echo -e "${RED}❌ Migration failed!${NC}"
    echo -e "${YELLOW}Attempting to restore from backup...${NC}"

    # Find latest backup
    LATEST_BACKUP=$(ls -t /var/lib/crystalbudget/backups/budget_backup_*.db 2>/dev/null | head -1)
    if [ -n "$LATEST_BACKUP" ]; then
        cp "$LATEST_BACKUP" "$DB_PATH"
        echo -e "${GREEN}✅ Database restored from backup${NC}"
    else
        echo -e "${RED}❌ No backup found! Manual recovery required.${NC}"
    fi

    sudo systemctl start "$SERVICE_NAME"
    exit 1
fi

# Step 4: Restart the service
echo -e "${YELLOW}Step 4/4: Starting application...${NC}"
sudo systemctl start "$SERVICE_NAME"

# Wait for service to start
sleep 2

# Check if service started successfully
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo -e "${GREEN}✅ Service started successfully${NC}"

    # Check health endpoint
    echo -e "${YELLOW}Checking application health...${NC}"
    sleep 3

    if curl -f -s http://localhost:5030/healthz > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Application is healthy${NC}"
    else
        echo -e "${YELLOW}⚠️  Health check failed - check logs${NC}"
        echo -e "View logs: ${BLUE}sudo journalctl -u $SERVICE_NAME -f${NC}"
    fi
else
    echo -e "${RED}❌ Service failed to start!${NC}"
    echo -e "Check logs: ${BLUE}sudo journalctl -u $SERVICE_NAME -n 50${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Migration completed successfully!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Monitor logs: sudo journalctl -u $SERVICE_NAME -f"
echo "2. Test the application in browser"
echo "3. Check database: flask db current"
echo ""
echo -e "${YELLOW}If something went wrong:${NC}"
echo "1. Stop service: sudo systemctl stop $SERVICE_NAME"
echo "2. Restore backup: cp /var/lib/crystalbudget/backups/budget_backup_*.db $DB_PATH"
echo "3. Downgrade: flask db downgrade -1"
echo "4. Start service: sudo systemctl start $SERVICE_NAME"
