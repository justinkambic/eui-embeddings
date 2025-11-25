# Cloud Run Deployment Guide

This guide shows you how to deploy the EUI Icon Embeddings services to Cloud Run using the simplest possible approach - no service accounts, no Secret Manager, just direct container deployment.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Detailed Deployment Steps](#detailed-deployment-steps)
4. [Configuration Options](#configuration-options)
5. [Security and Authentication](#security-and-authentication)
6. [CORS Setup](#cors-setup)
7. [Public Access Configuration](#public-access-configuration)
8. [Cost Analysis](#cost-analysis)
9. [Updating Services](#updating-services)
10. [Cleanup](#cleanup)
11. [Troubleshooting](#troubleshooting)

## Prerequisites

1. **gcloud CLI** installed and authenticated
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

2. **Docker** (optional - Cloud Run can build from source)
   - If you have Docker, you can build locally
   - If not, Cloud Run will build from source automatically

3. **Project Access**
   - Access to a GCP project
   - Permission to deploy Cloud Run services
   - Cloud Run API enabled (script will enable it if needed)

## Quick Start

### 1. Set Environment Variables

```bash
# Copy the example file
cp .env.basic .env.local

# Edit .env.local with your values
# At minimum, set:
export PROJECT_ID="your-project-id"
export ELASTICSEARCH_ENDPOINT="https://your-cluster.es.amazonaws.com"
export ELASTICSEARCH_API_KEY="your-api-key"

# Optional: API keys (comma-separated)
export API_KEYS="key1,key2,key3"
export FRONTEND_API_KEY="key1"

# Optional: CORS
export CORS_ORIGINS="https://your-domain.com"

# Source the file
source .env.local
```

### 2. Deploy Services

```bash
# Make script executable
chmod +x scripts/deploy/deploy-basic.sh

# Deploy both services (frontend will be private by default)
./scripts/deploy/deploy-basic.sh both

# Or deploy individually
./scripts/deploy/deploy-basic.sh python
./scripts/deploy/deploy-basic.sh frontend

# To make frontend publicly accessible:
FRONTEND_AUTH=public ./scripts/deploy/deploy-basic.sh frontend
```

### 3. Get Service URLs

After deployment, service URLs are saved to `/tmp/eui-deployment-vars.sh`:

```bash
source /tmp/eui-deployment-vars.sh
echo "Python API: $PYTHON_API_URL"
echo "Frontend: $FRONTEND_URL"
```

### 4. Test Deployment

```bash
# Test Python API health endpoint
curl $PYTHON_API_URL/health

# Test Frontend
curl $FRONTEND_URL
```

## Detailed Deployment Steps

### Step 1: Configure Environment Variables

Edit `.env.basic` or create `.env.local` with your configuration:

```bash
# Required
export PROJECT_ID="elastic-observability"
export ELASTICSEARCH_ENDPOINT="https://your-cluster.es.amazonaws.com"
export ELASTICSEARCH_API_KEY="your-api-key"

# Optional: API Keys (comma-separated)
export API_KEYS="key1,key2,key3"
export FRONTEND_API_KEY="key1"

# Optional: CORS (comma-separated origins)
export CORS_ORIGINS="https://your-domain.com"

# Source the file
source .env.local
```

### Step 2: Deploy Python API

```bash
./scripts/deploy/deploy-basic.sh python
```

This will:
- Build the Docker image from source (or use local Docker if available)
- Deploy to Cloud Run as `eui-python-api`
- Configure environment variables
- Make the service publicly accessible (API key still required for operations)

**Expected output:**
```
[INFO] Deploying Python API to Cloud Run...
Service [eui-python-api] revision [eui-python-api-00001-abc] has been deployed
[INFO] Python API URL: https://eui-python-api-xxxxx-uc.a.run.app
```

### Step 3: Deploy Frontend

**By default, the frontend is deployed as private** (requires authentication).

If deploying both together, the script automatically sets `EMBEDDING_SERVICE_URL`. Otherwise:

```bash
# Set the Python API URL
export EMBEDDING_SERVICE_URL="https://eui-python-api-xxxxx-uc.a.run.app"

# Deploy frontend (private by default)
./scripts/deploy/deploy-basic.sh frontend

# Or make it publicly accessible
FRONTEND_AUTH=public ./scripts/deploy/deploy-basic.sh frontend
```

Or deploy both at once:

```bash
# Both services (frontend private)
./scripts/deploy/deploy-basic.sh both

# Or with public frontend
FRONTEND_AUTH=public ./scripts/deploy/deploy-basic.sh both
```

**After deploying a private frontend**, grant access to users:

```bash
# Grant access to a user
gcloud run services add-iam-policy-binding eui-frontend \
  --region=us-central1 \
  --project=$PROJECT_ID \
  --member="user:someone@example.com" \
  --role="roles/run.invoker"

# Or use gcloud proxy for testing
gcloud run services proxy eui-frontend \
  --region=us-central1 \
  --project=$PROJECT_ID \
  --port=8080
```

## Configuration Options

### Environment Variables

All environment variables are passed directly to Cloud Run containers. See `docs/api/environment-variables.md` for all available options.

**Required:**
- `PROJECT_ID` - GCP project ID
- `ELASTICSEARCH_ENDPOINT` - Elasticsearch cluster URL
- `ELASTICSEARCH_API_KEY` - Elasticsearch API key

**Optional:**
- `API_KEYS` - Comma-separated API keys for authentication
- `FRONTEND_API_KEY` - API key for frontend to use
- `CORS_ORIGINS` - Allowed CORS origins
- `PYTHON_API_BASE_URL` - Base URL for API (for CORS)
- `RATE_LIMIT_PER_MINUTE` - Rate limit per minute (default: 60)
- `RATE_LIMIT_PER_HOUR` - Rate limit per hour (default: 1000)

### Resource Configuration

The script sets these defaults (can be modified in `scripts/deploy-basic.sh`):

**Python API:**
- Memory: 2GB
- CPU: 2 vCPU
- Timeout: 60 seconds
- Max instances: 10
- Min instances: 0 (scales to zero)

**Frontend:**
- Memory: 1GB
- CPU: 1 vCPU
- Timeout: 60 seconds
- Max instances: 5
- Min instances: 0 (scales to zero)

## Security and Authentication

### HTTPS - Automatic ✅

**Good news**: HTTPS works automatically!

Cloud Run provides HTTPS for all services via their default domain:
- Python API: `https://eui-python-api-xxxxx-uc.a.run.app`
- Frontend: `https://eui-frontend-xxxxx-uc.a.run.app`

**All traffic is encrypted** - Cloud Run terminates TLS automatically. You don't need to configure SSL certificates.

### Authentication - Two Levels

#### 1. Cloud Run Level Authentication

**Current Status**: Services are **publicly accessible** (`--allow-unauthenticated`)

This means:
- ✅ Anyone with the URL can access the service
- ✅ No Google Cloud authentication required
- ⚠️ Services are exposed to the internet

**To enable Cloud Run authentication** (make services private):

```bash
# Remove --allow-unauthenticated and add --no-allow-unauthenticated
gcloud run services update eui-python-api \
  --region=us-central1 \
  --project=$PROJECT_ID \
  --no-allow-unauthenticated

# Then users need to authenticate with gcloud or use service account
gcloud run services proxy eui-python-api --region=us-central1
```

**Recommendation**: Keep `--allow-unauthenticated` and use application-level API key authentication instead (see below).

#### 2. Application-Level API Key Authentication

**Status**: Works if `API_KEYS` environment variable is set ✅

The Python API has built-in API key authentication:

```bash
# When deploying, set API keys
export API_KEYS="key1,key2,key3"
export FRONTEND_API_KEY="key1"
./scripts/deploy/deploy-basic.sh both
```

**How it works:**
- Python API requires `X-API-Key` header for all endpoints (except `/health`)
- Frontend includes `FRONTEND_API_KEY` in requests to Python API
- Rate limiting tracks by API key

**Example request:**
```bash
# Without API key - will fail
curl https://eui-python-api-xxxxx-uc.a.run.app/search

# With API key - works
curl https://eui-python-api-xxxxx-uc.a.run.app/search \
  -H "X-API-Key: key1"
```

### Browser Experience with API Keys

When you set `FRONTEND_API_KEY`, the browser experience is **seamless** - users don't need to know about API keys at all!

**Request Flow:**
```
Browser (User)
  ↓
  fetch('/api/search', { ... })  ← No API key needed here!
  ↓
Next.js API Route (Server-side)
  ↓
  Reads FRONTEND_API_KEY from process.env
  ↓
  Adds X-API-Key header automatically
  ↓
Python API (Cloud Run)
  ↓
  Validates API key
  ↓
  Returns response
```

**Key Points:**
1. **Browser never sees the API key** - it's only used server-side
2. **No user interaction needed** - API key is added automatically
3. **Standard fetch requests** - just like any other API call
4. **Secure** - API key stays on the server, never exposed to browser

### Security Status Summary

| Feature | Status | Notes |
|---------|--------|-------|
| HTTPS | ✅ Automatic | Cloud Run provides HTTPS via `*.run.app` domains |
| TLS Encryption | ✅ Enabled | All traffic encrypted in transit |
| Cloud Run Auth | ⚠️ Disabled | Services are publicly accessible |
| API Key Auth | ✅ Available | Works if `API_KEYS` env var is set |
| Rate Limiting | ✅ Enabled | Configured in application |
| CORS | ⚠️ Basic | Set via `CORS_ORIGINS` env var (default: `*`) |

### Recommended Security Configuration

#### For Development/Testing

```bash
# Basic security - API keys only
export API_KEYS="dev-key-123"
export FRONTEND_API_KEY="dev-key-123"
export CORS_ORIGINS="*"  # Allow all origins
./scripts/deploy/deploy-basic.sh both
```

**Security level**: Medium
- ✅ HTTPS enabled
- ✅ API key authentication
- ⚠️ Publicly accessible (anyone with URL + API key)
- ⚠️ CORS allows all origins

#### For Production

**Option 1: API Keys + Restricted CORS** (Better)

```bash
export API_KEYS="prod-key-abc123,prod-key-def456"
export FRONTEND_API_KEY="prod-key-abc123"
export CORS_ORIGINS="https://yourdomain.com,https://www.yourdomain.com"
export PYTHON_API_BASE_URL="https://api.yourdomain.com"
./scripts/deploy/deploy-basic.sh both
```

**Security level**: Good
- ✅ HTTPS enabled
- ✅ API key authentication
- ✅ Restricted CORS
- ⚠️ Still publicly accessible (but requires API key)

**Option 2: Cloud Run Auth + API Keys** (Best)

```bash
# Deploy with API keys
export API_KEYS="prod-key-abc123"
export FRONTEND_API_KEY="prod-key-abc123"
./scripts/deploy/deploy-basic.sh both

# Then make services private
gcloud run services update eui-python-api \
  --region=us-central1 \
  --project=$PROJECT_ID \
  --no-allow-unauthenticated

gcloud run services update eui-frontend \
  --region=us-central1 \
  --project=$PROJECT_ID \
  --no-allow-unauthenticated
```

**Security level**: Excellent
- ✅ HTTPS enabled
- ✅ Cloud Run authentication required
- ✅ API key authentication (double layer)
- ✅ Not publicly accessible

## CORS Setup

### The CORS Challenge

**Problem:** 
- Python API needs `CORS_ORIGINS` to allow frontend requests
- Frontend URL is only known after deployment
- But Python API is deployed first (when deploying both together)

### Recommended Workflow

**For First-Time Deployment:**

```bash
# 1. Set required variables
export PROJECT_ID="elastic-observability"
export ELASTICSEARCH_ENDPOINT="https://your-cluster.es.amazonaws.com"
export ELASTICSEARCH_API_KEY="your-key"
export API_KEYS="your-api-key"
export FRONTEND_API_KEY="your-api-key"

# 2. Deploy both services
./scripts/deploy/deploy-basic.sh both

# 3. Get service URLs
source /tmp/eui-deployment-vars.sh

# 4. Update Python API with frontend CORS
gcloud run services update eui-python-api \
  --region=us-central1 \
  --project=$PROJECT_ID \
  --update-env-vars CORS_ORIGINS=$FRONTEND_URL

# 5. Verify CORS is set
gcloud run services describe eui-python-api \
  --region=us-central1 \
  --project=$PROJECT_ID \
  --format="value(spec.template.spec.containers[0].env)" | grep CORS
```

**For Updates/Re-deployments:**

If you're updating services and already know the URLs:

```bash
# Set CORS before deploying
export CORS_ORIGINS="https://eui-frontend-xxxxx-uc.a.run.app"
./scripts/deploy/deploy-basic.sh python
```

### What Happens Without CORS?

**If CORS_ORIGINS is not set:**
- Default: `*` (allows all origins)
- Frontend can call Python API
- Less secure, but works

**If CORS_ORIGINS is set incorrectly:**
- Browser will block frontend requests
- You'll see CORS errors in browser console
- API calls will fail

## Public Access Configuration

### Current Status: Private by Default

**The frontend is deployed as private** (requires authentication) by default.

- **Frontend**: Private (requires Google Cloud authentication) - **Default**
- **Python API**: Public (but requires API key for operations)

You can make the frontend public by setting `FRONTEND_AUTH=public` when deploying.

### Access Control Options

#### Option 1: Keep Private (Default Setup)

**Default behavior:**
- Frontend: Private, requires Google Cloud authentication
- API: Public but requires API key for operations

**Best for:**
- Internal tools
- Team-only applications
- When you want access control

**To grant access:**
```bash
gcloud run services add-iam-policy-binding eui-frontend \
  --region=us-central1 \
  --project=$PROJECT_ID \
  --member="user:someone@example.com" \
  --role="roles/run.invoker"
```

#### Option 2: Make Public (Optional)

**To make frontend public:**

```bash
FRONTEND_AUTH=public ./scripts/deploy/deploy-basic.sh frontend
```

**Best for:**
- Public-facing applications
- Demo/test environments
- Open tools

**Security:**
- Frontend: Public, no restrictions
- API: Protected by API keys (application-level)

## Cost Analysis

### Resource Allocations

**Python API:**
- Memory: 2 GB
- CPU: 2 vCPU
- Max Instances: 10
- Min Instances: 0 (scales to zero)
- Timeout: 60 seconds

**Frontend:**
- Memory: 1 GB
- CPU: 1 vCPU
- Max Instances: 5
- Min Instances: 0 (scales to zero)
- Timeout: 60 seconds

### Cloud Run Pricing Model

**Key Point**: Cloud Run charges only when handling requests. With `min-instances: 0`, services scale to zero when idle.

**Pricing Components:**

1. **CPU Allocation** (only charged when handling requests)
   - $0.00002400 per vCPU-second
   - Python API: 2 vCPU × $0.00002400 = $0.00004800/second when active
   - Frontend: 1 vCPU × $0.00002400 = $0.00002400/second when active

2. **Memory Allocation** (only charged when handling requests)
   - $0.00000250 per GB-second
   - Python API: 2 GB × $0.00000250 = $0.00000500/second when active
   - Frontend: 1 GB × $0.00000250 = $0.00000250/second when active

3. **Request Pricing**
   - $0.40 per million requests
   - First 2 million requests/month are FREE

4. **Free Tier** (per month)
   - 2 million requests
   - 360,000 GB-seconds of memory
   - 180,000 vCPU-seconds of compute

### Estimated Monthly Costs

| Usage Level | Requests/Month | Estimated Cost |
|-------------|----------------|----------------|
| **Idle** | 0 | $0 |
| **Light** | 1,000 | $0 (free tier) |
| **Moderate** | 100,000 | ~$4 |
| **Heavy** | 1,000,000 | ~$40 |
| **Very Heavy** | 10,000,000 | ~$400 |

**Assumptions:**
- Average request duration: 2 seconds
- Scale-to-zero enabled
- Using free tier where applicable

### Cost Safety Features

✅ **Scale to Zero** (Enabled by Default)
- No charges when no requests
- Services start automatically when requests arrive
- Cold start delay: ~5-10 seconds (acceptable for most use cases)

✅ **Request Limits**
- Prevents runaway scaling
- Caps maximum concurrent instances
- Protects against cost spikes

✅ **Timeout Limits**
- Prevents long-running requests from accumulating costs
- Requests timeout after 60 seconds

## Updating Services

To update a service, simply run the deployment script again:

```bash
# Update Python API
./scripts/deploy/deploy-basic.sh python

# Update Frontend
./scripts/deploy/deploy-basic.sh frontend
```

Cloud Run will create a new revision automatically.

## Cleanup

### Quick Commands

**List Services (No Deletion):**
```bash
./scripts/manage/delete-basic.sh list

# Or manually
gcloud run services list --project=$PROJECT_ID --region=us-central1
```

**Delete Services:**
```bash
# Delete both services
./scripts/manage/delete-basic.sh both

# Delete Python API only
./scripts/manage/delete-basic.sh python

# Delete Frontend only
./scripts/manage/delete-basic.sh frontend
```

**Manual Deletion:**
```bash
# Set project and region
export PROJECT_ID="elastic-observability"
export REGION="us-central1"

# Delete Python API
gcloud run services delete eui-python-api \
  --region=$REGION \
  --project=$PROJECT_ID

# Delete Frontend
gcloud run services delete eui-frontend \
  --region=$REGION \
  --project=$PROJECT_ID
```

**Complete Cleanup:**
```bash
# 1. Delete Cloud Run services
./scripts/manage/delete-basic.sh both

# 2. (Optional) Delete container images from Container Registry
gcloud container images list --project=$PROJECT_ID
gcloud container images delete gcr.io/$PROJECT_ID/eui-python-api:latest --quiet
gcloud container images delete gcr.io/$PROJECT_ID/eui-frontend:latest --quiet
```

## Troubleshooting

### Common Issues

#### Container Failed to Start / PORT Timeout

**Error:**
```
The user-provided container failed to start and listen on the port defined provided by the PORT=8000 environment variable within the allocated timeout.
```

**Causes:**
1. Model loading takes too long (sentence-transformers models are large)
2. Container startup timeout too short
3. Insufficient CPU during startup

**Solutions:**

1. **Increase timeout and enable CPU boost** (already done in script):
   ```bash
   --timeout 300 --startup-cpu-boost
   ```

2. **Check logs** for startup errors:
   ```bash
   gcloud run services logs read eui-python-api \
     --region=us-central1 \
     --project=$PROJECT_ID \
     --limit=50
   ```

3. **Verify Procfile is correct**:
   ```
   web: uvicorn embed:app --host 0.0.0.0 --port $PORT
   ```

#### CORS Errors

**Symptom**: Browser shows CORS error when frontend calls API

**Solution**: Set `CORS_ORIGINS` to include your frontend URL:
```bash
export CORS_ORIGINS="https://eui-frontend-xxxxx-uc.a.run.app"
gcloud run services update eui-python-api \
  --region=us-central1 \
  --project=$PROJECT_ID \
  --update-env-vars CORS_ORIGINS=$CORS_ORIGINS
```

#### API Key Authentication Not Working

**Symptom**: API returns 401 even with API key

**Causes:**
1. API keys not set during deployment
2. Wrong API key header name (should be `X-API-Key`)
3. API key not in the `API_KEYS` list

**Solution**: 
```bash
# Check if API keys are configured
gcloud run services describe eui-python-api \
  --region=us-central1 \
  --project=$PROJECT_ID \
  --format="value(spec.template.spec.containers[0].env)" | grep API_KEYS

# Redeploy with correct API keys
export API_KEYS="correct-key-here"
./scripts/deploy/deploy-basic.sh python
```

#### Health Check Failing

**Symptoms:**
- Service deploys but health checks fail
- Service shows as unhealthy

**Solutions:**

1. **Verify health endpoint**:
   ```bash
   curl https://your-service-url.run.app/health
   ```

2. **Check health endpoint code**:
   - Should return 200 OK
   - Should respond quickly (< 5 seconds)

3. **Increase health check timeout**:
   ```bash
   --startup-probe-timeout 300
   ```

### Debugging Commands

**View Service Logs:**
```bash
gcloud run services logs read eui-python-api \
  --region us-central1 \
  --project $PROJECT_ID
```

**Check Service Status:**
```bash
gcloud run services describe eui-python-api \
  --region us-central1 \
  --project $PROJECT_ID
```

**View Environment Variables:**
```bash
gcloud run services describe eui-python-api \
  --region us-central1 \
  --project $PROJECT_ID \
  --format="value(spec.template.spec.containers[0].env)"
```

**View Build Logs:**
```bash
gcloud builds list --project=$PROJECT_ID --limit=5
gcloud builds log BUILD_ID --project=$PROJECT_ID
```

## Security Considerations

⚠️ **Important**: This basic deployment approach stores secrets as environment variables, which is less secure than Secret Manager. For production:

1. **Use Secret Manager** (see Phase 6 full deployment)
2. **Use service accounts** with minimal permissions
3. **Enable authentication** on Cloud Run services
4. **Use HTTPS** with custom domains
5. **Set up monitoring and alerting**

## Next Steps

After basic deployment works:

1. **Set up HTTPS** (Phase 3): Configure Cloud Load Balancer with SSL
2. **Add authentication**: Enable Cloud Run authentication
3. **Use Secret Manager**: Migrate secrets to Secret Manager
4. **Set up monitoring**: Configure Cloud Monitoring
5. **Full Phase 6 setup**: Complete IAM and service account configuration

## Comparison: Basic vs Full Deployment

| Feature | Basic Deployment | Full Deployment (Phase 6) |
|---------|------------------|---------------------------|
| Setup Complexity | Low | High |
| Secrets Management | Environment variables | Secret Manager |
| Service Accounts | Default | Custom with minimal permissions |
| IAM Configuration | None | Full IAM setup |
| Security | Basic | Production-ready |
| CI/CD | Manual | Cloud Build automated |
| Best For | Testing, development | Production |

## Support

For issues or questions:
1. Check logs: `gcloud run services logs read SERVICE_NAME`
2. Review this guide's troubleshooting section
3. See `docs/infrastructure/gcp-setup.md` for advanced setup
4. See `docs/archive/phases/PHASE6_GCP_DEPLOYMENT_IMPLEMENTATION.md` for full deployment

