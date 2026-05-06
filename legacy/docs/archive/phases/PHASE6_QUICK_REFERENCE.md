# Phase 6: GCP Deployment Configuration - Quick Reference

## Quick Start

### 0. Get Project Access (if you can't create projects)

If you don't have permission to create projects:
1. Use an existing project you have access to, OR
2. Request project creation from your GCP admin (see `docs/GCP_ADMIN_REQUEST.md`)

### 1. Initial Setup

```bash
# Set project ID (use existing project)
export PROJECT_ID=your-existing-project-id
gcloud config set project $PROJECT_ID

# Verify you have access
gcloud projects describe $PROJECT_ID

# Enable required APIs (may require admin if APIs aren't enabled)
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable iam.googleapis.com
```

### 2. Create Service Accounts

```bash
./scripts/setup-service-accounts.sh create-all
```

### 3. Create Secrets

```bash
./scripts/setup-secrets.sh create-all
```

### 4. Grant Secret Access

```bash
./scripts/setup-service-accounts.sh grant-secret-access
```

### 5. Update Cloud Run YAML Files

Edit `cloud-run-python.yaml` and `cloud-run-frontend.yaml`:
- Replace `PROJECT_ID` with your actual project ID
- Update domain names (`icons.example.com`, `api.icons.example.com`)
- Update Elasticsearch endpoint
- Verify service account names match

### 6. Build and Deploy

```bash
# Option 1: Cloud Build (recommended)
gcloud builds submit --config=cloudbuild.yaml

# Option 2: Manual build and deploy
docker build -t gcr.io/$PROJECT_ID/eui-python-api:latest -f Dockerfile.python .
docker build -t gcr.io/$PROJECT_ID/eui-frontend:latest -f Dockerfile.frontend .
docker push gcr.io/$PROJECT_ID/eui-python-api:latest
docker push gcr.io/$PROJECT_ID/eui-frontend:latest
gcloud run services replace cloud-run-python.yaml --region=us-central1
gcloud run services replace cloud-run-frontend.yaml --region=us-central1
```

## Common Commands

### Service Accounts

```bash
# List service accounts
./scripts/setup-service-accounts.sh list

# Create individual service account
./scripts/setup-service-accounts.sh create-python-sa
./scripts/setup-service-accounts.sh create-frontend-sa
```

### Secrets

```bash
# List secrets
./scripts/setup-secrets.sh list

# View secret (masked)
./scripts/setup-secrets.sh get elasticsearch-api-key

# Update API keys
./scripts/setup-secrets.sh create-api-keys

# Delete secret
./scripts/setup-secrets.sh delete secret-name
```

### Verification

```bash
# Verify Phase 6 implementation
./scripts/verify-phase6.sh
```

## File Reference

### Cloud Run Configurations
- `cloud-run-python.yaml` - Python API service
- `cloud-run-frontend.yaml` - Frontend service
- `cloud-run-token-renderer.yaml` - Token renderer (optional)

### CI/CD
- `cloudbuild.yaml` - Cloud Build configuration

### Setup Scripts
- `scripts/setup-secrets.sh` - Secret management
- `scripts/setup-service-accounts.sh` - Service account and IAM setup

### Environment Files
- `.env.example` - Environment variable template
- `.env.production.example` - Production environment reference

## Troubleshooting

### Service Account Permissions

```bash
# Check service account IAM bindings
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:eui-python-api-sa@$PROJECT_ID.iam.gserviceaccount.com"
```

### Secret Access

```bash
# Check secret IAM policy
gcloud secrets get-iam-policy elasticsearch-api-key

# List all secrets
gcloud secrets list
```

### Cloud Build

```bash
# View build logs
gcloud builds list --limit=5
gcloud builds log BUILD_ID

# Check build status
gcloud builds describe BUILD_ID
```

### Cloud Run

```bash
# View service logs
gcloud run services logs read eui-python-api --region=us-central1

# Check service status
gcloud run services describe eui-python-api --region=us-central1

# View revisions
gcloud run revisions list --service=eui-python-api --region=us-central1
```

## Next Steps

After Phase 6:
1. Set up Cloud Load Balancer (Phase 3 - HTTPS)
2. Configure monitoring and alerting (Phase 7)
3. Set up CI/CD triggers (Phase 9)

