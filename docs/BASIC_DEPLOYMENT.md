# Basic Cloud Run Deployment Guide

This guide shows you how to deploy the EUI Icon Embeddings services to Cloud Run using the simplest possible approach - no service accounts, no Secret Manager, just direct container deployment.

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

# Source the file
source .env.local
```

### 2. Deploy Services

```bash
# Make script executable
chmod +x scripts/deploy-basic.sh

# Deploy both services
./scripts/deploy-basic.sh both

# Or deploy individually
./scripts/deploy-basic.sh python
./scripts/deploy-basic.sh frontend
```

### 3. Get Service URLs

After deployment, service URLs are saved to `/tmp/eui-deployment-vars.sh`:

```bash
source /tmp/eui-deployment-vars.sh
echo $PYTHON_API_URL
echo $FRONTEND_URL
```

## Detailed Steps

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
./scripts/deploy-basic.sh python
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
./scripts/deploy-basic.sh frontend

# Or make it publicly accessible
FRONTEND_AUTH=public ./scripts/deploy-basic.sh frontend
```

Or deploy both at once:

```bash
# Both services (frontend private)
./scripts/deploy-basic.sh both

# Or with public frontend
FRONTEND_AUTH=public ./scripts/deploy-basic.sh both
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

### Step 4: Test Deployment

```bash
# Test Python API health endpoint
curl https://YOUR-PYTHON-API-URL/health

# Test Frontend
curl https://YOUR-FRONTEND-URL/
```

## Configuration Options

### Environment Variables

All environment variables are passed directly to Cloud Run containers. See `.env.basic` for all available options.

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

## Updating Services

To update a service, simply run the deployment script again:

```bash
# Update Python API
./scripts/deploy-basic.sh python

# Update Frontend
./scripts/deploy-basic.sh frontend
```

Cloud Run will create a new revision automatically.

## Viewing Logs

```bash
# Python API logs
gcloud run services logs read eui-python-api \
  --region us-central1 \
  --project $PROJECT_ID

# Frontend logs
gcloud run services logs read eui-frontend \
  --region us-central1 \
  --project $PROJECT_ID
```

## Troubleshooting

### "Permission denied" errors

**Solution**: Ensure you have Cloud Run deployment permissions:
```bash
# Check your permissions
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:user:YOUR_EMAIL"
```

You need at least `roles/run.developer` or `roles/run.admin`.

### "API not enabled" errors

**Solution**: The script will try to enable Cloud Run API automatically. If it fails:
```bash
gcloud services enable run.googleapis.com --project=$PROJECT_ID
```

### Build failures

**Solution**: Check build logs:
```bash
gcloud builds list --project=$PROJECT_ID --limit=5
gcloud builds log BUILD_ID --project=$PROJECT_ID
```

### Service not accessible

**Solution**: Check service status:
```bash
gcloud run services describe eui-python-api \
  --region us-central1 \
  --project $PROJECT_ID
```

Verify `--allow-unauthenticated` is set (script does this automatically).

### Environment variables not working

**Solution**: Verify environment variables are set correctly:
```bash
gcloud run services describe eui-python-api \
  --region us-central1 \
  --project $PROJECT_ID \
  --format="value(spec.template.spec.containers[0].env)"
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

## Cost Estimation

Cloud Run pricing (approximate):
- **Free tier**: 2 million requests/month, 360,000 GB-seconds, 180,000 vCPU-seconds
- **Pay-as-you-go**: ~$0.40 per million requests, $0.0000025 per GB-second, $0.0000100 per vCPU-second

With scale-to-zero enabled, you only pay when services are handling requests.

## Support

For issues or questions:
1. Check logs: `gcloud run services logs read SERVICE_NAME`
2. Review this guide's troubleshooting section
3. See `docs/GCP_PROJECT_SETUP.md` for advanced setup
4. See `docs/PHASE6_GCP_DEPLOYMENT_IMPLEMENTATION.md` for full deployment

