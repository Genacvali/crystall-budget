#!/bin/bash
# Test migrations on local development database

set -e

# Configuration for LOCAL testing
LOCAL_DB="/opt/crystall-budget/instance/budget.db"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}🧪 Testing migrations locally${NC}"
echo "=============================="

cd /opt/crystalbudget/crystall-budget
source .venv/bin/activate

# Set database to local instance
export BUDGET_DB="sqlite:///$LOCAL_DB"
echo -e "Using database: ${GREEN}$LOCAL_DB${NC}"

# Check if database exists
if [ ! -f "$LOCAL_DB" ]; then
    echo -e "${YELLOW}⚠️  Local database not found. Creating...${NC}"
    mkdir -p "$(dirname $LOCAL_DB)"
    flask db upgrade
fi

# Show current status
echo ""
echo -e "${GREEN}Current migration status:${NC}"
flask db current

echo ""
echo -e "${GREEN}Migration history:${NC}"
flask db history | head -20

echo ""
echo -e "${YELLOW}To create a new migration:${NC}"
echo "  export BUDGET_DB=\"sqlite:///$LOCAL_DB\""
echo "  flask db migrate -m 'Description'"
echo ""
echo -e "${YELLOW}To apply migrations:${NC}"
echo "  export BUDGET_DB=\"sqlite:///$LOCAL_DB\""
echo "  flask db upgrade"
