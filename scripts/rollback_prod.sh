#!/bin/bash
# Rollback script for production database
# This script helps rollback to a previous database state

set -e  # Exit on error

echo "🔄 CrystalBudget Production Rollback"
echo "===================================="
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

# Ensure we're in project root
cd "$PROJECT_ROOT"

# Check database path
if [ -z "$BUDGET_DB" ]; then
    export BUDGET_DB="sqlite:////opt/crystall-budget/instance/budget.db"
fi
DB_FILE=$(echo "$BUDGET_DB" | sed 's|sqlite:///||')

# List available backups
echo -e "${YELLOW}Available backups:${NC}"
if [ ! -d "$BACKUP_DIR" ]; then
    echo -e "${RED}No backups found in $BACKUP_DIR${NC}"
    exit 1
fi

ls -lht "$BACKUP_DIR"/*.db 2>/dev/null | awk '{print NR") " $9 " (" $6 " " $7 " " $8 ")"}'
echo ""

# Select backup
read -p "Enter backup number to restore (or 'q' to quit): " BACKUP_NUM
if [ "$BACKUP_NUM" = "q" ]; then
    echo "Rollback cancelled"
    exit 0
fi

BACKUP_FILE=$(ls -t "$BACKUP_DIR"/*.db | sed -n "${BACKUP_NUM}p")
if [ -z "$BACKUP_FILE" ]; then
    echo -e "${RED}Invalid backup number${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Selected backup:${NC} $BACKUP_FILE"
echo -e "${YELLOW}Current database:${NC} $DB_FILE"
echo ""
echo -e "${RED}WARNING: This will replace the current database!${NC}"
read -p "Are you sure? Type 'ROLLBACK' to confirm: " CONFIRM

if [ "$CONFIRM" != "ROLLBACK" ]; then
    echo "Rollback cancelled"
    exit 1
fi

# Stop service
echo ""
echo -e "${YELLOW}[1/4]${NC} Stopping application..."
if systemctl is-active --quiet crystalbudget; then
    sudo systemctl stop crystalbudget
    echo -e "${GREEN}✓ Application stopped${NC}"
else
    echo -e "${YELLOW}! Application not running${NC}"
fi

# Create emergency backup of current state
echo ""
echo -e "${YELLOW}[2/4]${NC} Creating emergency backup of current state..."
EMERGENCY_BACKUP="$BACKUP_DIR/emergency_$(date +%Y%m%d_%H%M%S).db"
cp "$DB_FILE" "$EMERGENCY_BACKUP"
echo -e "${GREEN}✓ Emergency backup: $EMERGENCY_BACKUP${NC}"

# Restore backup
echo ""
echo -e "${YELLOW}[3/4]${NC} Restoring backup..."
cp "$BACKUP_FILE" "$DB_FILE"
echo -e "${GREEN}✓ Database restored${NC}"

# Start service
echo ""
echo -e "${YELLOW}[4/4]${NC} Starting application..."
sudo systemctl start crystalbudget
sleep 2
if systemctl is-active --quiet crystalbudget; then
    echo -e "${GREEN}✓ Application started${NC}"
else
    echo -e "${RED}✗ Application failed to start${NC}"
    echo "Check logs: sudo journalctl -u crystalbudget -n 50"
    exit 1
fi

echo ""
echo "======================================"
echo -e "${GREEN}✓ Rollback completed successfully!${NC}"
echo ""
echo "Restored from: $BACKUP_FILE"
echo "Emergency backup: $EMERGENCY_BACKUP"
echo ""
echo "Check application: sudo journalctl -u crystalbudget -f"
echo ""
