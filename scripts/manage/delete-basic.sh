#!/bin/bash
# Delete Cloud Run services deployed via basic deployment
#
# Usage:
#   ./scripts/manage/delete-basic.sh [python|frontend|both]
#
# Prerequisites:
#   - gcloud CLI installed and authenticated
#   - PROJECT_ID environment variable set

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="${PROJECT_ID:-}"
REGION="${REGION:-us-central1}"
SERVICE_TO_DELETE="${1:-both}"

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "\n${BLUE}============================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================${NC}\n"
}

# Check prerequisites
check_prerequisites() {
    if [ -z "$PROJECT_ID" ]; then
        PROJECT_ID=$(gcloud config get-value project 2>/dev/null || echo "")
        if [ -z "$PROJECT_ID" ]; then
            print_error "PROJECT_ID not set. Set it with: export PROJECT_ID=your-project-id"
            exit 1
        fi
    fi
    
    print_info "Using project: $PROJECT_ID"
    print_info "Using region: $REGION"
}

# List services (for reference)
list_services() {
    print_header "Cloud Run Services in Project"
    
    echo "Python API:"
    gcloud run services list \
        --project "$PROJECT_ID" \
        --region "$REGION" \
        --filter="metadata.name:eui-python-api" \
        --format="table(metadata.name,status.url,status.conditions[0].status)" 2>/dev/null || echo "  Not found"
    
    echo ""
    echo "Frontend:"
    gcloud run services list \
        --project "$PROJECT_ID" \
        --region "$REGION" \
        --filter="metadata.name:eui-frontend" \
        --format="table(metadata.name,status.url,status.conditions[0].status)" 2>/dev/null || echo "  Not found"
}

# Delete Python API
delete_python_api() {
    print_header "Deleting Python API"
    
    if gcloud run services describe eui-python-api \
        --region "$REGION" \
        --project "$PROJECT_ID" &>/dev/null; then
        
        print_warn "This will permanently delete the eui-python-api service"
        read -p "Are you sure? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Deletion cancelled"
            return
        fi
        
        gcloud run services delete eui-python-api \
            --region "$REGION" \
            --project "$PROJECT_ID" \
            --quiet
        
        print_info "Python API deleted successfully"
    else
        print_warn "Python API service not found (may already be deleted)"
    fi
}

# Delete Frontend
delete_frontend() {
    print_header "Deleting Frontend"
    
    if gcloud run services describe eui-frontend \
        --region "$REGION" \
        --project "$PROJECT_ID" &>/dev/null; then
        
        print_warn "This will permanently delete the eui-frontend service"
        read -p "Are you sure? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Deletion cancelled"
            return
        fi
        
        gcloud run services delete eui-frontend \
            --region "$REGION" \
            --project "$PROJECT_ID" \
            --quiet
        
        print_info "Frontend deleted successfully"
    else
        print_warn "Frontend service not found (may already be deleted)"
    fi
}

# Get service IDs/URLs for reference
get_service_info() {
    print_header "Service Information"
    
    echo "Service Names and URLs:"
    echo ""
    
    # Python API
    if gcloud run services describe eui-python-api \
        --region "$REGION" \
        --project "$PROJECT_ID" &>/dev/null; then
        PYTHON_URL=$(gcloud run services describe eui-python-api \
            --region "$REGION" \
            --project "$PROJECT_ID" \
            --format="value(status.url)")
        echo "Python API:"
        echo "  Name: eui-python-api"
        echo "  URL: $PYTHON_URL"
        echo "  Region: $REGION"
        echo "  Project: $PROJECT_ID"
        echo ""
    else
        echo "Python API: Not found"
        echo ""
    fi
    
    # Frontend
    if gcloud run services describe eui-frontend \
        --region "$REGION" \
        --project "$PROJECT_ID" &>/dev/null; then
        FRONTEND_URL=$(gcloud run services describe eui-frontend \
            --region "$REGION" \
            --project "$PROJECT_ID" \
            --format="value(status.url)")
        echo "Frontend:"
        echo "  Name: eui-frontend"
        echo "  URL: $FRONTEND_URL"
        echo "  Region: $REGION"
        echo "  Project: $PROJECT_ID"
        echo ""
    else
        echo "Frontend: Not found"
        echo ""
    fi
    
    echo "To delete manually:"
    echo "  gcloud run services delete eui-python-api --region=$REGION --project=$PROJECT_ID"
    echo "  gcloud run services delete eui-frontend --region=$REGION --project=$PROJECT_ID"
}

# Main deletion logic
main() {
    case "${1:-}" in
        python)
            check_prerequisites
            delete_python_api
            ;;
        frontend)
            check_prerequisites
            delete_frontend
            ;;
        both)
            check_prerequisites
            delete_python_api
            delete_frontend
            ;;
        list|info)
            check_prerequisites
            get_service_info
            list_services
            ;;
        *)
            print_header "EUI Icon Embeddings - Service Deletion"
            echo "Usage: $0 [python|frontend|both|list]"
            echo ""
            echo "Commands:"
            echo "  python   - Delete Python API service"
            echo "  frontend - Delete Frontend service"
            echo "  both     - Delete both services"
            echo "  list     - List service information (no deletion)"
            echo ""
            echo "Examples:"
            echo "  $0 list     # Show service info without deleting"
            echo "  $0 python   # Delete Python API only"
            echo "  $0 both     # Delete both services"
            exit 1
            ;;
    esac
    
    print_header "Done!"
}

main "$@"

