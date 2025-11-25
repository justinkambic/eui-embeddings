#!/bin/bash
# Verification script for Phase 4: API Key Authentication
# This script checks that all Phase 4 requirements are met

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0
WARNINGS=0

# Function to print test result
print_result() {
    local status=$1
    local message=$2
    
    if [ "$status" == "PASS" ]; then
        echo -e "${GREEN}✓${NC} $message"
        PASSED=$((PASSED + 1))
    elif [ "$status" == "FAIL" ]; then
        echo -e "${RED}✗${NC} $message"
        FAILED=$((FAILED + 1))
    elif [ "$status" == "WARN" ]; then
        echo -e "${YELLOW}⚠${NC} $message"
        WARNINGS=$((WARNINGS + 1))
    fi
}

echo -e "${BLUE}=== Phase 4: API Key Authentication Verification ===${NC}\n"

# Check 1: Required files exist
echo -e "${BLUE}Checking required files...${NC}"

if [ -f "scripts/manage/manage-api-keys.sh" ]; then
    print_result "PASS" "scripts/manage/manage-api-keys.sh exists"
    if [ -x "scripts/manage/manage-api-keys.sh" ]; then
        print_result "PASS" "scripts/manage/manage-api-keys.sh is executable"
    else
        print_result "FAIL" "scripts/manage/manage-api-keys.sh is not executable"
    fi
else
    print_result "FAIL" "scripts/manage/manage-api-keys.sh missing"
fi

if [ -f "docs/API_KEY_ROTATION.md" ]; then
    print_result "PASS" "API key rotation documentation exists"
else
    print_result "FAIL" "docs/API_KEY_ROTATION.md missing"
fi

# Check 2: Python API authentication implementation
echo -e "\n${BLUE}Checking Python API authentication...${NC}"

if grep -q "verify_api_key" embed.py; then
    print_result "PASS" "verify_api_key function found in embed.py"
else
    print_result "FAIL" "verify_api_key function not found in embed.py"
fi

if grep -q "API_KEY_HEADER" embed.py; then
    print_result "PASS" "API_KEY_HEADER environment variable used"
else
    print_result "FAIL" "API_KEY_HEADER not found in embed.py"
fi

if grep -q "API_KEYS_SECRET_NAME" embed.py; then
    print_result "PASS" "API_KEYS_SECRET_NAME environment variable used"
else
    print_result "FAIL" "API_KEYS_SECRET_NAME not found in embed.py"
fi

if grep -q "load_api_keys" embed.py; then
    print_result "PASS" "load_api_keys function found"
else
    print_result "FAIL" "load_api_keys function not found"
fi

if grep -q "secretmanager" embed.py; then
    print_result "PASS" "Google Secret Manager integration found"
else
    print_result "WARN" "Google Secret Manager integration not found (may use env vars only)"
fi

# Check health endpoint is excluded from authentication
if grep -q "@app.get(\"/health\")" embed.py || grep -q "def health_check" embed.py; then
    # Check if health endpoint has dependencies (should not have verify_api_key)
    if grep -A 5 "def health_check" embed.py | grep -q "verify_api_key"; then
        print_result "FAIL" "Health endpoint requires authentication (should be excluded)"
    else
        print_result "PASS" "Health endpoint excluded from authentication"
    fi
else
    print_result "WARN" "Health endpoint not found"
fi

# Check 3: Frontend authentication
echo -e "\n${BLUE}Checking frontend authentication...${NC}"

if grep -q "FRONTEND_API_KEY" frontend/pages/api/search.ts; then
    print_result "PASS" "search.ts includes FRONTEND_API_KEY"
else
    print_result "FAIL" "search.ts missing FRONTEND_API_KEY"
fi

if grep -q "X-API-Key" frontend/pages/api/search.ts; then
    print_result "PASS" "search.ts includes X-API-Key header"
else
    print_result "FAIL" "search.ts missing X-API-Key header"
fi

# Check admin endpoints have authentication
if [ -f "frontend/lib/auth.ts" ]; then
    print_result "PASS" "frontend/lib/auth.ts exists"
    
    if grep -q "verifyAdminAuth" frontend/lib/auth.ts; then
        print_result "PASS" "verifyAdminAuth function found"
    else
        print_result "FAIL" "verifyAdminAuth function not found"
    fi
else
    print_result "WARN" "frontend/lib/auth.ts not found (admin auth may not be implemented)"
fi

if grep -q "verifyAdminAuth" frontend/pages/api/batchIndexImages.ts 2>/dev/null; then
    print_result "PASS" "batchIndexImages.ts includes admin authentication"
else
    print_result "WARN" "batchIndexImages.ts missing admin authentication (optional)"
fi

if grep -q "verifyAdminAuth" frontend/pages/api/batchIndexSVG.ts 2>/dev/null; then
    print_result "PASS" "batchIndexSVG.ts includes admin authentication"
else
    print_result "WARN" "batchIndexSVG.ts missing admin authentication (optional)"
fi

if grep -q "verifyAdminAuth" frontend/pages/api/batchIndexText.ts 2>/dev/null; then
    print_result "PASS" "batchIndexText.ts includes admin authentication"
else
    print_result "WARN" "batchIndexText.ts missing admin authentication (optional)"
fi

# Check 4: API key management script
echo -e "\n${BLUE}Checking API key management script...${NC}"

if [ -f "scripts/manage/manage-api-keys.sh" ]; then
    # Check for key functions
    if grep -q "generate_api_key" scripts/manage/manage-api-keys.sh; then
        print_result "PASS" "manage-api-keys.sh includes key generation"
    else
        print_result "FAIL" "manage-api-keys.sh missing key generation"
    fi
    
    if grep -q "list_keys\|list" scripts/manage/manage-api-keys.sh; then
        print_result "PASS" "manage-api-keys.sh includes list functionality"
    else
        print_result "FAIL" "manage-api-keys.sh missing list functionality"
    fi
    
    if grep -q "add_key\|add" scripts/manage/manage-api-keys.sh; then
        print_result "PASS" "manage-api-keys.sh includes add functionality"
    else
        print_result "FAIL" "manage-api-keys.sh missing add functionality"
    fi
    
    if grep -q "remove_key\|remove" scripts/manage/manage-api-keys.sh; then
        print_result "PASS" "manage-api-keys.sh includes remove functionality"
    else
        print_result "FAIL" "manage-api-keys.sh missing remove functionality"
    fi
    
    if grep -q "gcloud secrets" scripts/manage/manage-api-keys.sh; then
        print_result "PASS" "manage-api-keys.sh uses gcloud secrets"
    else
        print_result "FAIL" "manage-api-keys.sh missing gcloud secrets integration"
    fi
fi

# Check 5: Environment variable documentation
echo -e "\n${BLUE}Checking documentation...${NC}"

if grep -q "API_KEY" docs/ENVIRONMENT_VARIABLES.md; then
    print_result "PASS" "ENVIRONMENT_VARIABLES.md documents API key variables"
else
    print_result "WARN" "ENVIRONMENT_VARIABLES.md doesn't mention API keys"
fi

if [ -f "docs/API_KEY_ROTATION.md" ]; then
    if grep -q "rotation\|rotate" docs/API_KEY_ROTATION.md -i; then
        print_result "PASS" "API_KEY_ROTATION.md includes rotation process"
    else
        print_result "WARN" "API_KEY_ROTATION.md missing rotation details"
    fi
fi

# Check 6: Cloud Run configuration
echo -e "\n${BLUE}Checking Cloud Run configuration...${NC}"

if grep -q "API_KEYS_SECRET_NAME" cloud-run-python.yaml 2>/dev/null; then
    print_result "PASS" "cloud-run-python.yaml includes API_KEYS_SECRET_NAME"
else
    print_result "WARN" "cloud-run-python.yaml doesn't include API_KEYS_SECRET_NAME"
fi

if grep -q "FRONTEND_API_KEY" cloud-run-frontend.yaml 2>/dev/null; then
    print_result "PASS" "cloud-run-frontend.yaml includes FRONTEND_API_KEY"
else
    print_result "WARN" "cloud-run-frontend.yaml doesn't include FRONTEND_API_KEY"
fi

# Summary
echo -e "\n${BLUE}=== Verification Summary ===${NC}"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
echo -e "${RED}Failed: $FAILED${NC}"

if [ $FAILED -eq 0 ]; then
    echo -e "\n${GREEN}✓ Phase 4 verification PASSED!${NC}"
    exit 0
else
    echo -e "\n${RED}✗ Phase 4 verification FAILED. Please fix the issues above.${NC}"
    exit 1
fi

