#!/bin/bash
# URGENT: Restore preprod after accidental deletion
# This script will copy all files from dev to preprod

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

DEV_PATH="/opt/crystall-budget"
PREPROD_PATH="/opt/preprod/crystall-budget"

echo -e "${RED}🚨 URGENT RESTORE: Preprod files${NC}"
echo "=================================="
echo ""

# Create directory structure
echo -e "${YELLOW}Creating directories...${NC}"
sudo mkdir -p "$PREPROD_PATH"
sudo mkdir -p "$PREPROD_PATH/instance"
sudo mkdir -p "$PREPROD_PATH/static/avatars"
sudo mkdir -p "$PREPROD_PATH/logs"

# Copy ALL files (no --delete flag!)
echo -e "${YELLOW}Copying files from dev...${NC}"
sudo rsync -av \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.venv' \
    --exclude='instance/*.db' \
    --exclude='instance/*.db-journal' \
    "$DEV_PATH/" "$PREPROD_PATH/"

# Set permissions
echo -e "${YELLOW}Setting permissions...${NC}"
sudo chown -R crystal:crystal "$PREPROD_PATH"
sudo chmod -R 755 "$PREPROD_PATH"
sudo chmod -R 775 "$PREPROD_PATH/instance"
sudo chmod -R 775 "$PREPROD_PATH/static/avatars"
sudo chmod -R 775 "$PREPROD_PATH/logs"

# Create virtualenv
echo -e "${YELLOW}Creating virtualenv...${NC}"
cd "$PREPROD_PATH"
sudo rm -rf .venv
python3 -m venv .venv
sudo chown -R crystal:crystal .venv

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
sudo -u crystal .venv/bin/pip install --quiet --upgrade pip
sudo -u crystal .venv/bin/pip install --quiet -r requirements.txt

echo -e "${GREEN}✅ Files restored!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Initialize database: cd $PREPROD_PATH && export BUDGET_DB='sqlite:///instance/budget.db' && .venv/bin/flask db upgrade"
echo "2. Restart service: sudo systemctl restart crystalbudget_preprod"
