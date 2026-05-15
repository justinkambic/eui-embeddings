#!/bin/bash
# API Key Management Script for EUI Icon Embeddings
# Manages API keys stored in Google Secret Manager

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-}"
SECRET_NAME="${API_KEYS_SECRET_NAME:-api-keys}"
KEY_LENGTH="${API_KEY_LENGTH:-32}"

# Function to generate a secure API key
generate_api_key() {
    # Generate a random 32+ character key using openssl
    if command -v openssl &> /dev/null; then
        openssl rand -hex 32 | tr -d '\n'
    elif command -v python3 &> /dev/null; then
        python3 -c "import secrets; print(secrets.token_urlsafe($KEY_LENGTH))"
    else
        # Fallback: use /dev/urandom
        cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w $KEY_LENGTH | head -n 1
    fi
}

# Function to get current API keys from Secret Manager
get_api_keys() {
    local project_id=$1
    local secret_name=$2
    
    if [ -z "$project_id" ]; then
        echo -e "${RED}Error: GOOGLE_CLOUD_PROJECT not set${NC}" >&2
        return 1
    fi
    
    local secret_path="projects/${project_id}/secrets/${secret_name}/versions/latest"
    
    # Try to get the secret
    if gcloud secrets versions access latest --secret="$secret_name" --project="$project_id" 2>/dev/null; then
        return 0
    else
        # Secret doesn't exist or can't be accessed
        echo "[]"
        return 1
    fi
}

# Function to save API keys to Secret Manager
save_api_keys() {
    local project_id=$1
    local secret_name=$2
    local keys_json=$3
    
    if [ -z "$project_id" ]; then
        echo -e "${RED}Error: GOOGLE_CLOUD_PROJECT not set${NC}" >&2
        return 1
    fi
    
    # Check if secret exists
    if ! gcloud secrets describe "$secret_name" --project="$project_id" &>/dev/null; then
        echo -e "${YELLOW}Creating secret: $secret_name${NC}"
        echo -n "$keys_json" | gcloud secrets create "$secret_name" \
            --data-file=- \
            --replication-policy="automatic" \
            --project="$project_id"
    else
        echo -e "${YELLOW}Updating secret: $secret_name${NC}"
        echo -n "$keys_json" | gcloud secrets versions add "$secret_name" \
            --data-file=- \
            --project="$project_id"
    fi
}

# Function to list API keys
list_keys() {
    local project_id=$1
    local secret_name=$2
    
    echo -e "${BLUE}Fetching API keys from Secret Manager...${NC}"
    
    local keys_json=$(get_api_keys "$project_id" "$secret_name")
    
    if [ "$keys_json" == "[]" ]; then
        echo -e "${YELLOW}No API keys found in Secret Manager${NC}"
        return 0
    fi
    
    # Parse and display keys
    echo -e "${GREEN}Active API keys:${NC}"
    echo "$keys_json" | python3 -c "
import json, sys
try:
    keys = json.load(sys.stdin)
    if isinstance(keys, list):
        for i, key in enumerate(keys, 1):
            # Show first 8 and last 4 characters for security
            masked = key[:8] + '...' + key[-4:] if len(key) > 12 else '***'
            print(f'  {i}. {masked} (length: {len(key)})')
    else:
        print('  Invalid format: expected JSON array')
except Exception as e:
    print(f'  Error parsing keys: {e}')
" 2>/dev/null || echo "$keys_json"
}

# Function to add a new API key
add_key() {
    local project_id=$1
    local secret_name=$2
    local new_key=$3
    
    echo -e "${BLUE}Adding new API key...${NC}"
    
    # Get current keys
    local current_keys_json=$(get_api_keys "$project_id" "$secret_name")
    local keys_array
    
    if [ "$current_keys_json" == "[]" ] || [ -z "$current_keys_json" ]; then
        keys_array="[]"
    else
        keys_array="$current_keys_json"
    fi
    
    # Add new key using Python
    local updated_keys=$(echo "$keys_array" | python3 -c "
import json, sys
try:
    keys = json.load(sys.stdin) if sys.stdin.readable() else []
    if not isinstance(keys, list):
        keys = []
    new_key = sys.argv[1]
    if new_key not in keys:
        keys.append(new_key)
        print(json.dumps(keys))
    else:
        print('ERROR: Key already exists', file=sys.stderr)
        sys.exit(1)
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)
" "$new_key")
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error: Failed to add key${NC}" >&2
        return 1
    fi
    
    # Save updated keys
    save_api_keys "$project_id" "$secret_name" "$updated_keys"
    
    echo -e "${GREEN}API key added successfully${NC}"
    echo -e "${YELLOW}New key: ${new_key}${NC}"
    echo -e "${YELLOW}⚠️  Save this key securely - it won't be shown again!${NC}"
}

# Function to remove an API key
remove_key() {
    local project_id=$1
    local secret_name=$2
    local key_to_remove=$3
    
    echo -e "${BLUE}Removing API key...${NC}"
    
    # Get current keys
    local current_keys_json=$(get_api_keys "$project_id" "$secret_name")
    
    if [ "$current_keys_json" == "[]" ] || [ -z "$current_keys_json" ]; then
        echo -e "${YELLOW}No keys to remove${NC}"
        return 0
    fi
    
    # Remove key using Python
    local updated_keys=$(echo "$current_keys_json" | python3 -c "
import json, sys
try:
    keys = json.load(sys.stdin)
    if not isinstance(keys, list):
        keys = []
    key_to_remove = sys.argv[1]
    if key_to_remove in keys:
        keys.remove(key_to_remove)
        print(json.dumps(keys))
    else:
        print('ERROR: Key not found', file=sys.stderr)
        sys.exit(1)
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)
" "$key_to_remove")
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error: Key not found${NC}" >&2
        return 1
    fi
    
    # Save updated keys
    save_api_keys "$project_id" "$secret_name" "$updated_keys"
    
    echo -e "${GREEN}API key removed successfully${NC}"
}

# Function to generate and add a new key
generate_and_add() {
    local project_id=$1
    local secret_name=$2
    
    echo -e "${BLUE}Generating new API key...${NC}"
    local new_key=$(generate_api_key)
    
    if [ -z "$new_key" ]; then
        echo -e "${RED}Error: Failed to generate API key${NC}" >&2
        return 1
    fi
    
    add_key "$project_id" "$secret_name" "$new_key"
}

# Main script logic
main() {
    # Get project ID
    if [ -z "$PROJECT_ID" ]; then
        PROJECT_ID=$(gcloud config get-value project 2>/dev/null || echo "")
        if [ -z "$PROJECT_ID" ]; then
            echo -e "${RED}Error: GOOGLE_CLOUD_PROJECT not set and no default project configured${NC}" >&2
            echo "Set GOOGLE_CLOUD_PROJECT environment variable or run: gcloud config set project PROJECT_ID"
            exit 1
        fi
    fi
    
    echo -e "${BLUE}Project ID: $PROJECT_ID${NC}"
    echo -e "${BLUE}Secret Name: $SECRET_NAME${NC}"
    echo ""
    
    case "${1:-}" in
        list|l)
            list_keys "$PROJECT_ID" "$SECRET_NAME"
            ;;
        generate|gen|g)
            generate_and_add "$PROJECT_ID" "$SECRET_NAME"
            ;;
        add|a)
            if [ -z "${2:-}" ]; then
                echo -e "${RED}Error: API key required${NC}" >&2
                echo "Usage: $0 add <api-key>"
                exit 1
            fi
            add_key "$PROJECT_ID" "$SECRET_NAME" "$2"
            ;;
        remove|rm|r)
            if [ -z "${2:-}" ]; then
                echo -e "${RED}Error: API key required${NC}" >&2
                echo "Usage: $0 remove <api-key>"
                exit 1
            fi
            remove_key "$PROJECT_ID" "$SECRET_NAME" "$2"
            ;;
        *)
            echo -e "${BLUE}API Key Management for EUI Icon Embeddings${NC}"
            echo ""
            echo "Usage: $0 <command> [options]"
            echo ""
            echo "Commands:"
            echo "  list, l              List all API keys (masked)"
            echo "  generate, gen, g     Generate and add a new API key"
            echo "  add, a <key>         Add an existing API key"
            echo "  remove, rm, r <key>  Remove an API key"
            echo ""
            echo "Environment Variables:"
            echo "  GOOGLE_CLOUD_PROJECT    GCP project ID (required)"
            echo "  API_KEYS_SECRET_NAME    Secret name (default: api-keys)"
            echo "  API_KEY_LENGTH          Key length (default: 32)"
            echo ""
            echo "Examples:"
            echo "  $0 list"
            echo "  $0 generate"
            echo "  $0 add my-api-key-here"
            echo "  $0 remove old-api-key-here"
            exit 1
            ;;
    esac
}

main "$@"

