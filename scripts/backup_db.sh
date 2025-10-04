#!/bin/bash
# Database backup script for CrystalBudget

set -e

# Configuration
PROD_PATH="/opt/crystall-budget"
DB_PATH="${PROD_PATH}/instance/budget.db"
BACKUP_DIR="${PROD_PATH}/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/budget_backup_${TIMESTAMP}.db"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🗄️  CrystalBudget Database Backup${NC}"
echo "=================================="

# Create backup directory if it doesn't exist
if [ ! -d "$BACKUP_DIR" ]; then
    echo -e "${YELLOW}Creating backup directory...${NC}"
    mkdir -p "$BACKUP_DIR"
fi

# Check if database exists
if [ ! -f "$DB_PATH" ]; then
    echo -e "${RED}❌ Database not found at: $DB_PATH${NC}"
    exit 1
fi

# Get database size
DB_SIZE=$(du -h "$DB_PATH" | cut -f1)
echo -e "Database size: ${GREEN}$DB_SIZE${NC}"

# Create backup
echo -e "${YELLOW}Creating backup...${NC}"
cp "$DB_PATH" "$BACKUP_FILE"

if [ -f "$BACKUP_FILE" ]; then
    echo -e "${GREEN}✅ Backup created successfully!${NC}"
    echo -e "Backup location: ${GREEN}$BACKUP_FILE${NC}"

    # Verify backup integrity
    if command -v sqlite3 &> /dev/null; then
        echo -e "${YELLOW}Verifying backup integrity...${NC}"
        if sqlite3 "$BACKUP_FILE" "PRAGMA integrity_check;" | grep -q "ok"; then
            echo -e "${GREEN}✅ Backup integrity verified${NC}"
        else
            echo -e "${RED}⚠️  Warning: Backup integrity check failed${NC}"
        fi
    fi

    # Show backup info
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo -e "Backup size: ${GREEN}$BACKUP_SIZE${NC}"

    # Cleanup old backups (keep last 10)
    echo -e "${YELLOW}Cleaning up old backups...${NC}"
    cd "$BACKUP_DIR"
    ls -t budget_backup_*.db | tail -n +11 | xargs -r rm --
    BACKUP_COUNT=$(ls -1 budget_backup_*.db 2>/dev/null | wc -l)
    echo -e "${GREEN}Total backups: $BACKUP_COUNT${NC}"
else
    echo -e "${RED}❌ Backup failed!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Backup complete!${NC}"
