#!/bin/bash
# Verification script for OpenTelemetry observability setup
# This script checks that OpenTelemetry dependencies are installed,
# environment variables are set, and optionally tests OTLP export connectivity.

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
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    PASSED=$((PASSED + 1))
}

print_error() {
    echo -e "${RED}[FAIL]${NC} $1"
    FAILED=$((FAILED + 1))
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    WARNINGS=$((WARNINGS + 1))
}

print_header() {
    echo -e "\n${BLUE}============================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================${NC}\n"
}

# Check Python OpenTelemetry dependencies
check_python_dependencies() {
    print_header "Checking Python OpenTelemetry Dependencies"
    
    if ! command -v python3 >/dev/null 2>&1; then
        print_error "Python 3 is not installed"
        return 1
    fi
    
    local missing_deps=()
    
    # Check for required packages
    python3 -c "import opentelemetry" 2>/dev/null || missing_deps+=("opentelemetry-api")
    python3 -c "import opentelemetry.sdk" 2>/dev/null || missing_deps+=("opentelemetry-sdk")
    python3 -c "import opentelemetry.instrumentation.fastapi" 2>/dev/null || missing_deps+=("opentelemetry-instrumentation-fastapi")
    python3 -c "import opentelemetry.instrumentation.requests" 2>/dev/null || missing_deps+=("opentelemetry-instrumentation-requests")
    python3 -c "import opentelemetry.instrumentation.elasticsearch" 2>/dev/null || missing_deps+=("opentelemetry-instrumentation-elasticsearch")
    python3 -c "import opentelemetry.exporter.otlp.proto.http.trace_exporter" 2>/dev/null || missing_deps+=("opentelemetry-exporter-otlp-proto-http")
    
    if [ ${#missing_deps[@]} -eq 0 ]; then
        print_success "All Python OpenTelemetry dependencies are installed"
        return 0
    else
        print_error "Missing Python dependencies: ${missing_deps[*]}"
        print_info "Install with: pip install -r requirements.txt"
        return 1
    fi
}

# Check Node.js OpenTelemetry dependencies
check_node_dependencies() {
    print_header "Checking Node.js OpenTelemetry Dependencies"
    
    if ! command -v node >/dev/null 2>&1; then
        print_warn "Node.js is not installed (skipping Node.js checks)"
        return 0
    fi
    
    if [ ! -f "frontend/package.json" ]; then
        print_warn "frontend/package.json not found (skipping Node.js checks)"
        return 0
    fi
    
    cd frontend || return 1
    
    local missing_deps=()
    
    # Check for required packages in node_modules
    [ -d "node_modules/@opentelemetry/api" ] || missing_deps+=("@opentelemetry/api")
    [ -d "node_modules/@opentelemetry/sdk-node" ] || missing_deps+=("@opentelemetry/sdk-node")
    [ -d "node_modules/@opentelemetry/instrumentation-http" ] || missing_deps+=("@opentelemetry/instrumentation-http")
    [ -d "node_modules/@opentelemetry/instrumentation-fetch" ] || missing_deps+=("@opentelemetry/instrumentation-fetch")
    [ -d "node_modules/@opentelemetry/exporter-trace-otlp-http" ] || missing_deps+=("@opentelemetry/exporter-trace-otlp-http")
    [ -d "node_modules/@opentelemetry/exporter-metrics-otlp-http" ] || missing_deps+=("@opentelemetry/exporter-metrics-otlp-http")
    [ -d "node_modules/@elastic/apm-rum" ] || missing_deps+=("@elastic/apm-rum")
    
    cd ..
    
    if [ ${#missing_deps[@]} -eq 0 ]; then
        print_success "All Node.js OpenTelemetry dependencies are installed"
        return 0
    else
        print_error "Missing Node.js dependencies: ${missing_deps[*]}"
        print_info "Install with: cd frontend && npm install"
        return 1
    fi
}

# Check Python API environment variables
check_python_env_vars() {
    print_header "Checking Python API Environment Variables"
    
    local all_set=true
    
    # Required variables (with defaults)
    local otel_endpoint="${OTEL_EXPORTER_OTLP_ENDPOINT:-https://ff29e674b8bb4b06b3e71aaacf84879f.ingest.us-central1.gcp.elastic.cloud:443}"
    local otel_headers="${OTEL_EXPORTER_OTLP_HEADERS:-Authorization=ApiKey ZjlhVnRwb0JITGJzUkpwVXhNR0w6S1htMDVsWHJPbW1yczFMOEo0QTFxdw==}"
    local otel_service_name="${OTEL_SERVICE_NAME:-eui-python-api}"
    
    print_info "OTEL_EXPORTER_OTLP_ENDPOINT: $otel_endpoint"
    print_info "OTEL_SERVICE_NAME: $otel_service_name"
    print_info "OTEL_EXPORTER_OTLP_HEADERS: ${otel_headers:0:30}... (hidden)"
    
    if [ -n "${OTEL_EXPORTER_OTLP_ENDPOINT:-}" ]; then
        print_success "OTEL_EXPORTER_OTLP_ENDPOINT is set"
    else
        print_warn "OTEL_EXPORTER_OTLP_ENDPOINT using default value"
    fi
    
    if [ -n "${OTEL_EXPORTER_OTLP_HEADERS:-}" ]; then
        print_success "OTEL_EXPORTER_OTLP_HEADERS is set"
    else
        print_warn "OTEL_EXPORTER_OTLP_HEADERS using default value"
    fi
    
    if [ -n "${OTEL_SERVICE_NAME:-}" ]; then
        print_success "OTEL_SERVICE_NAME is set: $otel_service_name"
    else
        print_warn "OTEL_SERVICE_NAME using default value: $otel_service_name"
    fi
    
    if [ -n "${OTEL_SERVICE_VERSION:-}" ]; then
        print_success "OTEL_SERVICE_VERSION is set: $OTEL_SERVICE_VERSION"
    else
        print_warn "OTEL_SERVICE_VERSION not set (will use 'unknown')"
    fi
    
    return 0
}

# Check Frontend environment variables
check_frontend_env_vars() {
    print_header "Checking Frontend Environment Variables"
    
    # Server-side variables
    local otel_endpoint="${OTEL_EXPORTER_OTLP_ENDPOINT:-https://ff29e674b8bb4b06b3e71aaacf84879f.ingest.us-central1.gcp.elastic.cloud:443}"
    local otel_service_name="${OTEL_SERVICE_NAME:-eui-frontend}"
    
    print_info "Server-side variables:"
    print_info "  OTEL_EXPORTER_OTLP_ENDPOINT: $otel_endpoint"
    print_info "  OTEL_SERVICE_NAME: $otel_service_name"
    
    if [ -n "${OTEL_EXPORTER_OTLP_ENDPOINT:-}" ]; then
        print_success "OTEL_EXPORTER_OTLP_ENDPOINT is set (server-side)"
    else
        print_warn "OTEL_EXPORTER_OTLP_ENDPOINT using default value (server-side)"
    fi
    
    # Browser-accessible variables (NEXT_PUBLIC_*)
    print_info "Browser-accessible variables (NEXT_PUBLIC_*):"
    
    local next_public_service_name="${NEXT_PUBLIC_OTEL_SERVICE_NAME:-eui-frontend}"
    local next_public_apm_url="${NEXT_PUBLIC_ELASTIC_APM_SERVER_URL:-$otel_endpoint}"
    
    print_info "  NEXT_PUBLIC_OTEL_SERVICE_NAME: $next_public_service_name"
    print_info "  NEXT_PUBLIC_ELASTIC_APM_SERVER_URL: $next_public_apm_url"
    
    if [ -n "${NEXT_PUBLIC_OTEL_SERVICE_NAME:-}" ]; then
        print_success "NEXT_PUBLIC_OTEL_SERVICE_NAME is set"
    else
        print_warn "NEXT_PUBLIC_OTEL_SERVICE_NAME using default value"
    fi
    
    if [ -n "${NEXT_PUBLIC_ELASTIC_APM_SERVER_URL:-}" ]; then
        print_success "NEXT_PUBLIC_ELASTIC_APM_SERVER_URL is set"
    else
        print_warn "NEXT_PUBLIC_ELASTIC_APM_SERVER_URL using default value"
    fi
    
    return 0
}

# Test OTLP endpoint connectivity (optional)
test_otlp_connectivity() {
    print_header "Testing OTLP Endpoint Connectivity (Optional)"
    
    if ! command -v curl >/dev/null 2>&1; then
        print_warn "curl is not installed (skipping connectivity test)"
        return 0
    fi
    
    local otel_endpoint="${OTEL_EXPORTER_OTLP_ENDPOINT:-https://ff29e674b8bb4b06b3e71aaacf84879f.ingest.us-central1.gcp.elastic.cloud:443}"
    local otel_headers="${OTEL_EXPORTER_OTLP_HEADERS:-Authorization=ApiKey ZjlhVnRwb0JITGJzUkpwVXhNR0w6S1htMDVsWHJPbW1yczFMOEo0QTFxdw==}"
    
    # Parse headers
    local auth_header=""
    if [[ "$otel_headers" == *"Authorization="* ]]; then
        auth_header=$(echo "$otel_headers" | sed 's/.*Authorization=\([^,]*\).*/\1/')
    fi
    
    print_info "Testing connectivity to: $otel_endpoint/v1/traces"
    
    # Try to connect (expecting 400 Bad Request for empty payload, which means endpoint is reachable)
    local response_code
    response_code=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "$otel_endpoint/v1/traces" \
        -H "Authorization: $auth_header" \
        -H "Content-Type: application/x-protobuf" \
        --data-binary "" \
        --max-time 10 2>/dev/null || echo "000")
    
    if [ "$response_code" = "400" ] || [ "$response_code" = "200" ]; then
        print_success "OTLP endpoint is reachable (response code: $response_code)"
        return 0
    elif [ "$response_code" = "000" ]; then
        print_error "Failed to connect to OTLP endpoint (timeout or connection error)"
        return 1
    else
        print_warn "OTLP endpoint returned unexpected response code: $response_code"
        return 0
    fi
}

# Check for instrumentation files
check_instrumentation_files() {
    print_header "Checking Instrumentation Files"
    
    local all_present=true
    
    # Python API
    if [ -f "otel_config.py" ]; then
        print_success "otel_config.py exists"
    else
        print_error "otel_config.py is missing"
        all_present=false
    fi
    
    # Frontend
    if [ -f "frontend/instrumentation.ts" ]; then
        print_success "frontend/instrumentation.ts exists"
    else
        print_error "frontend/instrumentation.ts is missing"
        all_present=false
    fi
    
    if [ -f "frontend/lib/rum.ts" ]; then
        print_success "frontend/lib/rum.ts exists"
    else
        print_error "frontend/lib/rum.ts is missing"
        all_present=false
    fi
    
    return $([ "$all_present" = true ] && echo 0 || echo 1)
}

# Main execution
main() {
    echo -e "${BLUE}"
    echo "============================================================"
    echo "OpenTelemetry Observability Verification"
    echo "============================================================"
    echo -e "${NC}"
    
    check_python_dependencies
    check_node_dependencies
    check_python_env_vars
    check_frontend_env_vars
    check_instrumentation_files
    
    # Optional connectivity test (skip if TEST_OTLP_CONNECTIVITY is set to false)
    if [ "${TEST_OTLP_CONNECTIVITY:-true}" != "false" ]; then
        test_otlp_connectivity
    else
        print_info "Skipping OTLP connectivity test (TEST_OTLP_CONNECTIVITY=false)"
    fi
    
    # Summary
    echo ""
    print_header "Summary"
    echo -e "${GREEN}Passed:${NC} $PASSED"
    echo -e "${YELLOW}Warnings:${NC} $WARNINGS"
    echo -e "${RED}Failed:${NC} $FAILED"
    echo ""
    
    if [ $FAILED -eq 0 ]; then
        print_success "All checks passed! OpenTelemetry observability is configured correctly."
        echo ""
        print_info "Next steps:"
        print_info "1. Start the Python API: python embed.py"
        print_info "2. Start the frontend: cd frontend && npm run dev"
        print_info "3. Make API calls to generate traces"
        print_info "4. Check Elastic Observability UI for traces and metrics"
        exit 0
    else
        print_error "Some checks failed. Please review the errors above."
        exit 1
    fi
}

# Run main function
main

