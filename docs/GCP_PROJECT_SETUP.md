# GCP Project Setup Guide

This guide walks you through setting up your Google Cloud Platform (GCP) project for deploying the EUI Icon Embeddings services.

## Prerequisites

1. **Google Cloud Account**: You need a Google Cloud account with billing enabled
2. **gcloud CLI**: Install the [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
3. **Project Access**: You need access to a GCP project with appropriate permissions
   - **If you can't create projects**: You'll need an existing project with these IAM roles:
     - `roles/run.admin` - Deploy Cloud Run services
     - `roles/cloudbuild.builds.editor` - Trigger Cloud Build
     - `roles/secretmanager.admin` - Manage secrets
     - `roles/iam.serviceAccountAdmin` - Create service accounts
   - **If you can create projects**: You'll need `roles/owner` or `roles/editor`

## Step 1: Get Access to a GCP Project

### Option A: Use an Existing Project (Recommended if you can't create projects)

If you don't have permission to create projects, you'll need to use an existing project that you have access to:

```bash
# List projects you have access to
gcloud projects list

# Set as active project
gcloud config set project YOUR_PROJECT_ID

# Verify you have necessary permissions
gcloud projects get-iam-policy YOUR_PROJECT_ID --flatten="bindings[].members" \
  --filter="bindings.members:user:YOUR_EMAIL@example.com"
```

**Required IAM Roles:**
You'll need at least one of these roles:
- `roles/owner` (full access)
- `roles/editor` (can create resources)
- `roles/run.admin` (can deploy Cloud Run services)
- `roles/cloudbuild.builds.editor` (can trigger Cloud Build)
- `roles/secretmanager.admin` (can manage secrets)
- `roles/iam.serviceAccountAdmin` (can create service accounts)

**If you don't have sufficient permissions**, ask your GCP admin to grant you the necessary roles.

### Option B: Request Project Creation

If you need a new project, contact your GCP organization administrator to:
1. Create a new project for you
2. Grant you the necessary IAM roles (see above)
3. Enable billing on the project

**Information to provide to your admin:**
- Project name: "EUI Icon Embeddings"
- Required APIs: Cloud Build, Cloud Run, Secret Manager, IAM, Container Registry
- Required IAM roles: `roles/run.admin`, `roles/cloudbuild.builds.editor`, `roles/secretmanager.admin`, `roles/iam.serviceAccountAdmin`

### Option C: Create a New Project (if you have permissions)

```bash
# Create a new project
gcloud projects create eui-icon-embeddings --name="EUI Icon Embeddings"

# Set as active project
gcloud config set project eui-icon-embeddings

# Enable billing (required for Cloud Run)
# Note: You'll need to do this in the Cloud Console:
# https://console.cloud.google.com/billing
```

**Save your project ID:**
```bash
export PROJECT_ID=$(gcloud config get-value project)
echo "Project ID: $PROJECT_ID"
```

## Step 2: Enable Required APIs

Enable the necessary Google Cloud APIs:

```bash
# Enable Cloud Build API
gcloud services enable cloudbuild.googleapis.com

# Enable Cloud Run API
gcloud services enable run.googleapis.com

# Enable Secret Manager API
gcloud services enable secretmanager.googleapis.com

# Enable IAM API
gcloud services enable iam.googleapis.com

# Enable Container Registry API (for storing Docker images)
gcloud services enable containerregistry.googleapis.com

# Verify APIs are enabled
gcloud services list --enabled
```

**Note**: If you get permission errors, you may need to ask your GCP admin to enable these APIs. They can do this via:
- Cloud Console: https://console.cloud.google.com/apis/library
- Or grant you `roles/servicemanagement.admin` role temporarily

## Step 3: Set Up Authentication

### Authenticate gcloud CLI

```bash
# Login to your Google account
gcloud auth login

# Set default account (if you have multiple accounts)
gcloud config set account YOUR_EMAIL@example.com

# Verify authentication
gcloud auth list
```

### Set Up Application Default Credentials (for local development)

```bash
# Set up ADC for local development/testing
gcloud auth application-default login
```

## Step 4: Configure Billing

**Important**: Cloud Run requires billing to be enabled, even for the free tier.

1. Go to [Cloud Console Billing](https://console.cloud.google.com/billing)
2. Link a billing account to your project
3. Verify billing is enabled:
   ```bash
   gcloud billing projects describe $PROJECT_ID
   ```

## Step 5: Create Service Accounts

Run the service account setup script:

```bash
# Make sure you're in the project root
cd /path/to/eui-embeddings

# Set PROJECT_ID environment variable
export PROJECT_ID=$(gcloud config get-value project)

# Create all service accounts
./scripts/setup-service-accounts.sh create-all
```

This creates:
- `eui-python-api-sa` - Service account for Python API
- `eui-frontend-sa` - Service account for Frontend
- `eui-token-renderer-sa` - Service account for Token Renderer (optional)

**Expected output:**
```
[INFO] Using project: your-project-id
[INFO] Creating Python API service account...
[INFO] Service account eui-python-api-sa created successfully
[INFO] Creating Frontend service account...
[INFO] Service account eui-frontend-sa created successfully
[INFO] Creating Token Renderer service account...
[INFO] Service account eui-token-renderer-sa created successfully
```

## Step 6: Create Secrets

Run the secrets setup script:

```bash
# Create all secrets interactively
./scripts/setup-secrets.sh create-all
```

This will prompt you for:
1. **Elasticsearch API Key**: Your Elasticsearch cluster API key
2. **API Keys**: One or more API keys for Python API authentication (enter one per line, empty line to finish)
3. **Frontend API Key**: The API key the frontend will use (must be one of the API keys from step 2)

**Example:**
```
[INFO] Creating Elasticsearch API key secret...
Enter Elasticsearch API key: VnVhQ2ZHY0JDZGJrU...

[INFO] Creating API keys secret...
Enter API keys (one per line, empty line to finish):
ZwsIy-4nzxTmVePT-Ja9n9Ug4EbpVI2i8PUph6zdZsw
<Press Enter to finish>

[INFO] Creating frontend API key secret...
Enter frontend API key (must be one of the API keys): ZwsIy-4nzxTmVePT-Ja9n9Ug4EbpVI2i8PUph6zdZsw
```

**Verify secrets were created:**
```bash
./scripts/setup-secrets.sh list
```

## Step 7: Grant Secret Access to Service Accounts

Grant the service accounts permission to access secrets:

```bash
./scripts/setup-service-accounts.sh grant-secret-access
```

This grants:
- Python API service account → Access to `elasticsearch-api-key` and `api-keys`
- Frontend service account → Access to `elasticsearch-api-key` and `frontend-api-key`

## Step 8: Update Cloud Run Configuration Files

Edit the Cloud Run YAML files to replace placeholders:

### Update `cloud-run-python.yaml`

```bash
# Replace PROJECT_ID placeholders
sed -i '' "s/PROJECT_ID/$PROJECT_ID/g" cloud-run-python.yaml

# Update domain names (replace with your actual domains)
sed -i '' "s/icons.example.com/your-domain.com/g" cloud-run-python.yaml
sed -i '' "s/api.icons.example.com/api.your-domain.com/g" cloud-run-python.yaml

# Update Elasticsearch endpoint
sed -i '' "s|https://your-cluster.es.amazonaws.com|https://your-actual-cluster.es.amazonaws.com|g" cloud-run-python.yaml
```

### Update `cloud-run-frontend.yaml`

```bash
# Replace PROJECT_ID placeholders
sed -i '' "s/PROJECT_ID/$PROJECT_ID/g" cloud-run-frontend.yaml

# Update domain names
sed -i '' "s/icons.example.com/your-domain.com/g" cloud-run-frontend.yaml
sed -i '' "s/api.icons.example.com/api.your-domain.com/g" cloud-run-frontend.yaml

# Update Elasticsearch endpoint
sed -i '' "s|https://your-cluster.es.amazonaws.com|https://your-actual-cluster.es.amazonaws.com|g" cloud-run-frontend.yaml
```

**Or edit manually** with your preferred editor:
- Replace all `PROJECT_ID` with your actual project ID
- Replace `icons.example.com` with your frontend domain
- Replace `api.icons.example.com` with your API domain
- Replace Elasticsearch endpoint with your actual endpoint

## Step 9: Verify Setup

Run the verification script:

```bash
./scripts/verify-phase6.sh
```

This checks:
- Cloud Build configuration
- Cloud Run YAML files
- Setup scripts
- Environment configuration files
- Documentation

**Expected output:**
```
✓ All required checks passed!
```

## Step 10: Build and Deploy (Optional - Test Build)

Before deploying, you can test building the Docker images:

```bash
# Build Python API image locally (for testing)
docker build -t gcr.io/$PROJECT_ID/eui-python-api:test -f Dockerfile.python .

# Build Frontend image locally (for testing)
docker build -t gcr.io/$PROJECT_ID/eui-frontend:test -f Dockerfile.frontend .

# Test that images build successfully
```

## Step 11: Deploy to Cloud Run

### Option A: Using Cloud Build (Recommended)

```bash
# Submit build to Cloud Build
gcloud builds submit --config=cloudbuild.yaml

# This will:
# 1. Build Docker images
# 2. Push to Container Registry
# 3. Deploy to Cloud Run
```

### Option B: Manual Deployment

```bash
# Build and push images
docker build -t gcr.io/$PROJECT_ID/eui-python-api:latest -f Dockerfile.python .
docker build -t gcr.io/$PROJECT_ID/eui-frontend:latest -f Dockerfile.frontend .
docker push gcr.io/$PROJECT_ID/eui-python-api:latest
docker push gcr.io/$PROJECT_ID/eui-frontend:latest

# Deploy to Cloud Run
gcloud run services replace cloud-run-python.yaml --region=us-central1
gcloud run services replace cloud-run-frontend.yaml --region=us-central1
```

## Step 12: Verify Deployment

### Check Service Status

```bash
# List Cloud Run services
gcloud run services list --region=us-central1

# Get service URLs
gcloud run services describe eui-python-api --region=us-central1 --format="value(status.url)"
gcloud run services describe eui-frontend --region=us-central1 --format="value(status.url)"
```

### Test Health Endpoints

```bash
# Test Python API health
curl https://YOUR-PYTHON-API-URL/health

# Test Frontend
curl https://YOUR-FRONTEND-URL/
```

## Troubleshooting

### Common Issues

#### 1. "Cannot create project" or "Permission denied" errors

**If you can't create projects:**
- Use an existing project you have access to (see Step 1, Option A)
- Or request project creation from your GCP admin (see `docs/GCP_ADMIN_REQUEST.md`)

**If you get permission errors:**
- Verify your IAM roles: `gcloud projects get-iam-policy $PROJECT_ID --flatten="bindings[].members" --filter="bindings.members:user:YOUR_EMAIL"`
- Request additional roles from your GCP admin
- See `docs/GCP_ADMIN_REQUEST.md` for a request template

#### 2. "Permission denied" errors

**Solution**: Ensure you have the necessary IAM roles:
```bash
# Grant yourself necessary roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="user:YOUR_EMAIL@example.com" \
  --role="roles/owner"
```

#### 2. "API not enabled" errors

**Solution**: Enable the required API:
```bash
gcloud services enable API_NAME.googleapis.com
```

#### 3. "Billing not enabled" errors

**Solution**: Link a billing account in the Cloud Console:
- Go to https://console.cloud.google.com/billing
- Link a billing account to your project

#### 4. "Secret not found" errors

**Solution**: Verify secrets exist and service accounts have access:
```bash
# List secrets
gcloud secrets list

# Check secret IAM policy
gcloud secrets get-iam-policy elasticsearch-api-key
```

#### 5. "Service account not found" errors

**Solution**: Verify service accounts exist:
```bash
# List service accounts
gcloud iam service-accounts list

# Check service account exists
gcloud iam service-accounts describe eui-python-api-sa@$PROJECT_ID.iam.gserviceaccount.com
```

### Getting Help

- Check Cloud Build logs:
  ```bash
  gcloud builds list --limit=5
  gcloud builds log BUILD_ID
  ```

- Check Cloud Run logs:
  ```bash
  gcloud run services logs read eui-python-api --region=us-central1
  ```

- Check service status:
  ```bash
  gcloud run services describe eui-python-api --region=us-central1
  ```

## Next Steps

After setup is complete:

1. **Configure HTTPS** (Phase 3): Set up Cloud Load Balancer with SSL certificates
2. **Set up Monitoring** (Phase 7): Configure Cloud Monitoring and alerting
3. **Set up CI/CD** (Phase 9): Configure Cloud Build triggers for automatic deployments

## Quick Reference

### Essential Commands

```bash
# Set project
export PROJECT_ID=$(gcloud config get-value project)

# Create service accounts
./scripts/setup-service-accounts.sh create-all

# Create secrets
./scripts/setup-secrets.sh create-all

# Grant secret access
./scripts/setup-service-accounts.sh grant-secret-access

# Verify setup
./scripts/verify-phase6.sh

# Deploy
gcloud builds submit --config=cloudbuild.yaml
```

### Useful Links

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud Build Documentation](https://cloud.google.com/build/docs)
- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [Service Accounts Documentation](https://cloud.google.com/iam/docs/service-accounts)

