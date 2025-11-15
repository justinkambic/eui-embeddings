# Public Access and Security in Basic Deployment

## Current Status: Private by Default

**The frontend is deployed as private** (requires authentication) by default.

- **Frontend**: Private (requires Google Cloud authentication) - **Default**
- **Python API**: Public (but requires API key for operations)

You can make the frontend public by setting `FRONTEND_AUTH=public` when deploying.

### Frontend (Next.js)
- ✅ **Publicly accessible** - Anyone with the URL can view it
- ✅ **No authentication required** - No login, no API key needed to view
- ✅ **Anyone can use the UI** - Search, browse icons, etc.

### Python API
- ✅ **Publicly accessible** - Anyone with the URL can reach it
- ✅ **API key required** - But only for actual operations (search, embed, etc.)
- ✅ **Health endpoint public** - `/health` doesn't require API key

## What This Means

### ✅ What Works
- Anyone can visit your frontend URL and use the app
- Frontend automatically handles API key authentication (server-side)
- Users don't need to know about API keys
- Good for public-facing applications

### ⚠️ Security Considerations

**Frontend:**
- No access control - anyone can use the UI
- No rate limiting at Cloud Run level (only application-level)
- No user authentication or authorization

**Python API:**
- Publicly reachable, but requires API key for operations
- Health endpoint is public (intentional)
- API keys protect against unauthorized use

## Access Control Options

### Option 1: Keep Private (Default Setup)

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

### Option 1b: Make Public (Optional)

**To make frontend public:**

```bash
FRONTEND_AUTH=public ./scripts/deploy-basic.sh frontend
```

**Best for:**
- Public-facing applications
- Demo/test environments
- Open tools

**Security:**
- Frontend: Public, no restrictions
- API: Protected by API keys (application-level)

### Option 2: Frontend is Already Private (Default)

**Default behavior** - frontend is deployed as private:

```bash
# Deploy (frontend is private by default)
./scripts/deploy-basic.sh frontend
```

**Result:**
- Only authenticated Google Cloud users can access frontend
- Users need to run: `gcloud run services proxy eui-frontend --region=us-central1`
- Or grant IAM permissions to specific users/groups

**Best for:**
- Internal tools
- Team-only applications
- When you want Google Cloud IAM control

### Option 3: Add Application-Level Auth

**Add login/authentication to the frontend:**

- Implement OAuth (Google, GitHub, etc.)
- Add session management
- Protect routes with authentication middleware

**Best for:**
- User-specific features
- Multi-user applications
- When you need user identity

### Option 4: Use Cloud Load Balancer with Auth

**Set up Cloud Load Balancer (Phase 3):**
- Configure Identity-Aware Proxy (IAP)
- Require Google account authentication
- More advanced access control

**Best for:**
- Enterprise deployments
- Complex access requirements
- Integration with Google Workspace

## Comparison

| Setup | Frontend Access | API Access | Best For |
|-------|----------------|------------|----------|
| **Default (Private)** | Google Cloud users only | API key required | Internal tools |
| **Public Frontend** | Anyone | API key required | Public apps, demos |
| **App-Level Auth** | Authenticated users | API key required | Multi-user apps |
| **IAP + Load Balancer** | Google Workspace users | API key required | Enterprise |

## Accessing Private Frontend (Quick Guide)

The frontend is private by default. Here's how to access it:

### Step 1: Deploy Frontend (Private by Default)

```bash
export PROJECT_ID="your-project"
export EMBEDDING_SERVICE_URL="https://your-python-api-url"
./scripts/deploy-basic.sh frontend
```

### Step 2: Grant Access to Users

**Option A: Use gcloud proxy (for testing)**
```bash
gcloud run services proxy eui-frontend \
  --region=us-central1 \
  --project=$PROJECT_ID \
  --port=8080
```
Then visit: `http://localhost:8080`

**Option B: Grant specific users access**
```bash
# Grant user access
gcloud run services add-iam-policy-binding eui-frontend \
  --region=us-central1 \
  --project=$PROJECT_ID \
  --member="user:someone@example.com" \
  --role="roles/run.invoker"
```

**Option C: Grant service account access**
```bash
# Grant service account access
gcloud run services add-iam-policy-binding eui-frontend \
  --region=us-central1 \
  --project=$PROJECT_ID \
  --member="serviceAccount:service-account@project.iam.gserviceaccount.com" \
  --role="roles/run.invoker"
```

## Current Deployment Behavior

### What Users Can Do

**With private frontend (default):**
- ⚠️ Must be authenticated Google Cloud user
- ⚠️ Must have `roles/run.invoker` permission
- ✅ Use gcloud proxy for local access
- ✅ Or be granted IAM access

**With public frontend (`FRONTEND_AUTH=public`):**
- ✅ Anyone can visit frontend URL
- ✅ View the UI
- ✅ Use search functionality
- ✅ Browse icons

**What's protected:**
- ✅ Python API operations require API key (handled automatically by frontend)
- ✅ Rate limiting applies
- ✅ CORS restrictions (if configured)

### Example URLs

After deployment, you'll get URLs like:
- Frontend: `https://eui-frontend-xxxxx-uc.a.run.app`
- Python API: `https://eui-python-api-xxxxx-uc.a.run.app`

**Both are publicly accessible**, but:
- Frontend: No restrictions
- Python API: Requires API key for operations

## Recommendations

### For Development/Testing
- ✅ Keep public (current setup)
- ✅ Use API keys for API protection
- ✅ Monitor usage via Cloud Run logs

### For Production (Public Tool)
- ✅ Keep public frontend
- ✅ Use API keys
- ✅ Set restrictive CORS (`CORS_ORIGINS`)
- ✅ Enable rate limiting
- ✅ Monitor and alert on abuse

### For Production (Internal Tool)
- ⚠️ Make frontend private (`--no-allow-unauthenticated`)
- ✅ Use Cloud Run IAM for access control
- ✅ Grant access to specific users/groups
- ✅ Use API keys for API protection

## Summary

**Default Setup:**
- ✅ Frontend: **Private** - requires Google Cloud authentication
- ✅ Python API: **Publicly accessible** but requires API key for operations
- ✅ Security: Frontend access controlled via IAM, API protected by API keys

**To make frontend public:**
- Set `FRONTEND_AUTH=public` when deploying
- Or use `--allow-unauthenticated` flag manually

**To grant access to private frontend:**
- Grant `roles/run.invoker` to users/groups
- Use `gcloud run services proxy` for local testing
- Or use service account authentication

The basic deployment prioritizes security by default - frontend is private. Make it public only if needed.

