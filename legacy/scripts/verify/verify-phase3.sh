#!/bin/bash
# Verification script for Phase 3: HTTPS/SSL Configuration
# This script checks that all Phase 3 requirements are met

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

echo -e "${BLUE}=== Phase 3: HTTPS/SSL Configuration Verification ===${NC}\n"

# Check 1: Required files exist
echo -e "${BLUE}Checking required files...${NC}"

if [ -f "cloud-run-python.yaml" ]; then
    print_result "PASS" "cloud-run-python.yaml exists"
else
    print_result "FAIL" "cloud-run-python.yaml missing"
fi

if [ -f "cloud-run-frontend.yaml" ]; then
    print_result "PASS" "cloud-run-frontend.yaml exists"
else
    print_result "FAIL" "cloud-run-frontend.yaml missing"
fi

if [ -f "scripts/setup/setup-https.sh" ]; then
    print_result "PASS" "scripts/setup/setup-https.sh exists"
    if [ -x "scripts/setup/setup-https.sh" ]; then
        print_result "PASS" "scripts/setup/setup-https.sh is executable"
    else
        print_result "FAIL" "scripts/setup/setup-https.sh is not executable"
    fi
else
    print_result "FAIL" "scripts/setup/setup-https.sh missing"
fi

if [ -f "docs/PHASE3_HTTPS_IMPLEMENTATION.md" ]; then
    print_result "PASS" "Phase 3 documentation exists"
else
    print_result "WARN" "Phase 3 documentation missing (optional)"
fi

# Check 2: Security headers in embed.py
echo -e "\n${BLUE}Checking security headers implementation...${NC}"

if grep -q "SecurityHeadersMiddleware" embed.py; then
    print_result "PASS" "SecurityHeadersMiddleware class found in embed.py"
else
    print_result "FAIL" "SecurityHeadersMiddleware not found in embed.py"
fi

if grep -q "X-Content-Type-Options" embed.py; then
    print_result "PASS" "X-Content-Type-Options header configured"
else
    print_result "FAIL" "X-Content-Type-Options header missing"
fi

if grep -q "X-Frame-Options" embed.py; then
    print_result "PASS" "X-Frame-Options header configured"
else
    print_result "FAIL" "X-Frame-Options header missing"
fi

if grep -q "Strict-Transport-Security" embed.py; then
    print_result "PASS" "Strict-Transport-Security (HSTS) header configured"
else
    print_result "FAIL" "Strict-Transport-Security header missing"
fi

if grep -q "X-Forwarded-Proto" embed.py; then
    print_result "PASS" "X-Forwarded-Proto header check implemented"
else
    print_result "WARN" "X-Forwarded-Proto header check not found (may be handled differently)"
fi

# Check 3: Environment variables in embed.py
echo -e "\n${BLUE}Checking environment variable usage...${NC}"

if grep -q "PYTHON_API_BASE_URL" embed.py; then
    print_result "PASS" "PYTHON_API_BASE_URL environment variable used"
else
    print_result "FAIL" "PYTHON_API_BASE_URL not found in embed.py"
fi

if grep -q "CORS_ORIGINS" embed.py; then
    print_result "PASS" "CORS_ORIGINS environment variable used"
else
    print_result "FAIL" "CORS_ORIGINS not found in embed.py"
fi

# Check 4: Cloud Run YAML file validation
echo -e "\n${BLUE}Validating Cloud Run YAML files...${NC}"

if command -v yamllint &> /dev/null; then
    if yamllint cloud-run-python.yaml &> /dev/null; then
        print_result "PASS" "cloud-run-python.yaml is valid YAML"
    else
        print_result "FAIL" "cloud-run-python.yaml has YAML syntax errors"
        yamllint cloud-run-python.yaml 2>&1 | head -5
    fi
    
    if yamllint cloud-run-frontend.yaml &> /dev/null; then
        print_result "PASS" "cloud-run-frontend.yaml is valid YAML"
    else
        print_result "FAIL" "cloud-run-frontend.yaml has YAML syntax errors"
        yamllint cloud-run-frontend.yaml 2>&1 | head -5
    fi
else
    print_result "WARN" "yamllint not installed, skipping YAML validation"
fi

# Check 5: Cloud Run YAML content checks
echo -e "\n${BLUE}Checking Cloud Run YAML content...${NC}"

if grep -q "PYTHON_API_BASE_URL" cloud-run-python.yaml; then
    print_result "PASS" "cloud-run-python.yaml includes PYTHON_API_BASE_URL"
else
    print_result "WARN" "cloud-run-python.yaml doesn't include PYTHON_API_BASE_URL (may be set elsewhere)"
fi

if grep -q "CORS_ORIGINS" cloud-run-python.yaml; then
    print_result "PASS" "cloud-run-python.yaml includes CORS_ORIGINS"
else
    print_result "WARN" "cloud-run-python.yaml doesn't include CORS_ORIGINS (may be set elsewhere)"
fi

if grep -q "health" cloud-run-python.yaml; then
    print_result "PASS" "cloud-run-python.yaml includes health check configuration"
else
    print_result "WARN" "cloud-run-python.yaml doesn't include health check configuration"
fi

if grep -q "NEXT_PUBLIC_EMBEDDING_SERVICE_URL" cloud-run-frontend.yaml; then
    print_result "PASS" "cloud-run-frontend.yaml includes NEXT_PUBLIC_EMBEDDING_SERVICE_URL"
else
    print_result "FAIL" "cloud-run-frontend.yaml missing NEXT_PUBLIC_EMBEDDING_SERVICE_URL"
fi

if grep -q "NEXT_PUBLIC_FRONTEND_URL" cloud-run-frontend.yaml; then
    print_result "PASS" "cloud-run-frontend.yaml includes NEXT_PUBLIC_FRONTEND_URL"
else
    print_result "FAIL" "cloud-run-frontend.yaml missing NEXT_PUBLIC_FRONTEND_URL"
fi

# Check 6: Docker Compose HTTPS comments
echo -e "\n${BLUE}Checking docker-compose.yml HTTPS configuration...${NC}"

if grep -q "HTTPS" docker-compose.yml; then
    print_result "PASS" "docker-compose.yml includes HTTPS configuration comments"
else
    print_result "WARN" "docker-compose.yml doesn't include HTTPS configuration comments"
fi

# Check 7: Setup script validation
echo -e "\n${BLUE}Checking setup-https.sh script...${NC}"

if [ -f "scripts/setup/setup-https.sh" ]; then
    # Check for key commands in script
    if grep -q "gcloud compute addresses" scripts/setup/setup-https.sh; then
        print_result "PASS" "setup-https.sh includes static IP reservation"
    else
        print_result "FAIL" "setup-https.sh missing static IP reservation"
    fi
    
    if grep -q "ssl-certificates" scripts/setup/setup-https.sh; then
        print_result "PASS" "setup-https.sh includes SSL certificate creation"
    else
        print_result "FAIL" "setup-https.sh missing SSL certificate creation"
    fi
    
    if grep -q "network-endpoint-groups" scripts/setup/setup-https.sh; then
        print_result "PASS" "setup-https.sh includes NEG creation"
    else
        print_result "FAIL" "setup-https.sh missing NEG creation"
    fi
    
    if grep -q "forwarding-rules" scripts/setup/setup-https.sh; then
        print_result "PASS" "setup-https.sh includes forwarding rule creation"
    else
        print_result "FAIL" "setup-https.sh missing forwarding rule creation"
    fi
fi

# Check 8: Documentation
echo -e "\n${BLUE}Checking documentation...${NC}"

if [ -f "docs/HTTPS_SETUP.md" ]; then
    print_result "PASS" "HTTPS_SETUP.md documentation exists"
else
    print_result "WARN" "HTTPS_SETUP.md missing"
fi

if [ -f "docs/ENVIRONMENT_VARIABLES.md" ]; then
    if grep -q "HTTPS" docs/ENVIRONMENT_VARIABLES.md; then
        print_result "PASS" "ENVIRONMENT_VARIABLES.md includes HTTPS configuration"
    else
        print_result "WARN" "ENVIRONMENT_VARIABLES.md doesn't mention HTTPS"
    fi
fi

# Summary
echo -e "\n${BLUE}=== Verification Summary ===${NC}"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
echo -e "${RED}Failed: $FAILED${NC}"

if [ $FAILED -eq 0 ]; then
    echo -e "\n${GREEN}✓ Phase 3 verification PASSED!${NC}"
    exit 0
else
    echo -e "\n${RED}✗ Phase 3 verification FAILED. Please fix the issues above.${NC}"
    exit 1
fi

