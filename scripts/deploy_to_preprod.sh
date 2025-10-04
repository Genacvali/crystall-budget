#!/bin/bash
# Deploy CrystalBudget from dev to preprod
# Run this on the production server where both environments exist

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEV_PATH="/opt/crystall-budget"
PREPROD_PATH="/opt/preprod/crystall-budget"
PREPROD_USER="crystal"
PREPROD_GROUP="crystal"

echo -e "${YELLOW}🚀 Deploying CrystalBudget to Preprod${NC}"
echo "======================================"
echo ""
echo -e "From: ${GREEN}$DEV_PATH${NC}"
echo -e "To:   ${GREEN}$PREPROD_PATH${NC}"
echo ""

# Check if dev directory exists
if [ ! -d "$DEV_PATH" ]; then
    echo -e "${RED}❌ Dev directory not found: $DEV_PATH${NC}"
    exit 1
fi

# Create preprod directory structure if it doesn't exist
echo -e "${YELLOW}Step 1: Creating preprod directory structure...${NC}"
sudo mkdir -p "$PREPROD_PATH"
sudo mkdir -p "$PREPROD_PATH/instance"
sudo mkdir -p "$PREPROD_PATH/static/avatars"
sudo mkdir -p "$PREPROD_PATH/logs"
echo -e "${GREEN}✅ Directories created${NC}"

# Sync files from dev to preprod
echo -e "${YELLOW}Step 2: Syncing files...${NC}"
sudo rsync -av --delete \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.venv' \
    --exclude='instance/*.db' \
    --exclude='instance/*.db-journal' \
    --exclude='logs/*.log' \
    --exclude='static/avatars/*' \
    --exclude='.pytest_cache' \
    --exclude='node_modules' \
    "$DEV_PATH/" "$PREPROD_PATH/"

echo -e "${GREEN}✅ Files synced${NC}"

# Set proper ownership
echo -e "${YELLOW}Step 3: Setting permissions...${NC}"
sudo chown -R $PREPROD_USER:$PREPROD_GROUP "$PREPROD_PATH"
sudo chmod -R 755 "$PREPROD_PATH"
sudo chmod -R 775 "$PREPROD_PATH/instance"
sudo chmod -R 775 "$PREPROD_PATH/static/avatars"
sudo chmod -R 775 "$PREPROD_PATH/logs"
echo -e "${GREEN}✅ Permissions set${NC}"

# Create/activate virtual environment
echo -e "${YELLOW}Step 4: Setting up virtual environment...${NC}"
if [ ! -d "$PREPROD_PATH/.venv" ]; then
    echo "Creating new virtual environment..."
    cd "$PREPROD_PATH"
    sudo -u $PREPROD_USER python3 -m venv .venv

    # Upgrade pip
    echo "Upgrading pip..."
    sudo -u $PREPROD_USER .venv/bin/python -m pip install --upgrade pip
fi

# Verify virtualenv exists
if [ ! -f "$PREPROD_PATH/.venv/bin/pip" ]; then
    echo -e "${RED}❌ Failed to create virtualenv!${NC}"
    echo "Trying alternative method..."

    # Remove broken venv
    sudo rm -rf "$PREPROD_PATH/.venv"

    # Create as root and chown
    cd "$PREPROD_PATH"
    python3 -m venv .venv
    sudo chown -R $PREPROD_USER:$PREPROD_GROUP .venv

    if [ ! -f "$PREPROD_PATH/.venv/bin/pip" ]; then
        echo -e "${RED}❌ Virtualenv creation failed!${NC}"
        exit 1
    fi
fi

echo "Installing dependencies..."
cd "$PREPROD_PATH"
sudo -u $PREPROD_USER .venv/bin/pip install --quiet -r requirements.txt
echo -e "${GREEN}✅ Virtual environment ready${NC}"

# Initialize database if needed
echo -e "${YELLOW}Step 5: Database setup...${NC}"
if [ ! -f "$PREPROD_PATH/instance/budget.db" ]; then
    echo "Creating new database..."
    cd "$PREPROD_PATH"
    export BUDGET_DB="sqlite:///$PREPROD_PATH/instance/budget.db"
    sudo -u $PREPROD_USER "$PREPROD_PATH/.venv/bin/flask" db upgrade
    echo -e "${GREEN}✅ Database created${NC}"
else
    echo -e "${BLUE}ℹ Database already exists, skipping${NC}"
    read -p "Apply migrations? (yes/no): " -r
    if [[ $REPLY =~ ^[Yy]es$ ]]; then
        cd "$PREPROD_PATH"
        export BUDGET_DB="sqlite:///$PREPROD_PATH/instance/budget.db"
        sudo -u $PREPROD_USER "$PREPROD_PATH/.venv/bin/flask" db upgrade
        echo -e "${GREEN}✅ Migrations applied${NC}"
    fi
fi

# Restart preprod service
echo -e "${YELLOW}Step 6: Restarting preprod service...${NC}"
if sudo systemctl is-active --quiet crystalbudget_preprod; then
    sudo systemctl restart crystalbudget_preprod
else
    sudo systemctl start crystalbudget_preprod
fi

# Wait for service to start
sleep 3

# Check service status
if sudo systemctl is-active --quiet crystalbudget_preprod; then
    echo -e "${GREEN}✅ Service started successfully${NC}"

    # Show service info
    echo ""
    echo -e "${BLUE}Service Status:${NC}"
    sudo systemctl status crystalbudget_preprod --no-pager | head -10

    # Try to check health endpoint (adjust port if needed)
    echo ""
    echo -e "${YELLOW}Checking health endpoint...${NC}"
    sleep 2
    if curl -f -s http://localhost:5001/healthz > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Application is healthy${NC}"
    else
        echo -e "${YELLOW}⚠️  Health check failed - check logs${NC}"
    fi
else
    echo -e "${RED}❌ Service failed to start!${NC}"
    echo -e "Check logs: ${BLUE}sudo journalctl -u crystalbudget_preprod -n 50${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Monitor logs: sudo journalctl -u crystalbudget_preprod -f"
echo "2. Test the application in browser"
echo "3. Check processes: ps aux | grep python | grep preprod"
echo ""
echo -e "${YELLOW}If something went wrong:${NC}"
echo "1. View logs: sudo journalctl -u crystalbudget_preprod -n 100"
echo "2. Check status: sudo systemctl status crystalbudget_preprod"
echo "3. Restart: sudo systemctl restart crystalbudget_preprod"
