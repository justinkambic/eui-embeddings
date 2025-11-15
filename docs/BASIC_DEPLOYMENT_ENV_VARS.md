# Environment Variables for Basic Deployment

## Required Variables

These must be set before running `deploy-basic.sh`:

### 1. PROJECT_ID
```bash
export PROJECT_ID="your-project-id"
```
**Required for:** All deployments  
**How to get:** `gcloud config get-value project` or your GCP project ID

### 2. ELASTICSEARCH_ENDPOINT
```bash
export ELASTICSEARCH_ENDPOINT="https://your-cluster.es.amazonaws.com"
```
**Required for:** Python API deployment  
**Already set:** ✅ You have this

### 3. ELASTICSEARCH_API_KEY
```bash
export ELASTICSEARCH_API_KEY="your-api-key"
```
**Required for:** Python API deployment  
**Already set:** ✅ You have this

## Optional but Recommended Variables

### 4. API_KEYS (Recommended)
```bash
export API_KEYS="key1,key2,key3"
```
**Purpose:** Enables API key authentication for Python API  
**Default:** If not set, API key authentication is disabled  
**Recommendation:** Set this for production use

### 5. FRONTEND_API_KEY (Required if API_KEYS is set)
```bash
export FRONTEND_API_KEY="key1"
```
**Purpose:** API key the frontend uses to authenticate with Python API  
**Required if:** `API_KEYS` is set  
**Must be:** One of the keys in `API_KEYS`  
**Recommendation:** Set this if you set `API_KEYS`

### 6. EMBEDDING_SERVICE_URL (Required for frontend deployment)
```bash
export EMBEDDING_SERVICE_URL="https://eui-python-api-xxxxx-uc.a.run.app"
```
**Purpose:** Python API URL for frontend to connect to  
**When needed:** When deploying frontend (or deploying both together)  
**Auto-set:** Script sets this automatically if deploying both services together  
**Manual:** Set manually if deploying frontend separately

## Optional Configuration Variables

### 7. CORS_ORIGINS
```bash
export CORS_ORIGINS="https://your-domain.com,https://www.your-domain.com"
```
**Purpose:** Restricts which domains can call the Python API  
**Default:** `*` (allows all origins)  
**Recommendation:** Set to your frontend domain(s) for production

### 8. PYTHON_API_BASE_URL
```bash
export PYTHON_API_BASE_URL="https://api.your-domain.com"
```
**Purpose:** Base URL for Python API (for CORS, redirects)  
**Default:** Cloud Run auto-generated URL  
**When needed:** If using custom domain or need specific CORS configuration

### 9. NEXT_PUBLIC_FRONTEND_URL
```bash
export NEXT_PUBLIC_FRONTEND_URL="https://your-frontend-domain.com"
```
**Purpose:** Public frontend URL (for CORS, etc.)  
**Default:** Cloud Run auto-generated URL  
**When needed:** If using custom domain

### 10. FRONTEND_AUTH
```bash
export FRONTEND_AUTH="private"  # or "public"
```
**Purpose:** Controls frontend authentication  
**Default:** `private` (requires Google Cloud authentication)  
**Options:** 
- `private` - Requires authentication (default)
- `public` - Publicly accessible

### 11. REGION
```bash
export REGION="us-central1"
```
**Purpose:** Cloud Run deployment region  
**Default:** `us-central1`  
**When to change:** If you need a different region

### 12. Rate Limiting (Optional)
```bash
export RATE_LIMIT_PER_MINUTE="60"
export RATE_LIMIT_PER_HOUR="1000"
export RATE_LIMIT_BURST="10"
```
**Purpose:** Configure rate limiting for Python API  
**Defaults:** 60/min, 1000/hour, 10 burst  
**When to change:** If you need different rate limits

### 13. API_KEY_HEADER
```bash
export API_KEY_HEADER="X-API-Key"
```
**Purpose:** Header name for API key authentication  
**Default:** `X-API-Key`  
**When to change:** Rarely needed

## Quick Setup Checklist

### Minimum Setup (Will Work)
```bash
export PROJECT_ID="your-project-id"
export ELASTICSEARCH_ENDPOINT="https://your-cluster.es.amazonaws.com"
export ELASTICSEARCH_API_KEY="your-api-key"
./scripts/deploy-basic.sh both
```

### Recommended Setup (Better Security)
```bash
export PROJECT_ID="your-project-id"
export ELASTICSEARCH_ENDPOINT="https://your-cluster.es.amazonaws.com"
export ELASTICSEARCH_API_KEY="your-api-key"
export API_KEYS="your-secure-key-here"
export FRONTEND_API_KEY="your-secure-key-here"  # Same as one in API_KEYS
export CORS_ORIGINS="https://your-frontend-url.run.app"
./scripts/deploy-basic.sh both
```

### Production Setup (Full Configuration)
```bash
export PROJECT_ID="your-project-id"
export ELASTICSEARCH_ENDPOINT="https://your-cluster.es.amazonaws.com"
export ELASTICSEARCH_API_KEY="your-api-key"
export API_KEYS="prod-key-1,prod-key-2"
export FRONTEND_API_KEY="prod-key-1"
export CORS_ORIGINS="https://your-domain.com"
export PYTHON_API_BASE_URL="https://api.your-domain.com"
export NEXT_PUBLIC_FRONTEND_URL="https://your-domain.com"
export FRONTEND_AUTH="private"  # or "public" if needed
./scripts/deploy-basic.sh both
```

## What Happens If Variables Are Missing

### PROJECT_ID
- **Missing:** Script will try to get from `gcloud config get-value project`
- **Still missing:** Script will fail with error

### ELASTICSEARCH_ENDPOINT / ELASTICSEARCH_API_KEY
- **Missing:** Python API deployment will fail
- **Error:** "ELASTICSEARCH_ENDPOINT not set" or "ELASTICSEARCH_API_KEY not set"

### EMBEDDING_SERVICE_URL
- **Missing when deploying frontend separately:** Frontend deployment will fail
- **Auto-set:** Script sets this automatically when deploying both services together

### API_KEYS
- **Missing:** API key authentication disabled
- **Result:** Python API accepts requests without API keys (less secure)

### FRONTEND_API_KEY
- **Missing but API_KEYS is set:** Frontend won't be able to call Python API
- **Result:** Frontend requests will fail with 401 Unauthorized

## Verification Before Deployment

Check your variables:

```bash
# Check required variables
echo "PROJECT_ID: ${PROJECT_ID:-NOT SET}"
echo "ELASTICSEARCH_ENDPOINT: ${ELASTICSEARCH_ENDPOINT:-NOT SET}"
echo "ELASTICSEARCH_API_KEY: ${ELASTICSEARCH_API_KEY:+SET (hidden)}"

# Check optional but recommended
echo "API_KEYS: ${API_KEYS:-NOT SET (API auth disabled)}"
echo "FRONTEND_API_KEY: ${FRONTEND_API_KEY:-NOT SET}"

# Check frontend-specific (if deploying frontend)
echo "EMBEDDING_SERVICE_URL: ${EMBEDDING_SERVICE_URL:-NOT SET (will be auto-set if deploying both)}"
```

## Example: Complete Setup

```bash
# 1. Set required variables
export PROJECT_ID="elastic-observability"
export ELASTICSEARCH_ENDPOINT="https://your-cluster.es.amazonaws.com"
export ELASTICSEARCH_API_KEY="your-key"

# 2. Set recommended variables
export API_KEYS="dev-key-123"
export FRONTEND_API_KEY="dev-key-123"  # Must match one in API_KEYS

# 3. Optional: Configure CORS (if you know your frontend URL)
# Will be set automatically if deploying both, but you can set it manually:
# export CORS_ORIGINS="https://eui-frontend-xxxxx-uc.a.run.app"

# 4. Deploy
./scripts/deploy-basic.sh both
```

## Summary

**You already have:**
- ✅ ELASTICSEARCH_ENDPOINT
- ✅ ELASTICSEARCH_API_KEY

**You still need:**
- ⚠️ PROJECT_ID (required)

**Recommended to add:**
- ⚠️ API_KEYS (for security)
- ⚠️ FRONTEND_API_KEY (if setting API_KEYS)

**Everything else is optional** and can use defaults or be set later.

