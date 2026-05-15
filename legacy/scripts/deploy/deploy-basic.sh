#!/bin/bash
# Basic deployment script for EUI Icon Embeddings to Cloud Run
# This script deploys containers with minimal configuration - no service accounts or Secret Manager
#
# Usage:
#   ./scripts/deploy/deploy-basic.sh [python|frontend|both]
#
# Environment Variables:
#   - FORCE_REBUILD=true  Force a full rebuild without Docker cache (slower but ensures fresh build)
#
# Prerequisites:
#   - gcloud CLI installed and authenticated
#   - Docker installed (for local builds, optional)
#   - PROJECT_ID environment variable set
#   - Environment variables set (see .env.basic)

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
SERVICE_TO_DEPLOY="${1:-both}"
# Frontend authentication: set to "public" to allow unauthenticated access
FRONTEND_AUTH="${FRONTEND_AUTH:-private}"

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
    
    # Verify gcloud is authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        print_error "Not authenticated with gcloud. Run: gcloud auth login"
        exit 1
    fi
    
    # Check if Cloud Run API is enabled
    if ! gcloud services list --enabled --filter="name:run.googleapis.com" --format="value(name)" | grep -q run; then
        print_warn "Cloud Run API not enabled. Enabling now..."
        gcloud services enable run.googleapis.com --project="$PROJECT_ID"
    fi
}

# Deploy Python API
deploy_python_api() {
    print_header "Deploying Python API"
    
    # Check for required environment variables
    if [ -z "${ELASTICSEARCH_ENDPOINT:-}" ]; then
        print_error "ELASTICSEARCH_ENDPOINT not set. Set it before deploying."
        exit 1
    fi
    
    if [ -z "${ELASTICSEARCH_API_KEY:-}" ]; then
        print_error "ELASTICSEARCH_API_KEY not set. Set it before deploying."
        exit 1
    fi
    
    # Build environment variables string
    ENV_VARS="ELASTICSEARCH_ENDPOINT=$ELASTICSEARCH_ENDPOINT"
    ENV_VARS="$ENV_VARS,ELASTICSEARCH_API_KEY=$ELASTICSEARCH_API_KEY"
    ENV_VARS="$ENV_VARS,PYTHON_API_HOST=0.0.0.0"
    # Set Hugging Face cache location (models are pre-downloaded in Docker image)
    ENV_VARS="$ENV_VARS,TRANSFORMERS_CACHE=/app/.cache/huggingface"
    ENV_VARS="$ENV_VARS,HF_HOME=/app/.cache/huggingface"
    ENV_VARS="$ENV_VARS,HF_DATASETS_CACHE=/app/.cache/huggingface"
    # Note: PORT is automatically set by Cloud Run, don't set it manually
    
    # Add optional environment variables
    [ -n "${PYTHON_API_BASE_URL:-}" ] && ENV_VARS="$ENV_VARS,PYTHON_API_BASE_URL=$PYTHON_API_BASE_URL"
    [ -n "${CORS_ORIGINS:-}" ] && ENV_VARS="$ENV_VARS,CORS_ORIGINS=$CORS_ORIGINS"
    [ -n "${API_KEYS:-}" ] && ENV_VARS="$ENV_VARS,API_KEYS=$API_KEYS"
    [ -n "${API_KEY_HEADER:-}" ] && ENV_VARS="$ENV_VARS,API_KEY_HEADER=${API_KEY_HEADER:-X-API-Key}"
    [ -n "${RATE_LIMIT_PER_MINUTE:-}" ] && ENV_VARS="$ENV_VARS,RATE_LIMIT_PER_MINUTE=${RATE_LIMIT_PER_MINUTE:-60}"
    [ -n "${RATE_LIMIT_PER_HOUR:-}" ] && ENV_VARS="$ENV_VARS,RATE_LIMIT_PER_HOUR=${RATE_LIMIT_PER_HOUR:-1000}"
    
    # Add OpenTelemetry environment variables
    # Get service version from git (short commit hash) or use provided/default
    SERVICE_VERSION="${OTEL_SERVICE_VERSION:-}"
    if [ -z "$SERVICE_VERSION" ] && command -v git >/dev/null 2>&1 && git rev-parse --git-dir >/dev/null 2>&1; then
        SERVICE_VERSION=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    fi
    SERVICE_VERSION="${SERVICE_VERSION:-unknown}"
    
    ENV_VARS="$ENV_VARS,OTEL_SERVICE_NAME=${OTEL_SERVICE_NAME:-eui-icon-search-api}"
    ENV_VARS="$ENV_VARS,OTEL_SERVICE_VERSION=$SERVICE_VERSION"
    ENV_VARS="$ENV_VARS,OTEL_EXPORTER_OTLP_ENDPOINT=${OTEL_EXPORTER_OTLP_ENDPOINT:-https://ff29e674b8bb4b06b3e71aaacf84879f.ingest.us-central1.gcp.elastic.cloud:443}"
    ENV_VARS="$ENV_VARS,OTEL_EXPORTER_OTLP_HEADERS=${OTEL_EXPORTER_OTLP_HEADERS:-Authorization=ApiKey ZjlhVnRwb0JITGJzUkpwVXhNR0w6S1htMDVsWHJPbW1yczFMOEo0QTFxdw==}"
    ENV_VARS="$ENV_VARS,OTEL_RESOURCE_ATTRIBUTES=${OTEL_RESOURCE_ATTRIBUTES:-deployment.environment=production}"
    
    print_info "Deploying Python API to Cloud Run..."
    
    # Build Docker image first (required for system dependencies like cairo)
    print_info "Building Docker image..."
    
    # Use Artifact Registry (Container Registry is deprecated)
    ARTIFACT_REGISTRY="${ARTIFACT_REGISTRY:-$REGION-docker.pkg.dev}"
    IMAGE_NAME="$ARTIFACT_REGISTRY/$PROJECT_ID/cloud-run-source-deploy/eui-icon-search-api:latest"
    
    # Ensure Artifact Registry repository exists
    print_info "Ensuring Artifact Registry repository exists..."
    gcloud artifacts repositories create cloud-run-source-deploy \
        --repository-format=docker \
        --location=$REGION \
        --project=$PROJECT_ID \
        2>/dev/null || print_info "Repository already exists or created"
    
    # Authenticate Docker with Artifact Registry
    print_info "Authenticating Docker with Artifact Registry..."
    gcloud auth configure-docker $ARTIFACT_REGISTRY --quiet
    
    # Build for linux/amd64 (Cloud Run requirement)
    # Docker will cache layers that haven't changed, speeding up subsequent builds
    # Set FORCE_REBUILD=true to force a full rebuild without cache
    BUILD_ARGS="--platform linux/amd64"
    if [ "${FORCE_REBUILD:-false}" = "true" ]; then
        BUILD_ARGS="$BUILD_ARGS --no-cache"
        print_info "Building Docker image with --no-cache (forced rebuild)..."
    else
        print_info "Building Docker image (using cache for faster builds)..."
    print_info "Note: If you see 'ModuleNotFoundError: No module named otel_config', ensure otel_config.py is in the project root"
    fi
    docker build $BUILD_ARGS -t "$IMAGE_NAME" -f Dockerfile.python . || {
        print_error "Docker build failed. Make sure Docker is installed and running."
        exit 1
    }
    
    print_info "Pushing Docker image to Artifact Registry..."
    docker push "$IMAGE_NAME" || {
        print_error "Docker push failed. Make sure you have permission to push to Artifact Registry"
        exit 1
    }
    
    print_info "Deploying to Cloud Run..."
    gcloud run deploy eui-icon-search-api \
        --image "$IMAGE_NAME" \
        --platform managed \
        --region "$REGION" \
        --project "$PROJECT_ID" \
        --allow-unauthenticated \
        --set-env-vars "$ENV_VARS" \
        --memory 2Gi \
        --cpu 2 \
        --timeout 300 \
        --max-instances 10 \
        --min-instances 0 \
        --cpu-boost \
        --startup-probe=timeoutSeconds=5,periodSeconds=10,failureThreshold=60,httpGet.port=8080,httpGet.path=/health
    
    print_info "Python API deployed successfully!"
    
    # Get service URL
    SERVICE_URL=$(gcloud run services describe eui-icon-search-api \
        --region "$REGION" \
        --project "$PROJECT_ID" \
        --format="value(status.url)")
    
    print_info "Python API URL: $SERVICE_URL"
    echo "export PYTHON_API_URL=$SERVICE_URL" >> /tmp/eui-deployment-vars.sh
}

# Deploy Frontend
deploy_frontend() {
    print_header "Deploying Frontend"
    
    # Check for required environment variables
    if [ -z "${EMBEDDING_SERVICE_URL:-}" ]; then
        print_error "EMBEDDING_SERVICE_URL not set. Set it before deploying."
        print_info "If Python API was just deployed, it should be in /tmp/eui-deployment-vars.sh"
        exit 1
    fi
    
    # Build environment variables string
    ENV_VARS="EMBEDDING_SERVICE_URL=$EMBEDDING_SERVICE_URL"
    ENV_VARS="$ENV_VARS,NEXT_PUBLIC_EMBEDDING_SERVICE_URL=$EMBEDDING_SERVICE_URL"
    # Note: PORT is automatically set by Cloud Run, don't set it manually
    ENV_VARS="$ENV_VARS,NODE_ENV=production"
    
    # Add optional environment variables
    [ -n "${NEXT_PUBLIC_FRONTEND_URL:-}" ] && ENV_VARS="$ENV_VARS,NEXT_PUBLIC_FRONTEND_URL=$NEXT_PUBLIC_FRONTEND_URL"
    [ -n "${FRONTEND_API_KEY:-}" ] && ENV_VARS="$ENV_VARS,FRONTEND_API_KEY=$FRONTEND_API_KEY"
    [ -n "${ELASTICSEARCH_ENDPOINT:-}" ] && ENV_VARS="$ENV_VARS,ELASTICSEARCH_ENDPOINT=$ELASTICSEARCH_ENDPOINT"
    [ -n "${ELASTICSEARCH_API_KEY:-}" ] && ENV_VARS="$ENV_VARS,ELASTICSEARCH_API_KEY=$ELASTICSEARCH_API_KEY"
    
    # Add OpenTelemetry environment variables
    # Get service version from git (short commit hash) or use provided/default
    SERVICE_VERSION="${OTEL_SERVICE_VERSION:-}"
    if [ -z "$SERVICE_VERSION" ] && command -v git >/dev/null 2>&1 && git rev-parse --git-dir >/dev/null 2>&1; then
        SERVICE_VERSION=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    fi
    SERVICE_VERSION="${SERVICE_VERSION:-unknown}"
    
    # Server-side OpenTelemetry variables
    ENV_VARS="$ENV_VARS,OTEL_SERVICE_NAME=${OTEL_SERVICE_NAME:-eui-icon-search-frontend}"
    ENV_VARS="$ENV_VARS,OTEL_SERVICE_VERSION=$SERVICE_VERSION"
    ENV_VARS="$ENV_VARS,OTEL_EXPORTER_OTLP_ENDPOINT=${OTEL_EXPORTER_OTLP_ENDPOINT:-https://ff29e674b8bb4b06b3e71aaacf84879f.ingest.us-central1.gcp.elastic.cloud:443}"
    ENV_VARS="$ENV_VARS,OTEL_EXPORTER_OTLP_HEADERS=${OTEL_EXPORTER_OTLP_HEADERS:-Authorization=ApiKey ZjlhVnRwb0JITGJzUkpwVXhNR0w6S1htMDVsWHJPbW1yczFMOEo0QTFxdw==}"
    
    # Browser-accessible OpenTelemetry variables (NEXT_PUBLIC_ prefix)
    ENV_VARS="$ENV_VARS,NEXT_PUBLIC_OTEL_SERVICE_NAME=${NEXT_PUBLIC_OTEL_SERVICE_NAME:-${OTEL_SERVICE_NAME:-eui-icon-search-frontend}}"
    ENV_VARS="$ENV_VARS,NEXT_PUBLIC_OTEL_SERVICE_VERSION=$SERVICE_VERSION"
    # Extract deployment.environment from OTEL_RESOURCE_ATTRIBUTES if needed, or use default
    DEPLOYMENT_ENV="${NEXT_PUBLIC_DEPLOYMENT_ENVIRONMENT:-}"
    if [ -z "$DEPLOYMENT_ENV" ]; then
        OTEL_RESOURCE_ATTRS="${OTEL_RESOURCE_ATTRIBUTES:-deployment.environment=production}"
        if [[ "$OTEL_RESOURCE_ATTRS" == *"deployment.environment="* ]]; then
            DEPLOYMENT_ENV=$(echo "$OTEL_RESOURCE_ATTRS" | sed 's/.*deployment.environment=\([^,]*\).*/\1/')
        else
            DEPLOYMENT_ENV="production"
        fi
    fi
    ENV_VARS="$ENV_VARS,NEXT_PUBLIC_DEPLOYMENT_ENVIRONMENT=$DEPLOYMENT_ENV"
    ENV_VARS="$ENV_VARS,NEXT_PUBLIC_ELASTIC_APM_SERVER_URL=${NEXT_PUBLIC_ELASTIC_APM_SERVER_URL:-${OTEL_EXPORTER_OTLP_ENDPOINT:-https://ff29e674b8bb4b06b3e71aaacf84879f.ingest.us-central1.gcp.elastic.cloud:443}}"
    
    print_info "Deploying Frontend to Cloud Run..."
    
    # Determine authentication setting
    if [ "$FRONTEND_AUTH" = "public" ]; then
        AUTH_FLAG="--allow-unauthenticated"
        print_info "Frontend will be publicly accessible"
    else
        AUTH_FLAG="--no-allow-unauthenticated"
        print_info "Frontend will require authentication (private)"
        print_warn "After deployment, grant access with:"
        print_warn "  gcloud run services add-iam-policy-binding eui-icon-search-frontend \\"
        print_warn "    --region=$REGION --project=$PROJECT_ID \\"
        print_warn "    --member='user:YOUR_EMAIL@example.com' \\"
        print_warn "    --role='roles/run.invoker'"
    fi
    
    # Use Dockerfile for frontend (more reliable than buildpacks)
    print_info "Building Docker image for frontend..."
    
    # Use Artifact Registry (Container Registry is deprecated)
    ARTIFACT_REGISTRY="${ARTIFACT_REGISTRY:-$REGION-docker.pkg.dev}"
    IMAGE_NAME="$ARTIFACT_REGISTRY/$PROJECT_ID/cloud-run-source-deploy/eui-icon-search-frontend:latest"
    
    # Ensure Artifact Registry repository exists
    print_info "Ensuring Artifact Registry repository exists..."
    gcloud artifacts repositories create cloud-run-source-deploy \
        --repository-format=docker \
        --location=$REGION \
        --project=$PROJECT_ID \
        2>/dev/null || print_info "Repository already exists or created"
    
    # Authenticate Docker with Artifact Registry
    print_info "Authenticating Docker with Artifact Registry..."
    gcloud auth configure-docker $ARTIFACT_REGISTRY --quiet
    
    # Build for linux/amd64 (Cloud Run requirement)
    docker build --platform linux/amd64 -t "$IMAGE_NAME" -f Dockerfile.frontend . || {
        print_error "Docker build failed. Make sure Docker is installed and running."
        exit 1
    }
    
    print_info "Pushing Docker image to Artifact Registry..."
    docker push "$IMAGE_NAME" || {
        print_error "Docker push failed. Make sure you have permission to push to Artifact Registry"
        exit 1
    }
    
    print_info "Deploying to Cloud Run..."
    gcloud run deploy eui-icon-search-frontend \
        --image "$IMAGE_NAME" \
        --platform managed \
        --region "$REGION" \
        --project "$PROJECT_ID" \
        $AUTH_FLAG \
        --set-env-vars "$ENV_VARS" \
        --memory 1Gi \
        --cpu 1 \
        --timeout 300 \
        --max-instances 5 \
        --min-instances 0 \
        --cpu-boost
    
    print_info "Frontend deployed successfully!"
    
    # Get service URL
    SERVICE_URL=$(gcloud run services describe eui-icon-search-frontend \
        --region "$REGION" \
        --project "$PROJECT_ID" \
        --format="value(status.url)")
    
    print_info "Frontend URL: $SERVICE_URL"
    echo "export FRONTEND_URL=$SERVICE_URL" >> /tmp/eui-deployment-vars.sh
}

# Main deployment logic
main() {
    print_header "EUI Icon Embeddings - Basic Deployment"
    
    check_prerequisites
    
    # Load deployment vars if they exist (from previous deployments)
    if [ -f /tmp/eui-deployment-vars.sh ]; then
        print_info "Loading previous deployment URLs..."
        source /tmp/eui-deployment-vars.sh
    fi
    
    case "$SERVICE_TO_DEPLOY" in
        python)
            deploy_python_api
            ;;
        frontend)
            deploy_frontend
            ;;
        both)
            deploy_python_api
            # Set EMBEDDING_SERVICE_URL for frontend deployment
            if [ -f /tmp/eui-deployment-vars.sh ]; then
                source /tmp/eui-deployment-vars.sh
                export EMBEDDING_SERVICE_URL="$PYTHON_API_URL"
            fi
            deploy_frontend
            ;;
        *)
            print_error "Invalid service: $SERVICE_TO_DEPLOY"
            echo "Usage: $0 [python|frontend|both]"
            exit 1
            ;;
    esac
    
    print_header "Deployment Complete!"
    print_info "Service URLs saved to /tmp/eui-deployment-vars.sh"
    print_info "To use them: source /tmp/eui-deployment-vars.sh"
}

main "$@"

