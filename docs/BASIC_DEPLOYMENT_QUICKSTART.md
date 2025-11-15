# Basic Deployment Quick Start

## 1. Set Environment Variables

```bash
# Set required variables
export PROJECT_ID="elastic-observability"
export ELASTICSEARCH_ENDPOINT="https://your-cluster.es.amazonaws.com"
export ELASTICSEARCH_API_KEY="your-api-key"

# Optional: API keys (comma-separated)
export API_KEYS="key1,key2,key3"
export FRONTEND_API_KEY="key1"

# Optional: CORS
export CORS_ORIGINS="https://your-domain.com"
```

## 2. Deploy

```bash
# Deploy both services (frontend will be private by default)
./scripts/deploy-basic.sh both

# Or deploy individually
./scripts/deploy-basic.sh python
./scripts/deploy-basic.sh frontend

# To make frontend publicly accessible:
FRONTEND_AUTH=public ./scripts/deploy-basic.sh frontend
```

## 3. Get URLs

```bash
source /tmp/eui-deployment-vars.sh
echo "Python API: $PYTHON_API_URL"
echo "Frontend: $FRONTEND_URL"
```

## 4. Test

```bash
# Test Python API
curl $PYTHON_API_URL/health

# Test Frontend
curl $FRONTEND_URL
```

That's it! See `docs/BASIC_DEPLOYMENT.md` for detailed documentation.

