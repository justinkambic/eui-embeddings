# Authentication and HTTPS in Basic Deployment

## HTTPS - Automatic ✅

**Good news**: HTTPS works automatically!

Cloud Run provides HTTPS for all services via their default domain:
- Python API: `https://eui-python-api-xxxxx-uc.a.run.app`
- Frontend: `https://eui-frontend-xxxxx-uc.a.run.app`

**All traffic is encrypted** - Cloud Run terminates TLS automatically. You don't need to configure SSL certificates.

### Custom Domains (Optional)

If you want a custom domain (e.g., `api.yourdomain.com`):
1. Set up Cloud Load Balancer (see Phase 3)
2. Configure Google-managed SSL certificate
3. Point DNS to the load balancer

For basic deployment, the default `*.run.app` domains work fine with HTTPS.

## Authentication - Two Levels

### 1. Cloud Run Level Authentication

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

### 2. Application-Level API Key Authentication

**Status**: Works if `API_KEYS` environment variable is set ✅

The Python API has built-in API key authentication:

```bash
# When deploying, set API keys
export API_KEYS="key1,key2,key3"
export FRONTEND_API_KEY="key1"
./scripts/deploy-basic.sh both
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

## Security Status Summary

| Feature | Status | Notes |
|---------|--------|-------|
| HTTPS | ✅ Automatic | Cloud Run provides HTTPS via `*.run.app` domains |
| TLS Encryption | ✅ Enabled | All traffic encrypted in transit |
| Cloud Run Auth | ⚠️ Disabled | Services are publicly accessible |
| API Key Auth | ✅ Available | Works if `API_KEYS` env var is set |
| Rate Limiting | ✅ Enabled | Configured in application |
| CORS | ⚠️ Basic | Set via `CORS_ORIGINS` env var (default: `*`) |

## Recommended Security Configuration

### For Development/Testing

```bash
# Basic security - API keys only
export API_KEYS="dev-key-123"
export FRONTEND_API_KEY="dev-key-123"
export CORS_ORIGINS="*"  # Allow all origins
./scripts/deploy-basic.sh both
```

**Security level**: Medium
- ✅ HTTPS enabled
- ✅ API key authentication
- ⚠️ Publicly accessible (anyone with URL + API key)
- ⚠️ CORS allows all origins

### For Production

**Option 1: API Keys + Restricted CORS** (Better)

```bash
export API_KEYS="prod-key-abc123,prod-key-def456"
export FRONTEND_API_KEY="prod-key-abc123"
export CORS_ORIGINS="https://yourdomain.com,https://www.yourdomain.com"
export PYTHON_API_BASE_URL="https://api.yourdomain.com"
./scripts/deploy-basic.sh both
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
./scripts/deploy-basic.sh both

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

## How Frontend Communicates with Python API

### Current Setup (Basic Deployment)

1. **Frontend → Python API**: Direct HTTPS call
   ```
   Frontend (https://eui-frontend-xxx.run.app)
     ↓ HTTPS
   Python API (https://eui-python-api-xxx.run.app)
   ```

2. **Authentication**: Frontend includes `FRONTEND_API_KEY` in `X-API-Key` header

3. **CORS**: Python API checks `CORS_ORIGINS` to allow frontend requests

### Example Request Flow

```javascript
// Frontend makes request
fetch('https://eui-python-api-xxx.run.app/search', {
  headers: {
    'X-API-Key': process.env.FRONTEND_API_KEY,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ type: 'text', query: 'search' })
})
```

## Testing HTTPS and Auth

### Test HTTPS

```bash
# Should show HTTPS connection
curl -v https://eui-python-api-xxxxx-uc.a.run.app/health 2>&1 | grep -i "SSL\|TLS\|https"

# Check certificate
openssl s_client -connect eui-python-api-xxxxx-uc.a.run.app:443 -showcerts
```

### Test API Key Authentication

```bash
# Without API key - should fail with 401
curl https://eui-python-api-xxxxx-uc.a.run.app/search \
  -H "Content-Type: application/json" \
  -d '{"type":"text","query":"test"}'

# With API key - should work
curl https://eui-python-api-xxxxx-uc.a.run.app/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"type":"text","query":"test"}'
```

## Common Issues

### CORS Errors

**Symptom**: Browser shows CORS error when frontend calls API

**Solution**: Set `CORS_ORIGINS` to include your frontend URL:
```bash
export CORS_ORIGINS="https://eui-frontend-xxxxx-uc.a.run.app"
./scripts/deploy-basic.sh python  # Redeploy Python API
```

### 401 Unauthorized

**Symptom**: API returns 401 even with API key

**Causes**:
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
./scripts/deploy-basic.sh python
```

### Mixed Content Warnings

**Symptom**: Browser warns about mixed HTTP/HTTPS content

**Solution**: Ensure all URLs use HTTPS:
- Set `EMBEDDING_SERVICE_URL` to HTTPS URL
- Set `NEXT_PUBLIC_EMBEDDING_SERVICE_URL` to HTTPS URL
- Set `PYTHON_API_BASE_URL` to HTTPS URL

## Upgrading to Full Security (Phase 6)

For production, consider upgrading to full Phase 6 deployment:

1. **Use Secret Manager** instead of environment variables
2. **Custom service accounts** with minimal permissions
3. **Cloud Load Balancer** with custom domain and SSL
4. **Cloud Run authentication** for additional layer
5. **Monitoring and alerting**

See `docs/PHASE6_GCP_DEPLOYMENT_IMPLEMENTATION.md` for details.

## Summary

✅ **HTTPS**: Works automatically - all Cloud Run services have HTTPS  
✅ **API Key Auth**: Works if you set `API_KEYS` environment variable  
⚠️ **Public Access**: Services are publicly accessible (but require API key)  
⚠️ **CORS**: Set `CORS_ORIGINS` to restrict which domains can call your API  

**For basic deployment**: HTTPS + API keys provides good security for most use cases.

