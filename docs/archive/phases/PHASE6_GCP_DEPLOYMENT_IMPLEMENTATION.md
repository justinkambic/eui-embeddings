# Phase 6: GCP Deployment Configuration - Implementation Summary

## Overview

Phase 6 implements the complete GCP deployment configuration for the EUI Icon Embeddings services, including Cloud Run deployment files, Cloud Build CI/CD configuration, service account setup, secret management, and environment configuration templates.

## Implementation Details

### 6.1 Cloud Run Deployment

#### Files Created/Updated

1. **`cloud-run-python.yaml`** (already existed from Phase 3)
   - Python API Cloud Run service configuration
   - Resource limits: 1-2 vCPU, 1-2 GB memory
   - Environment variables and secret references
   - Health checks (startup and liveness probes)
   - Auto-scaling: 0-10 instances

2. **`cloud-run-frontend.yaml`** (already existed from Phase 3)
   - Next.js frontend Cloud Run service configuration
   - Resource limits: 0.5-1 vCPU, 512MB-1GB memory
   - Environment variables and secret references
   - Health checks
   - Auto-scaling: 0-5 instances

3. **`cloud-run-token-renderer.yaml`** (new)
   - Token renderer Cloud Run service configuration (optional)
   - Higher resource allocation: 1-2 vCPU, 2-4 GB memory
   - Internal-only ingress (not exposed externally)
   - Longer timeout (5 minutes) for rendering operations
   - Auto-scaling: 0-2 instances (low traffic)

### 6.2 Cloud Build Configuration

#### File Created

**`cloudbuild.yaml`**
- Multi-service build and deployment pipeline
- Builds Docker images for Python API and Frontend
- Tags images with commit SHA and `latest`
- Deploys to Cloud Run automatically
- Uses Cloud Build substitutions (`$PROJECT_ID`, `$SHORT_SHA`)
- Configured for parallel builds (Python API and Frontend build simultaneously)
- 20-minute timeout for builds

**Key Features:**
- Parallel image builds for faster CI/CD
- Automatic image tagging with git commit SHA
- Cloud Run deployment integration
- Uses high-CPU machine type for faster builds

### 6.3 Service Account and IAM

#### File Created

**`scripts/setup-service-accounts.sh`**
- Creates service accounts for all services:
  - `eui-python-api-sa` - Python API service account
  - `eui-frontend-sa` - Frontend service account
  - `eui-token-renderer-sa` - Token renderer service account (optional)
- Grants Secret Manager access to service accounts
- Provides commands for individual service account creation
- Lists all service accounts

**Usage:**
```bash
# Create all service accounts
./scripts/setup-service-accounts.sh create-all

# Grant Secret Manager access (if secrets already exist)
./scripts/setup-service-accounts.sh grant-secret-access

# List service accounts
./scripts/setup-service-accounts.sh list
```

**IAM Roles Granted:**
- `roles/secretmanager.secretAccessor` - For accessing secrets in Secret Manager

### 6.4 Secret Management

#### File Created

**`scripts/setup-secrets.sh`**
- Creates and manages secrets in Google Secret Manager:
  - `elasticsearch-api-key` - Elasticsearch API key
  - `api-keys` - JSON array of API keys for Python API authentication
  - `frontend-api-key` - API key for frontend to authenticate with Python API
- Provides interactive creation workflow
- Supports listing, viewing (masked), and deleting secrets
- Enables Secret Manager API automatically if needed

**Usage:**
```bash
# Create all secrets interactively
./scripts/setup-secrets.sh create-all

# Create individual secrets
./scripts/setup-secrets.sh create-elasticsearch-key
./scripts/setup-secrets.sh create-api-keys
./scripts/setup-secrets.sh create-frontend-key

# List secrets
./scripts/setup-secrets.sh list

# View secret (masked)
./scripts/setup-secrets.sh get elasticsearch-api-key

# Delete secret
./scripts/setup-secrets.sh delete secret-name
```

**Secret Format:**
- `elasticsearch-api-key`: Plain text API key
- `api-keys`: JSON array format: `["key1", "key2", "key3"]`
- `frontend-api-key`: Plain text API key (must be one of the keys in `api-keys`)

### 6.5 Environment Configuration

#### Files Created

1. **`.env.example`**
   - Template for all environment variables
   - Includes all services (Python API, Frontend, Token Renderer)
   - Documented with comments
   - Safe to commit to git (no actual secrets)

2. **`.env.development`**
   - Development environment template
   - More lenient rate limits for development
   - Localhost URLs
   - Example API keys for development

3. **`.env.production.example`**
   - Production environment reference
   - Documents where values should be set (Cloud Run vs Secret Manager)
   - Includes security best practices
   - No actual production values

**Environment Variable Categories:**
- **Python API**: `PYTHON_API_HOST`, `PYTHON_API_PORT`, `PYTHON_API_BASE_URL`
- **Frontend**: `NEXT_PUBLIC_EMBEDDING_SERVICE_URL`, `EMBEDDING_SERVICE_URL`, `NEXT_PUBLIC_FRONTEND_URL`
- **Token Renderer**: `TOKEN_RENDERER_HOST`, `TOKEN_RENDERER_PORT`, `TOKEN_RENDERER_BASE_URL`
- **Elasticsearch**: `ELASTICSEARCH_ENDPOINT`, `ELASTICSEARCH_API_KEY`, `ELASTICSEARCH_TIMEOUT`, `ELASTICSEARCH_MAX_RETRIES`
- **Authentication**: `API_KEY_HEADER`, `API_KEYS`, `API_KEYS_SECRET_NAME`, `FRONTEND_API_KEY`
- **CORS**: `CORS_ORIGINS`
- **Rate Limiting**: `RATE_LIMIT_PER_MINUTE`, `RATE_LIMIT_PER_HOUR`, `RATE_LIMIT_BURST`

## Deployment Workflow

### Initial Setup

1. **Set up GCP Project:**
   ```bash
   export PROJECT_ID=your-project-id
   gcloud config set project $PROJECT_ID
   ```

2. **Enable Required APIs:**
   ```bash
   gcloud services enable cloudbuild.googleapis.com
   gcloud services enable run.googleapis.com
   gcloud services enable secretmanager.googleapis.com
   gcloud services enable iam.googleapis.com
   ```

3. **Create Service Accounts:**
   ```bash
   ./scripts/setup-service-accounts.sh create-all
   ```

4. **Create Secrets:**
   ```bash
   ./scripts/setup-secrets.sh create-all
   ```

5. **Grant Secret Access:**
   ```bash
   ./scripts/setup-service-accounts.sh grant-secret-access
   ```

6. **Update Cloud Run YAML Files:**
   - Replace `PROJECT_ID` placeholders with actual project ID
   - Update domain names (`icons.example.com`, `api.icons.example.com`)
   - Update Elasticsearch endpoint
   - Verify service account names match created accounts

### Building and Deploying

#### Option 1: Cloud Build (Recommended)

```bash
# Submit build to Cloud Build
gcloud builds submit --config=cloudbuild.yaml

# Or trigger via Cloud Build triggers (set up in GCP Console)
```

#### Option 2: Manual Build and Deploy

```bash
# Build images locally
docker build -t gcr.io/$PROJECT_ID/eui-python-api:latest -f Dockerfile.python .
docker build -t gcr.io/$PROJECT_ID/eui-frontend:latest -f Dockerfile.frontend .

# Push to Container Registry
docker push gcr.io/$PROJECT_ID/eui-python-api:latest
docker push gcr.io/$PROJECT_ID/eui-frontend:latest

# Deploy to Cloud Run
gcloud run services replace cloud-run-python.yaml --region=us-central1
gcloud run services replace cloud-run-frontend.yaml --region=us-central1
```

### Updating Secrets

```bash
# Update API keys
./scripts/setup-secrets.sh create-api-keys

# Update Elasticsearch key
./scripts/setup-secrets.sh create-elasticsearch-key

# Update frontend key
./scripts/setup-secrets.sh create-frontend-key
```

## Security Considerations

1. **Secrets Management:**
   - All sensitive values stored in Secret Manager
   - Service accounts have minimal required permissions
   - Secrets are not exposed in environment variables

2. **Service Accounts:**
   - Each service has its own service account
   - Principle of least privilege applied
   - Only granted access to required secrets

3. **Network Security:**
   - Token renderer uses internal-only ingress
   - Frontend and API can use internal URLs for better performance
   - CORS configured to allow only frontend domain

4. **Resource Limits:**
   - Appropriate CPU and memory limits set
   - Prevents resource exhaustion attacks
   - Auto-scaling prevents over-provisioning

## Verification

Run the verification script to check Phase 6 implementation:

```bash
./scripts/verify-phase6.sh
```

The script checks:
- Cloud Build configuration file exists
- Cloud Run YAML files exist and are valid
- Setup scripts exist and are executable
- Environment configuration files exist
- Service account and secret management scripts are functional

## Next Steps

After Phase 6 completion:

1. **Phase 7: Production Hardening**
   - Structured logging
   - Monitoring and alerting
   - Error handling improvements
   - Input validation
   - Caching strategy

2. **Phase 8: MCP Server Container Distribution**
   - Build and publish MCP server Docker image
   - Documentation for Docker usage

3. **Phase 9: Documentation and Deployment Guides**
   - Complete deployment documentation
   - CI/CD pipeline setup
   - Migration guide

## Files Created/Modified

### New Files:
- `cloudbuild.yaml` - Cloud Build CI/CD configuration
- `cloud-run-token-renderer.yaml` - Token renderer Cloud Run configuration
- `scripts/setup-secrets.sh` - Secret management script
- `scripts/setup-service-accounts.sh` - Service account and IAM setup script
- `.env.example` - Environment variable template
- `.env.development` - Development environment template
- `.env.production.example` - Production environment reference
- `docs/PHASE6_GCP_DEPLOYMENT_IMPLEMENTATION.md` - This file

### Updated Files:
- `cloud-run-python.yaml` - Already existed from Phase 3 (no changes needed)
- `cloud-run-frontend.yaml` - Already existed from Phase 3 (no changes needed)

## Testing

### Local Testing

1. Test setup scripts locally (dry-run where possible):
   ```bash
   # Test secret creation (will prompt for values)
   ./scripts/setup-secrets.sh create-all

   # Test service account creation
   ./scripts/setup-service-accounts.sh create-all
   ```

2. Validate Cloud Run YAML files:
   ```bash
   # Check YAML syntax
   yamllint cloud-run-*.yaml cloudbuild.yaml
   ```

3. Test Cloud Build configuration:
   ```bash
   # Validate Cloud Build config
   gcloud builds submit --config=cloudbuild.yaml --dry-run
   ```

### Production Testing

1. Deploy to a test/staging project first
2. Verify service accounts have correct permissions
3. Verify secrets are accessible
4. Test Cloud Run deployments
5. Verify health checks work
6. Test service-to-service communication

## Troubleshooting

### Common Issues

1. **Service account permissions:**
   - Ensure service accounts have `roles/secretmanager.secretAccessor`
   - Check IAM bindings: `gcloud projects get-iam-policy $PROJECT_ID`

2. **Secret access:**
   - Verify secrets exist: `gcloud secrets list`
   - Check secret IAM: `gcloud secrets get-iam-policy secret-name`

3. **Cloud Build failures:**
   - Check build logs: `gcloud builds list`
   - Verify Dockerfile syntax
   - Check image push permissions

4. **Cloud Run deployment:**
   - Verify service account exists
   - Check secret references in YAML
   - Verify image exists in Container Registry

## References

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud Build Documentation](https://cloud.google.com/build/docs)
- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [Service Accounts Documentation](https://cloud.google.com/iam/docs/service-accounts)

