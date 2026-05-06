#!/bin/bash
# Verification script for Phase 5: Rate Limiting
# This script checks that all Phase 5 requirements are met

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

echo -e "${BLUE}=== Phase 5: Rate Limiting Verification ===${NC}\n"

# Check 1: Required files and dependencies
echo -e "${BLUE}Checking dependencies...${NC}"

if grep -q "slowapi" requirements.txt; then
    print_result "PASS" "slowapi found in requirements.txt"
else
    print_result "FAIL" "slowapi missing from requirements.txt"
fi

if grep -q "express-rate-limit" token_renderer/package.json 2>/dev/null; then
    print_result "PASS" "express-rate-limit found in token_renderer/package.json"
else
    print_result "FAIL" "express-rate-limit missing from token_renderer/package.json"
fi

# Check 2: Python API rate limiting implementation
echo -e "\n${BLUE}Checking Python API rate limiting...${NC}"

if grep -q "from slowapi import" embed.py; then
    print_result "PASS" "slowapi imported in embed.py"
else
    print_result "FAIL" "slowapi not imported in embed.py"
fi

if grep -q "Limiter" embed.py; then
    print_result "PASS" "Limiter class found in embed.py"
else
    print_result "FAIL" "Limiter class not found in embed.py"
fi

if grep -q "RATE_LIMIT_PER_MINUTE" embed.py; then
    print_result "PASS" "RATE_LIMIT_PER_MINUTE environment variable used"
else
    print_result "FAIL" "RATE_LIMIT_PER_MINUTE not found in embed.py"
fi

if grep -q "RATE_LIMIT_PER_HOUR" embed.py; then
    print_result "PASS" "RATE_LIMIT_PER_HOUR environment variable used"
else
    print_result "FAIL" "RATE_LIMIT_PER_HOUR not found in embed.py"
fi

if grep -q "@limiter.limit" embed.py; then
    print_result "PASS" "Rate limit decorators found on endpoints"
else
    print_result "FAIL" "Rate limit decorators not found on endpoints"
fi

if grep -q "get_rate_limit_key" embed.py; then
    print_result "PASS" "get_rate_limit_key function found (tracks by API key)"
else
    print_result "FAIL" "get_rate_limit_key function not found"
fi

# Check per-endpoint rate limits
if grep -q 'limiter.limit("30/minute")' embed.py || grep -q "30/minute" embed.py; then
    print_result "PASS" "Search endpoint has stricter rate limit (30/min)"
else
    print_result "WARN" "Search endpoint rate limit not found or not stricter"
fi

if grep -q "X-RateLimit" embed.py; then
    print_result "PASS" "Rate limit headers configured"
else
    print_result "WARN" "Rate limit headers not explicitly configured (slowapi may add them)"
fi

# Check 3: Frontend rate limiting
echo -e "\n${BLUE}Checking frontend rate limiting...${NC}"

if [ -f "frontend/lib/rateLimit.ts" ]; then
    print_result "PASS" "frontend/lib/rateLimit.ts exists"
    
    if grep -q "checkRateLimit" frontend/lib/rateLimit.ts; then
        print_result "PASS" "checkRateLimit function found"
    else
        print_result "FAIL" "checkRateLimit function not found"
    fi
    
    if grep -q "getClientIP" frontend/lib/rateLimit.ts; then
        print_result "PASS" "getClientIP function found"
    else
        print_result "FAIL" "getClientIP function not found"
    fi
else
    print_result "FAIL" "frontend/lib/rateLimit.ts missing"
fi

if grep -q "rateLimit" frontend/pages/api/batchIndexImages.ts 2>/dev/null; then
    print_result "PASS" "batchIndexImages.ts includes rate limiting"
else
    print_result "FAIL" "batchIndexImages.ts missing rate limiting"
fi

if grep -q "rateLimit" frontend/pages/api/batchIndexSVG.ts 2>/dev/null; then
    print_result "PASS" "batchIndexSVG.ts includes rate limiting"
else
    print_result "FAIL" "batchIndexSVG.ts missing rate limiting"
fi

if grep -q "rateLimit" frontend/pages/api/batchIndexText.ts 2>/dev/null; then
    print_result "PASS" "batchIndexText.ts includes rate limiting"
else
    print_result "FAIL" "batchIndexText.ts missing rate limiting"
fi

if grep -q "X-RateLimit" frontend/pages/api/batchIndexImages.ts 2>/dev/null; then
    print_result "PASS" "Rate limit headers added to admin endpoints"
else
    print_result "WARN" "Rate limit headers not found in admin endpoints"
fi

# Check 4: Token renderer rate limiting
echo -e "\n${BLUE}Checking token renderer rate limiting...${NC}"

if grep -q "express-rate-limit" token_renderer/server.js 2>/dev/null; then
    print_result "PASS" "express-rate-limit used in token_renderer/server.js"
else
    print_result "FAIL" "express-rate-limit not found in token_renderer/server.js"
fi

if grep -q "rateLimit" token_renderer/server.js 2>/dev/null; then
    print_result "PASS" "Rate limiting middleware configured in token renderer"
else
    print_result "FAIL" "Rate limiting middleware not found in token renderer"
fi

if grep -q "TOKEN_RENDERER_RATE_LIMIT" token_renderer/server.js 2>/dev/null; then
    print_result "PASS" "Token renderer rate limit configurable via env var"
else
    print_result "WARN" "Token renderer rate limit not configurable via env var"
fi

# Check 5: Environment variable documentation
echo -e "\n${BLUE}Checking documentation...${NC}"

if grep -q "RATE_LIMIT" docs/ENVIRONMENT_VARIABLES.md 2>/dev/null; then
    print_result "PASS" "ENVIRONMENT_VARIABLES.md documents rate limit variables"
else
    print_result "WARN" "ENVIRONMENT_VARIABLES.md doesn't mention rate limits"
fi

# Check 6: Cloud Run configuration
echo -e "\n${BLUE}Checking Cloud Run configuration...${NC}"

if grep -q "RATE_LIMIT" cloud-run-python.yaml 2>/dev/null; then
    print_result "PASS" "cloud-run-python.yaml includes rate limit configuration"
else
    print_result "WARN" "cloud-run-python.yaml doesn't include rate limit configuration"
fi

# Summary
echo -e "\n${BLUE}=== Verification Summary ===${NC}"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
echo -e "${RED}Failed: $FAILED${NC}"

if [ $FAILED -eq 0 ]; then
    echo -e "\n${GREEN}✓ Phase 5 verification PASSED!${NC}"
    exit 0
else
    echo -e "\n${RED}✗ Phase 5 verification FAILED. Please fix the issues above.${NC}"
    exit 1
fi


