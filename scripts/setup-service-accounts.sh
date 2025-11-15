#!/bin/bash
# Setup service accounts and IAM roles for EUI Icon Embeddings Cloud Run services
#
# This script creates service accounts and grants necessary IAM permissions:
# - eui-python-api-sa: Service account for Python API
# - eui-frontend-sa: Service account for Frontend
# - eui-token-renderer-sa: Service account for Token Renderer (optional)
#
# Usage:
#   ./scripts/setup-service-accounts.sh [command] [options]
#
# Commands:
#   create-all          Create all service accounts and grant permissions
#   create-python-sa    Create Python API service account
#   create-frontend-sa  Create Frontend service account
#   create-token-renderer-sa  Create Token Renderer service account
#   grant-secret-access Grant Secret Manager access to service accounts
#   list                List all service accounts
#
# Prerequisites:
#   - gcloud CLI installed and authenticated
#   - IAM Admin permissions
#   - Service Usage API enabled

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default project (can be overridden with PROJECT_ID env var)
PROJECT_ID="${PROJECT_ID:-}"

# Service account names
PYTHON_SA="eui-python-api-sa"
FRONTEND_SA="eui-frontend-sa"
TOKEN_RENDERER_SA="eui-token-renderer-sa"

# Secret names (must match setup-secrets.sh)
ELASTICSEARCH_SECRET="elasticsearch-api-key"
API_KEYS_SECRET="api-keys"
FRONTEND_KEY_SECRET="frontend-api-key"

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

# Function to check if PROJECT_ID is set
check_project() {
    if [ -z "$PROJECT_ID" ]; then
        PROJECT_ID=$(gcloud config get-value project 2>/dev/null || echo "")
        if [ -z "$PROJECT_ID" ]; then
            print_error "PROJECT_ID not set. Set it with: export PROJECT_ID=your-project-id"
            exit 1
        fi
    fi
    print_info "Using project: $PROJECT_ID"
}

# Function to create a service account
create_service_account() {
    local sa_name=$1
    local display_name=$2
    local description=$3
    
    if gcloud iam service-accounts describe "$sa_name@$PROJECT_ID.iam.gserviceaccount.com" --project="$PROJECT_ID" &>/dev/null; then
        print_warn "Service account $sa_name already exists. Skipping creation."
        return
    fi
    
    gcloud iam service-accounts create "$sa_name" \
        --display-name="$display_name" \
        --description="$description" \
        --project="$PROJECT_ID"
    
    print_info "Service account $sa_name created successfully"
}

# Function to grant Secret Manager access to a service account
grant_secret_access() {
    local sa_name=$1
    local secret_name=$2
    local sa_email="$sa_name@$PROJECT_ID.iam.gserviceaccount.com"
    
    # Check if secret exists
    if ! gcloud secrets describe "$secret_name" --project="$PROJECT_ID" &>/dev/null; then
        print_warn "Secret $secret_name does not exist. Skipping access grant."
        return
    fi
    
    # Grant secretAccessor role
    gcloud secrets add-iam-policy-binding "$secret_name" \
        --member="serviceAccount:$sa_email" \
        --role="roles/secretmanager.secretAccessor" \
        --project="$PROJECT_ID" \
        --quiet
    
    print_info "Granted Secret Manager access for $sa_name to secret $secret_name"
}

# Function to create Python API service account
create_python_sa() {
    check_project
    
    print_info "Creating Python API service account..."
    create_service_account \
        "$PYTHON_SA" \
        "EUI Python API Service Account" \
        "Service account for Python embedding/search API on Cloud Run"
    
    # Grant Secret Manager access
    grant_secret_access "$PYTHON_SA" "$ELASTICSEARCH_SECRET"
    grant_secret_access "$PYTHON_SA" "$API_KEYS_SECRET"
    
    print_info "Python API service account setup complete"
}

# Function to create Frontend service account
create_frontend_sa() {
    check_project
    
    print_info "Creating Frontend service account..."
    create_service_account \
        "$FRONTEND_SA" \
        "EUI Frontend Service Account" \
        "Service account for Next.js frontend on Cloud Run"
    
    # Grant Secret Manager access
    grant_secret_access "$FRONTEND_SA" "$ELASTICSEARCH_SECRET"
    grant_secret_access "$FRONTEND_SA" "$FRONTEND_KEY_SECRET"
    
    print_info "Frontend service account setup complete"
}

# Function to create Token Renderer service account
create_token_renderer_sa() {
    check_project
    
    print_info "Creating Token Renderer service account..."
    create_service_account \
        "$TOKEN_RENDERER_SA" \
        "EUI Token Renderer Service Account" \
        "Service account for token renderer service on Cloud Run (optional)"
    
    print_info "Token Renderer service account setup complete"
}

# Function to grant Secret Manager access to all service accounts
grant_secret_access_all() {
    check_project
    
    print_info "Granting Secret Manager access to all service accounts..."
    
    # Python API needs Elasticsearch and API keys
    grant_secret_access "$PYTHON_SA" "$ELASTICSEARCH_SECRET"
    grant_secret_access "$PYTHON_SA" "$API_KEYS_SECRET"
    
    # Frontend needs Elasticsearch and frontend API key
    grant_secret_access "$FRONTEND_SA" "$ELASTICSEARCH_SECRET"
    grant_secret_access "$FRONTEND_SA" "$FRONTEND_KEY_SECRET"
    
    print_info "Secret Manager access granted to all service accounts"
}

# Function to create all service accounts
create_all() {
    check_project
    
    print_info "Creating all service accounts..."
    
    create_python_sa
    create_frontend_sa
    create_token_renderer_sa
    
    print_info "All service accounts created successfully!"
    print_info ""
    print_info "Service account emails:"
    print_info "  Python API:    $PYTHON_SA@$PROJECT_ID.iam.gserviceaccount.com"
    print_info "  Frontend:      $FRONTEND_SA@$PROJECT_ID.iam.gserviceaccount.com"
    print_info "  Token Renderer: $TOKEN_RENDERER_SA@$PROJECT_ID.iam.gserviceaccount.com"
    print_info ""
    print_info "Next steps:"
    print_info "1. Update Cloud Run YAML files with service account emails"
    print_info "2. Run: $0 grant-secret-access (if secrets already exist)"
}

# Function to list all service accounts
list_service_accounts() {
    check_project
    print_info "Listing service accounts for project $PROJECT_ID:"
    gcloud iam service-accounts list --project="$PROJECT_ID" --format="table(email,displayName)"
}

# Main script logic
main() {
    case "${1:-}" in
        create-all)
            create_all
            ;;
        create-python-sa)
            create_python_sa
            ;;
        create-frontend-sa)
            create_frontend_sa
            ;;
        create-token-renderer-sa)
            create_token_renderer_sa
            ;;
        grant-secret-access)
            grant_secret_access_all
            ;;
        list)
            list_service_accounts
            ;;
        *)
            echo "Usage: $0 [command]"
            echo ""
            echo "Commands:"
            echo "  create-all              Create all service accounts and grant permissions"
            echo "  create-python-sa        Create Python API service account"
            echo "  create-frontend-sa      Create Frontend service account"
            echo "  create-token-renderer-sa  Create Token Renderer service account"
            echo "  grant-secret-access     Grant Secret Manager access to service accounts"
            echo "  list                    List all service accounts"
            exit 1
            ;;
    esac
}

main "$@"

