#!/bin/bash
# Complete production setup script

set -e

echo "🚀 CrystalBudget Production Setup"
echo "=================================="
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Step 1: Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

echo -e "${YELLOW}[1/8]${NC} Checking/creating crystal user..."
if ! id -u crystal &>/dev/null; then
    useradd -r -s /bin/bash -d /opt/crystalbudget crystal
    echo -e "${GREEN}✓ Created crystal user${NC}"
else
    echo -e "${GREEN}✓ User crystal exists${NC}"
fi

echo ""
echo -e "${YELLOW}[2/8]${NC} Creating directories..."
mkdir -p /var/lib/crystalbudget
chown -R crystal:crystal /var/lib/crystalbudget
chmod 755 /var/lib/crystalbudget

mkdir -p /opt/crystalbudget/crystall-budget/backups
chown -R crystal:crystal /opt/crystalbudget
chmod 755 /opt/crystalbudget

echo -e "${GREEN}✓ Directories created${NC}"

echo ""
echo -e "${YELLOW}[3/8]${NC} Checking virtual environment..."
if [ ! -d "/opt/crystalbudget/venv" ]; then
    echo "Creating venv..."
    su - crystal -c "cd /opt/crystalbudget/crystall-budget && python3 -m venv /opt/crystalbudget/venv"
    su - crystal -c "/opt/crystalbudget/venv/bin/pip install -r /opt/crystalbudget/crystall-budget/requirements.txt"
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment exists${NC}"
fi

echo ""
echo -e "${YELLOW}[4/8]${NC} Installing gunicorn..."
su - crystal -c "/opt/crystalbudget/venv/bin/pip install gunicorn" || true
echo -e "${GREEN}✓ Gunicorn installed${NC}"

echo ""
echo -e "${YELLOW}[5/8]${NC} Checking database..."
export BUDGET_DB="sqlite:////var/lib/crystalbudget/budget.db"
DB_FILE="/var/lib/crystalbudget/budget.db"

if [ -f "$DB_FILE" ]; then
    echo "Database exists, creating backup..."
    BACKUP_FILE="/var/lib/crystalbudget/budget_backup_$(date +%Y%m%d_%H%M%S).db"
    cp "$DB_FILE" "$BACKUP_FILE"
    echo -e "${GREEN}✓ Backup: $BACKUP_FILE${NC}"
else
    echo "Database doesn't exist, will create fresh one"
fi

echo ""
echo -e "${YELLOW}[6/8]${NC} Running migrations as crystal user..."
cd /opt/crystalbudget/crystall-budget
su - crystal -c "cd /opt/crystalbudget/crystall-budget && export BUDGET_DB='sqlite:////var/lib/crystalbudget/budget.db' && /opt/crystalbudget/venv/bin/flask db upgrade"
echo -e "${GREEN}✓ Migrations applied${NC}"

echo ""
echo -e "${YELLOW}[7/8]${NC} Installing systemd service..."
cp /opt/crystalbudget/crystall-budget/crystalbudget.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable crystalbudget
echo -e "${GREEN}✓ Service installed${NC}"

echo ""
echo -e "${YELLOW}[8/8]${NC} Starting service..."
systemctl restart crystalbudget
sleep 2

if systemctl is-active --quiet crystalbudget; then
    echo -e "${GREEN}✓ Service started successfully${NC}"
else
    echo -e "${RED}✗ Service failed to start${NC}"
    echo "Check logs: journalctl -u crystalbudget -n 50"
    exit 1
fi

echo ""
echo "=================================="
echo -e "${GREEN}✓ Production setup completed!${NC}"
echo ""
echo "Database: $DB_FILE"
echo "User: crystal"
echo "Service: crystalbudget"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status crystalbudget"
echo "  sudo systemctl restart crystalbudget"
echo "  sudo journalctl -u crystalbudget -f"
echo ""
