#!/bin/bash
# Setup secrets in Google Secret Manager for EUI Icon Embeddings services
#
# This script creates and manages secrets required for the application:
# - Elasticsearch API key
# - API keys for Python API authentication
# - Frontend API key for authenticating with Python API
#
# Usage:
#   ./scripts/setup/setup-secrets.sh [command] [options]
#
# Commands:
#   create-all          Create all required secrets (interactive)
#   create-elasticsearch-key  Create Elasticsearch API key secret
#   create-api-keys     Create API keys secret (JSON array)
#   create-frontend-key Create frontend API key secret
#   list                List all secrets
#   get [secret-name]   Get secret value (masked)
#   delete [secret-name] Delete a secret
#
# Prerequisites:
#   - gcloud CLI installed and authenticated
#   - Secret Manager API enabled
#   - Appropriate IAM permissions

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default project (can be overridden with PROJECT_ID env var)
PROJECT_ID="${PROJECT_ID:-}"

# Secret names
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

# Function to check if Secret Manager API is enabled
check_api_enabled() {
    if ! gcloud services list --enabled --filter="name:secretmanager.googleapis.com" --format="value(name)" | grep -q secretmanager; then
        print_warn "Secret Manager API not enabled. Enabling now..."
        gcloud services enable secretmanager.googleapis.com --project="$PROJECT_ID"
        print_info "Secret Manager API enabled"
    fi
}

# Function to create Elasticsearch API key secret
create_elasticsearch_key() {
    print_info "Creating Elasticsearch API key secret..."
    
    if gcloud secrets describe "$ELASTICSEARCH_SECRET" --project="$PROJECT_ID" &>/dev/null; then
        print_warn "Secret $ELASTICSEARCH_SECRET already exists. Skipping creation."
        return
    fi
    
    echo -n "Enter Elasticsearch API key: "
    read -s ELASTICSEARCH_KEY
    echo
    
    if [ -z "$ELASTICSEARCH_KEY" ]; then
        print_error "Elasticsearch API key cannot be empty"
        exit 1
    fi
    
    echo -n "$ELASTICSEARCH_KEY" | gcloud secrets create "$ELASTICSEARCH_SECRET" \
        --data-file=- \
        --replication-policy="automatic" \
        --project="$PROJECT_ID"
    
    print_info "Secret $ELASTICSEARCH_SECRET created successfully"
}

# Function to create API keys secret (JSON array)
create_api_keys() {
    print_info "Creating API keys secret..."
    
    if gcloud secrets describe "$API_KEYS_SECRET" --project="$PROJECT_ID" &>/dev/null; then
        print_warn "Secret $API_KEYS_SECRET already exists."
        read -p "Do you want to update it? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Skipping API keys creation"
            return
        fi
    fi
    
    print_info "Enter API keys (one per line, empty line to finish):"
    API_KEYS=()
    while IFS= read -r line; do
        [ -z "$line" ] && break
        API_KEYS+=("$line")
    done
    
    if [ ${#API_KEYS[@]} -eq 0 ]; then
        print_error "At least one API key is required"
        exit 1
    fi
    
    # Create JSON array
    JSON_ARRAY="["
    for i in "${!API_KEYS[@]}"; do
        if [ $i -gt 0 ]; then
            JSON_ARRAY+=","
        fi
        JSON_ARRAY+="\"${API_KEYS[$i]}\""
    done
    JSON_ARRAY+="]"
    
    echo -n "$JSON_ARRAY" | gcloud secrets create "$API_KEYS_SECRET" \
        --data-file=- \
        --replication-policy="automatic" \
        --project="$PROJECT_ID" \
        2>/dev/null || \
    echo -n "$JSON_ARRAY" | gcloud secrets versions add "$API_KEYS_SECRET" \
        --data-file=- \
        --project="$PROJECT_ID"
    
    print_info "Secret $API_KEYS_SECRET created/updated successfully"
    print_info "Added ${#API_KEYS[@]} API key(s)"
}

# Function to create frontend API key secret
create_frontend_key() {
    print_info "Creating frontend API key secret..."
    
    if gcloud secrets describe "$FRONTEND_KEY_SECRET" --project="$PROJECT_ID" &>/dev/null; then
        print_warn "Secret $FRONTEND_KEY_SECRET already exists. Skipping creation."
        return
    fi
    
    echo -n "Enter frontend API key (must be one of the API keys): "
    read -s FRONTEND_KEY
    echo
    
    if [ -z "$FRONTEND_KEY" ]; then
        print_error "Frontend API key cannot be empty"
        exit 1
    fi
    
    echo -n "$FRONTEND_KEY" | gcloud secrets create "$FRONTEND_KEY_SECRET" \
        --data-file=- \
        --replication-policy="automatic" \
        --project="$PROJECT_ID"
    
    print_info "Secret $FRONTEND_KEY_SECRET created successfully"
}

# Function to create all secrets interactively
create_all() {
    print_info "Creating all required secrets..."
    check_project
    check_api_enabled
    
    create_elasticsearch_key
    create_api_keys
    create_frontend_key
    
    print_info "All secrets created successfully!"
    print_info "Next steps:"
    print_info "1. Grant service accounts access to secrets (see setup-service-accounts.sh)"
    print_info "2. Update Cloud Run YAML files with secret names"
}

# Function to list all secrets
list_secrets() {
    check_project
    print_info "Listing secrets for project $PROJECT_ID:"
    gcloud secrets list --project="$PROJECT_ID" --format="table(name,createTime)"
}

# Function to get secret value (masked)
get_secret() {
    if [ -z "${1:-}" ]; then
        print_error "Secret name required"
        echo "Usage: $0 get <secret-name>"
        exit 1
    fi
    
    check_project
    
    if ! gcloud secrets describe "$1" --project="$PROJECT_ID" &>/dev/null; then
        print_error "Secret $1 not found"
        exit 1
    fi
    
    print_info "Secret $1 value (first 10 chars):"
    VALUE=$(gcloud secrets versions access latest --secret="$1" --project="$PROJECT_ID")
    echo "${VALUE:0:10}..."
}

# Function to delete a secret
delete_secret() {
    if [ -z "${1:-}" ]; then
        print_error "Secret name required"
        echo "Usage: $0 delete <secret-name>"
        exit 1
    fi
    
    check_project
    
    if ! gcloud secrets describe "$1" --project="$PROJECT_ID" &>/dev/null; then
        print_error "Secret $1 not found"
        exit 1
    fi
    
    print_warn "This will permanently delete secret $1"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Deletion cancelled"
        return
    fi
    
    gcloud secrets delete "$1" --project="$PROJECT_ID" --quiet
    print_info "Secret $1 deleted successfully"
}

# Main script logic
main() {
    case "${1:-}" in
        create-all)
            create_all
            ;;
        create-elasticsearch-key)
            check_project
            check_api_enabled
            create_elasticsearch_key
            ;;
        create-api-keys)
            check_project
            check_api_enabled
            create_api_keys
            ;;
        create-frontend-key)
            check_project
            check_api_enabled
            create_frontend_key
            ;;
        list)
            list_secrets
            ;;
        get)
            get_secret "${2:-}"
            ;;
        delete)
            delete_secret "${2:-}"
            ;;
        *)
            echo "Usage: $0 [command] [options]"
            echo ""
            echo "Commands:"
            echo "  create-all              Create all required secrets (interactive)"
            echo "  create-elasticsearch-key  Create Elasticsearch API key secret"
            echo "  create-api-keys         Create API keys secret (JSON array)"
            echo "  create-frontend-key     Create frontend API key secret"
            echo "  list                    List all secrets"
            echo "  get [secret-name]      Get secret value (masked)"
            echo "  delete [secret-name]    Delete a secret"
            exit 1
            ;;
    esac
}

main "$@"

