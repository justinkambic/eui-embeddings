# CORS Setup for Basic Deployment

## The CORS Challenge

**Problem:** 
- Python API needs `CORS_ORIGINS` to allow frontend requests
- Frontend URL is only known after deployment
- But Python API is deployed first (when deploying both together)

## Solution Options

### Option 1: Deploy Both, Then Update CORS (Recommended)

**Easiest approach** - deploy everything, then update CORS:

```bash
# 1. Deploy both services (Python API won't have CORS set initially)
export PROJECT_ID="your-project"
export ELASTICSEARCH_ENDPOINT="..."
export ELASTICSEARCH_API_KEY="..."
./scripts/deploy-basic.sh both

# 2. Get the frontend URL
source /tmp/eui-deployment-vars.sh
echo "Frontend URL: $FRONTEND_URL"

# 3. Update Python API with correct CORS
gcloud run services update eui-python-api \
  --region=us-central1 \
  --project=$PROJECT_ID \
  --update-env-vars CORS_ORIGINS=$FRONTEND_URL
```

**Pros:**
- Simple - one command to deploy both
- Script handles EMBEDDING_SERVICE_URL automatically
- Update CORS after deployment

**Cons:**
- CORS not set initially (may cause issues if frontend tries to call API immediately)

### Option 2: Deploy Frontend First, Then Python API with CORS

**More precise** - get frontend URL first:

```bash
# 1. Deploy frontend first
export PROJECT_ID="your-project"
export ELASTICSEARCH_ENDPOINT="..."
export ELASTICSEARCH_API_KEY="..."
# Note: EMBEDDING_SERVICE_URL won't be set yet, but that's OK for now
./scripts/deploy-basic.sh frontend

# 2. Get frontend URL
source /tmp/eui-deployment-vars.sh
export FRONTEND_URL=$FRONTEND_URL
echo "Frontend URL: $FRONTEND_URL"

# 3. Deploy Python API with CORS set
export CORS_ORIGINS=$FRONTEND_URL
export EMBEDDING_SERVICE_URL="https://eui-python-api-xxxxx-uc.a.run.app"  # Will be set after deployment
./scripts/deploy-basic.sh python

# 4. Update frontend with Python API URL
gcloud run services update eui-frontend \
  --region=us-central1 \
  --project=$PROJECT_ID \
  --update-env-vars EMBEDDING_SERVICE_URL=$PYTHON_API_URL,NEXT_PUBLIC_EMBEDDING_SERVICE_URL=$PYTHON_API_URL
```

**Pros:**
- CORS set correctly from the start
- More control over deployment order

**Cons:**
- More steps
- Need to update frontend with Python API URL after Python API deploys

### Option 3: Use Wildcard CORS Initially (Quick Test)

**For testing** - allow all origins initially:

```bash
export CORS_ORIGINS="*"
./scripts/deploy-basic.sh both

# Then restrict later if needed
gcloud run services update eui-python-api \
  --region=us-central1 \
  --project=$PROJECT_ID \
  --update-env-vars CORS_ORIGINS=https://eui-frontend-xxxxx-uc.a.run.app
```

**Pros:**
- Works immediately
- No CORS issues during initial testing

**Cons:**
- Less secure (allows all origins)
- Should restrict for production

## Recommended Workflow

### For First-Time Deployment

```bash
# 1. Set required variables
export PROJECT_ID="elastic-observability"
export ELASTICSEARCH_ENDPOINT="https://your-cluster.es.amazonaws.com"
export ELASTICSEARCH_API_KEY="your-key"
export API_KEYS="your-api-key"
export FRONTEND_API_KEY="your-api-key"

# 2. Deploy both services
./scripts/deploy-basic.sh both

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

### For Updates/Re-deployments

If you're updating services and already know the URLs:

```bash
# Set CORS before deploying
export CORS_ORIGINS="https://eui-frontend-xxxxx-uc.a.run.app"
./scripts/deploy-basic.sh python
```

## What Happens Without CORS?

**If CORS_ORIGINS is not set:**
- Default: `*` (allows all origins)
- Frontend can call Python API
- Less secure, but works

**If CORS_ORIGINS is set incorrectly:**
- Browser will block frontend requests
- You'll see CORS errors in browser console
- API calls will fail

## Verifying CORS Setup

After deployment, test CORS:

```bash
# Test from browser console (on frontend page)
fetch('https://your-python-api-url.run.app/health', {
  method: 'GET',
  headers: { 'X-API-Key': 'your-key' }
})
.then(r => r.json())
.then(console.log)
.catch(console.error)
```

If CORS is wrong, you'll see:
```
Access to fetch at '...' from origin '...' has been blocked by CORS policy
```

## Summary

**Best approach for first deployment:**
1. Deploy both services together
2. Get frontend URL from deployment output
3. Update Python API CORS with frontend URL

**Quick command sequence:**
```bash
./scripts/deploy-basic.sh both
source /tmp/eui-deployment-vars.sh
gcloud run services update eui-python-api \
  --region=us-central1 \
  --project=$PROJECT_ID \
  --update-env-vars CORS_ORIGINS=$FRONTEND_URL
```

This ensures CORS is set correctly after you know the frontend URL.

