#!/bin/bash
# Test runner script for local development

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
TEST_DB="sqlite:///test_local.db"
SECRET_KEY="test-secret-key-local"
BASE_URL="http://localhost:5000"

echo -e "${YELLOW}🧪 CrystalBudget Test Suite${NC}"
echo "=================================="

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo -e "${YELLOW}⚠️  Activating virtual environment...${NC}"
    source .venv/bin/activate
fi

# Install test dependencies if needed
if ! pip show pytest &> /dev/null; then
    echo -e "${YELLOW}📦 Installing test dependencies...${NC}"
    pip install -r requirements-test.txt
fi

# Create clean test database
echo -e "${YELLOW}🗄️  Setting up test database...${NC}"
export BUDGET_DB="$TEST_DB"
export SECRET_KEY="$SECRET_KEY"

rm -f test_local.db

python -c "
from app import create_app
from app.core.extensions import db

app = create_app()
with app.app_context():
    db.create_all()
    print('✅ Test database initialized')
"

# Function to run test suite
run_test_suite() {
    local suite_name=$1
    local test_path=$2
    local extra_args=$3
    
    echo ""
    echo -e "${YELLOW}📋 Running $suite_name...${NC}"
    echo "-----------------------------------"
    
    if pytest "$test_path" -v --tb=short $extra_args; then
        echo -e "${GREEN}✅ $suite_name: PASSED${NC}"
        return 0
    else
        echo -e "${RED}❌ $suite_name: FAILED${NC}"
        return 1
    fi
}

# Parse command line arguments
SUITE="all"
VERBOSE=false
STOP_ON_FAIL=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --suite)
            SUITE="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --stop-on-fail)
            STOP_ON_FAIL=true
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --suite SUITE      Run specific test suite: api, e2e, smoke, all (default: all)"
            echo "  --verbose          Enable verbose output"
            echo "  --stop-on-fail     Stop on first failure"
            echo "  --help            Show this help message"
            echo ""
            echo "Test suites:"
            echo "  api               Run API tests only"
            echo "  e2e               Run E2E tests only (requires Chrome/Chromium)"
            echo "  smoke             Run smoke test validation"
            echo "  all               Run all automated tests"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Track results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_SUITES=()

# Run tests based on suite selection
case $SUITE in
    "api"|"all")
        TOTAL_TESTS=$((TOTAL_TESTS + 1))
        if run_test_suite "API Tests" "tests/api/" "--maxfail=5"; then
            PASSED_TESTS=$((PASSED_TESTS + 1))
        else
            FAILED_SUITES+=("API Tests")
            if [[ $STOP_ON_FAIL == true ]]; then exit 1; fi
        fi
        ;;
esac

case $SUITE in
    "e2e"|"all")
        TOTAL_TESTS=$((TOTAL_TESTS + 1))
        # Check if Chrome/Chromium is available for E2E tests
        if command -v google-chrome &> /dev/null || command -v chromium-browser &> /dev/null || command -v chromium &> /dev/null; then
            export BASE_URL="$BASE_URL"
            if run_test_suite "E2E Tests" "tests/e2e/" "--maxfail=3"; then
                PASSED_TESTS=$((PASSED_TESTS + 1))
            else
                FAILED_SUITES+=("E2E Tests")
                if [[ $STOP_ON_FAIL == true ]]; then exit 1; fi
            fi
        else
            echo -e "${YELLOW}⚠️  Skipping E2E tests - Chrome/Chromium not found${NC}"
            echo "   Install Chrome or Chromium to run E2E tests"
        fi
        ;;
esac

case $SUITE in
    "smoke"|"all")
        TOTAL_TESTS=$((TOTAL_TESTS + 1))
        echo ""
        echo -e "${YELLOW}📋 Running Smoke Test Validation...${NC}"
        echo "-----------------------------------"
        
        # Validate smoke test checklist exists and app starts
        if [[ -f "tests/smoke/manual_checklist.md" ]]; then
            python -c "
from app import create_app
import sys

try:
    app = create_app()
    with app.test_client() as client:
        # Test basic endpoints
        response = client.get('/healthz')
        assert response.status_code == 200, 'Health check failed'
        
        response = client.get('/login')  
        assert response.status_code == 200, 'Login page failed'
        
    print('✅ Smoke test framework validation: PASSED')
    print('📋 Manual checklist ready at: tests/smoke/manual_checklist.md')
    print('⏱️  Estimated time: 15 minutes')
except Exception as e:
    print(f'❌ Smoke test validation failed: {e}')
    sys.exit(1)
"
            if [[ $? -eq 0 ]]; then
                PASSED_TESTS=$((PASSED_TESTS + 1))
                echo -e "${GREEN}✅ Smoke Tests: READY${NC}"
            else
                FAILED_SUITES+=("Smoke Tests")
                echo -e "${RED}❌ Smoke Tests: FAILED${NC}"
                if [[ $STOP_ON_FAIL == true ]]; then exit 1; fi
            fi
        else
            FAILED_SUITES+=("Smoke Tests")
            echo -e "${RED}❌ Smoke test checklist not found${NC}"
            if [[ $STOP_ON_FAIL == true ]]; then exit 1; fi
        fi
        ;;
esac

# Final report
echo ""
echo "=================================="
echo -e "${YELLOW}📊 TEST SUMMARY${NC}"
echo "=================================="
echo "Total test suites: $TOTAL_TESTS"
echo "Passed: $PASSED_TESTS"
echo "Failed: $((TOTAL_TESTS - PASSED_TESTS))"

if [[ ${#FAILED_SUITES[@]} -eq 0 ]]; then
    echo -e "${GREEN}🎉 ALL TESTS PASSED!${NC}"
    echo ""
    echo -e "${GREEN}✅ Ready for deployment${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Run manual smoke tests (tests/smoke/manual_checklist.md)"
    echo "2. Deploy to staging/production"
    echo "3. Run post-deployment smoke tests"
    exit 0
else
    echo -e "${RED}❌ TESTS FAILED:${NC}"
    for suite in "${FAILED_SUITES[@]}"; do
        echo -e "${RED}   - $suite${NC}"
    done
    echo ""
    echo -e "${RED}🚫 DO NOT DEPLOY${NC}"
    echo ""
    echo "Fix failing tests before deployment"
    exit 1
fi