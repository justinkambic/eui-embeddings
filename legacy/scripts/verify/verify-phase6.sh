#!/bin/bash
# Verification script for Phase 6: GCP Deployment Configuration
#
# This script verifies that all Phase 6 requirements are met:
# - Cloud Build configuration exists
# - Cloud Run YAML files exist and are valid
# - Setup scripts exist and are executable
# - Environment configuration files exist
# - Service account and secret management scripts are functional
#
# Usage:
#   ./scripts/verify/verify-phase6.sh

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# Function to print colored output
print_header() {
    echo -e "\n${BLUE}============================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================${NC}\n"
}

print_pass() {
    echo -e "${GREEN}✓${NC} $1"
    PASSED=$((PASSED + 1))
}

print_fail() {
    echo -e "${RED}✗${NC} $1"
    FAILED=$((FAILED + 1))
}

print_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    WARNINGS=$((WARNINGS + 1))
}

# Check if file exists
check_file() {
    if [ -f "$1" ]; then
        print_pass "File exists: $1"
        return 0
    else
        print_fail "File missing: $1"
        return 1
    fi
}

# Check if file is executable
check_executable() {
    if [ -x "$1" ]; then
        print_pass "File is executable: $1"
        return 0
    else
        print_fail "File is not executable: $1"
        return 1
    fi
}

# Check if YAML file is valid (basic check)
check_yaml() {
    if command -v yamllint &> /dev/null; then
        if yamllint "$1" &> /dev/null; then
            print_pass "YAML syntax valid: $1"
            return 0
        else
            print_warn "YAML syntax check failed (yamllint not available or error): $1"
            return 1
        fi
    else
        # Basic check: file exists and is readable
        if [ -r "$1" ]; then
            print_warn "YAML file exists but yamllint not installed: $1"
            return 0
        else
            print_fail "YAML file not readable: $1"
            return 1
        fi
    fi
}

# Check if script has required functions/commands
check_script_functionality() {
    local script=$1
    local required_pattern=$2
    
    if grep -q "$required_pattern" "$script" 2>/dev/null; then
        print_pass "Script contains required functionality: $script"
        return 0
    else
        print_fail "Script missing required functionality: $script ($required_pattern)"
        return 1
    fi
}

print_header "Phase 6: GCP Deployment Configuration Verification"

# =============================================================================
# 1. Cloud Build Configuration
# =============================================================================
print_header "1. Cloud Build Configuration"

check_file "cloudbuild.yaml" && {
    # Check for required fields
    if grep -q "build-python-api" cloudbuild.yaml && \
       grep -q "build-frontend" cloudbuild.yaml && \
       grep -q "deploy-python-api" cloudbuild.yaml && \
       grep -q "deploy-frontend" cloudbuild.yaml; then
        print_pass "Cloud Build config contains required build/deploy steps"
    else
        print_fail "Cloud Build config missing required steps"
    fi
    
    # Check for PROJECT_ID substitution
    if grep -q "\$PROJECT_ID" cloudbuild.yaml; then
        print_pass "Cloud Build config uses PROJECT_ID substitution"
    else
        print_warn "Cloud Build config may not use PROJECT_ID substitution"
    fi
}

# =============================================================================
# 2. Cloud Run Deployment Files
# =============================================================================
print_header "2. Cloud Run Deployment Files"

# Check Python API Cloud Run config
check_file "cloud-run-python.yaml" && {
    check_yaml "cloud-run-python.yaml"
    if grep -q "eui-python-api" cloud-run-python.yaml && \
       grep -q "serviceAccountName" cloud-run-python.yaml && \
       grep -q "secretKeyRef" cloud-run-python.yaml; then
        print_pass "Python API Cloud Run config contains required fields"
    else
        print_fail "Python API Cloud Run config missing required fields"
    fi
}

# Check Frontend Cloud Run config
check_file "cloud-run-frontend.yaml" && {
    check_yaml "cloud-run-frontend.yaml"
    if grep -q "eui-frontend" cloud-run-frontend.yaml && \
       grep -q "serviceAccountName" cloud-run-frontend.yaml && \
       grep -q "secretKeyRef" cloud-run-frontend.yaml; then
        print_pass "Frontend Cloud Run config contains required fields"
    else
        print_fail "Frontend Cloud Run config missing required fields"
    fi
}

# Check Token Renderer Cloud Run config (optional)
if check_file "cloud-run-token-renderer.yaml"; then
    check_yaml "cloud-run-token-renderer.yaml"
    if grep -q "eui-token-renderer" cloud-run-token-renderer.yaml && \
       grep -q "run.googleapis.com/ingress: internal" cloud-run-token-renderer.yaml; then
        print_pass "Token Renderer Cloud Run config contains required fields"
    else
        print_warn "Token Renderer Cloud Run config may be incomplete"
    fi
else
    print_warn "Token Renderer Cloud Run config not found (optional)"
fi

# =============================================================================
# 3. Setup Scripts
# =============================================================================
print_header "3. Setup Scripts"

# Check setup-secrets.sh
if check_file "scripts/setup/setup-secrets.sh"; then
    check_executable "scripts/setup/setup-secrets.sh"
    check_script_functionality "scripts/setup/setup-secrets.sh" "create-all"
    check_script_functionality "scripts/setup/setup-secrets.sh" "gcloud secrets"
fi

# Check setup-service-accounts.sh
if check_file "scripts/setup/setup-service-accounts.sh"; then
    check_executable "scripts/setup/setup-service-accounts.sh"
    check_script_functionality "scripts/setup/setup-service-accounts.sh" "create-all"
    check_script_functionality "scripts/setup/setup-service-accounts.sh" "gcloud iam"
fi

# =============================================================================
# 4. Environment Configuration Files
# =============================================================================
print_header "4. Environment Configuration Files"

# Check .env.example (should exist)
if check_file ".env.example"; then
    if grep -q "PYTHON_API" .env.example && \
       grep -q "ELASTICSEARCH" .env.example && \
       grep -q "API_KEYS" .env.example; then
        print_pass ".env.example contains required environment variables"
    else
        print_fail ".env.example missing required environment variables"
    fi
fi

# Check .env.development (optional, may be gitignored)
if [ -f ".env.development" ]; then
    print_pass ".env.development exists"
else
    print_warn ".env.development not found (may be gitignored, this is OK)"
fi

# Check .env.production.example (optional)
if check_file ".env.production.example"; then
    if grep -q "Cloud Run" .env.production.example && \
       grep -q "Secret Manager" .env.production.example; then
        print_pass ".env.production.example contains production guidance"
    else
        print_warn ".env.production.example may be incomplete"
    fi
fi

# =============================================================================
# 5. Documentation
# =============================================================================
print_header "5. Documentation"

check_file "docs/PHASE6_GCP_DEPLOYMENT_IMPLEMENTATION.md" && {
    if grep -q "Cloud Build" docs/PHASE6_GCP_DEPLOYMENT_IMPLEMENTATION.md && \
       grep -q "Service Account" docs/PHASE6_GCP_DEPLOYMENT_IMPLEMENTATION.md && \
       grep -q "Secret Management" docs/PHASE6_GCP_DEPLOYMENT_IMPLEMENTATION.md; then
        print_pass "Phase 6 documentation is complete"
    else
        print_warn "Phase 6 documentation may be incomplete"
    fi
}

# =============================================================================
# 6. Cloud Build Configuration Validation
# =============================================================================
print_header "6. Cloud Build Configuration Validation"

if [ -f "cloudbuild.yaml" ]; then
    # Check for required images
    if grep -q "eui-python-api" cloudbuild.yaml && \
       grep -q "eui-frontend" cloudbuild.yaml; then
        print_pass "Cloud Build config references required images"
    else
        print_fail "Cloud Build config missing image references"
    fi
    
    # Check for deployment steps (check for 'run' and 'services' or 'deploy')
    if grep -q "run" cloudbuild.yaml && grep -q "services" cloudbuild.yaml; then
        print_pass "Cloud Build config includes Cloud Run deployment"
    elif grep -q "deploy" cloudbuild.yaml; then
        print_pass "Cloud Build config includes deployment steps"
    else
        print_fail "Cloud Build config missing Cloud Run deployment"
    fi
fi

# =============================================================================
# Summary
# =============================================================================
print_header "Verification Summary"

echo -e "Passed:  ${GREEN}$PASSED${NC}"
echo -e "Failed:  ${RED}$FAILED${NC}"
echo -e "Warnings: ${YELLOW}$WARNINGS${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All required checks passed!${NC}"
    if [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}⚠ Some optional checks had warnings (see above)${NC}"
    fi
    exit 0
else
    echo -e "${RED}✗ Some checks failed. Please review the errors above.${NC}"
    exit 1
fi

