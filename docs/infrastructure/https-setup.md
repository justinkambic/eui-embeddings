# HTTPS/SSL Configuration Guide

This document describes how to configure HTTPS for the EUI Icon Embeddings services when deploying to GCP.

## Overview

HTTPS termination is handled at the GCP Load Balancer level, not within individual services. This approach:
- Simplifies certificate management (Google-managed certificates)
- Reduces overhead on application containers
- Provides centralized SSL/TLS configuration
- Enables easy certificate rotation

## Architecture

```
Internet (HTTPS)
    ↓
GCP Cloud Load Balancer (HTTPS termination)
    ↓
Cloud Run Services (HTTP internally)
    ↓
Internal GCP Network (HTTP)
```

## Recommended Setup

### Domain Structure

**Option 1: Subdomain Approach (Recommended)**
- Frontend: `https://icons.example.com` (or `https://search.example.com`)
- API: `https://api.icons.example.com` (or `https://api.search.example.com`)

**Option 2: Path-Based Routing**
- Frontend: `https://example.com/`
- API: `https://example.com/api/*`

### DNS Configuration

1. **Create DNS Records** (using Google Cloud DNS or external provider):
   ```
   icons.example.com     A     <Load Balancer IP>
   api.icons.example.com A     <Load Balancer IP>
   ```
   Or use CNAME if your DNS provider supports it:
   ```
   icons.example.com     CNAME <Load Balancer hostname>
   api.icons.example.com CNAME <Load Balancer hostname>
   ```

2. **Wait for DNS Propagation** (can take up to 48 hours)

## GCP Cloud Load Balancer Setup

### Prerequisites
- GCP project with billing enabled
- Cloud Run services deployed
- Domain name registered
- DNS access (Google Cloud DNS or external provider)

### Step 1: Reserve Static IP Address

```bash
# Reserve global static IP address
gcloud compute addresses create eui-icons-ip \
  --global

# Get the IP address (use this for DNS A records)
gcloud compute addresses describe eui-icons-ip --global --format='value(address)'
```

### Step 2: Create Google-Managed SSL Certificate

```bash
# Create SSL certificate
gcloud compute ssl-certificates create eui-icons-ssl-cert \
  --domains=icons.example.com,api.icons.example.com \
  --global

# Verify certificate provisioning (can take 30-60 minutes)
gcloud compute ssl-certificates describe eui-icons-ssl-cert --global
```

**Note**: Certificate provisioning requires DNS records to be in place and may take 30-60 minutes. Status will show `ACTIVE` when ready.

### Step 3: Create Health Checks

```bash
# Health check for Python API
gcloud compute health-checks create http eui-python-api-health-check \
  --port 8000 \
  --request-path /health \
  --global

# Health check for Frontend
gcloud compute health-checks create http eui-frontend-health-check \
  --port 3000 \
  --request-path / \
  --global
```

### Step 4: Create Serverless NEGs (Network Endpoint Groups)

```bash
# Create NEG for Python API Cloud Run service
gcloud compute network-endpoint-groups create eui-python-api-neg \
  --region=us-central1 \
  --network-endpoint-type=serverless \
  --cloud-run-service=eui-python-api

# Create NEG for Frontend Cloud Run service
gcloud compute network-endpoint-groups create eui-frontend-neg \
  --region=us-central1 \
  --network-endpoint-type=serverless \
  --cloud-run-service=eui-frontend
```

### Step 5: Create Backend Services

```bash
# Create backend service for Python API
gcloud compute backend-services create eui-python-api-backend \
  --global \
  --protocol HTTP \
  --health-checks eui-python-api-health-check \
  --port-name http

# Create backend service for Frontend
gcloud compute backend-services create eui-frontend-backend \
  --global \
  --protocol HTTP \
  --health-checks eui-frontend-health-check \
  --port-name http

# Add NEGs to backend services
gcloud compute backend-services add-backend eui-python-api-backend \
  --global \
  --network-endpoint-group eui-python-api-neg \
  --network-endpoint-group-region us-central1

gcloud compute backend-services add-backend eui-frontend-backend \
  --global \
  --network-endpoint-group eui-frontend-neg \
  --network-endpoint-group-region us-central1
```

### Step 6: Create URL Map

**For Subdomain Approach:**
```bash
# Create URL map
gcloud compute url-maps create eui-icons-url-map \
  --default-service eui-frontend-backend \
  --global

# Add host rule for API subdomain
gcloud compute url-maps add-host-rule eui-icons-url-map \
  --hosts api.icons.example.com \
  --default-service eui-python-api-backend \
  --global
```

**For Path-Based Routing:**
```bash
# Create URL map with path matcher
gcloud compute url-maps create eui-icons-url-map \
  --default-service eui-frontend-backend \
  --global

# Add path matcher for API
gcloud compute url-maps add-path-matcher eui-icons-url-map \
  --path-matcher-name api-matcher \
  --default-service eui-python-api-backend \
  --path-rules "/api/*=eui-python-api-backend,/search=eui-python-api-backend" \
  --global
```

### Step 7: Create HTTPS Target Proxy

```bash
gcloud compute target-https-proxies create eui-icons-https-proxy \
  --url-map eui-icons-url-map \
  --ssl-certificates eui-icons-ssl-cert \
  --global
```

### Step 8: Create Forwarding Rule

```bash
# Get the reserved IP address
LB_IP=$(gcloud compute addresses describe eui-icons-ip --global --format='value(address)')

# Create forwarding rule
gcloud compute forwarding-rules create eui-icons-https-forwarding-rule \
  --global \
  --target-https-proxy eui-icons-https-proxy \
  --ports 443 \
  --address $LB_IP
```

## Alternative: Cloud Run Custom Domains

For simpler setups, Cloud Run supports custom domains directly:

```bash
# Map custom domain to Cloud Run service
gcloud run domain-mappings create \
  --service eui-frontend \
  --domain icons.example.com \
  --region us-central1

gcloud run domain-mappings create \
  --service eui-python-api \
  --domain api.icons.example.com \
  --region us-central1
```

**Note**: This approach:
- Automatically provisions SSL certificates
- Simpler setup
- Less flexible routing options
- May have limitations for complex routing needs

## Service Configuration

### Python API

Configure with HTTPS URLs in Cloud Run:

```bash
gcloud run services update eui-python-api \
  --set-env-vars \
    PYTHON_API_BASE_URL=https://api.icons.example.com,\
    CORS_ORIGINS=https://icons.example.com \
  --region us-central1
```

### Frontend

Configure with HTTPS URLs:

```bash
# Option 1: Use public HTTPS URLs for both client and server
gcloud run services update eui-frontend \
  --set-env-vars \
    EMBEDDING_SERVICE_URL=https://api.icons.example.com,\
    NEXT_PUBLIC_EMBEDDING_SERVICE_URL=https://api.icons.example.com,\
    NEXT_PUBLIC_FRONTEND_URL=https://icons.example.com \
  --region us-central1

# Option 2: Use internal URL for server-side (better performance)
INTERNAL_API_URL=$(gcloud run services describe eui-python-api \
  --region=us-central1 \
  --format='value(status.url)')

gcloud run services update eui-frontend \
  --set-env-vars \
    EMBEDDING_SERVICE_URL=${INTERNAL_API_URL},\
    NEXT_PUBLIC_EMBEDDING_SERVICE_URL=https://api.icons.example.com,\
    NEXT_PUBLIC_FRONTEND_URL=https://icons.example.com \
  --region us-central1
```

**Note**: Option 2 is recommended for better performance - server-side requests use internal HTTP, client-side requests use public HTTPS.

## Internal Service Communication

Services communicate over HTTP within GCP's internal network:
- No SSL/TLS overhead
- Faster communication
- GCP network is secure by default
- Use Cloud Run service URLs for internal communication

Example internal URL format:
```
http://eui-python-api-<hash>-uc.a.run.app
```

## Certificate Management

### Google-Managed Certificates

- Automatically renewed (no manual intervention)
- Provisioning time: 30-60 minutes after DNS is configured
- Supports multiple domains per certificate
- Free with GCP

### Monitoring Certificate Status

```bash
# Check certificate provisioning status
gcloud compute ssl-certificates describe eui-icons-ssl-cert --global

# Expected status: ACTIVE (when ready)
# Other statuses: PROVISIONING, FAILED_PROVISIONING
```

### Troubleshooting Certificate Issues

1. **Certificate stuck in PROVISIONING**:
   - Verify DNS records are correct: `dig icons.example.com`
   - Ensure DNS points to load balancer IP
   - Wait up to 60 minutes (normal provisioning time)

2. **Certificate shows FAILED_PROVISIONING**:
   - Verify domain ownership
   - Check DNS configuration matches certificate domains exactly
   - Ensure load balancer forwarding rule is active

3. **Certificate not working after provisioning**:
   - Verify forwarding rule is active: `gcloud compute forwarding-rules list --global`
   - Check target proxy configuration
   - Verify URL map routing rules

## Testing HTTPS Configuration

### Verify SSL Certificate

```bash
# Check certificate details
openssl s_client -connect icons.example.com:443 -servername icons.example.com

# Verify certificate chain
curl -vI https://icons.example.com

# Test with specific domain
curl -vI https://api.icons.example.com/health
```

### Test Service Endpoints

```bash
# Test frontend
curl https://icons.example.com

# Test API health check (no auth required)
curl https://api.icons.example.com/health

# Test API search (requires API key)
curl -X POST https://api.icons.example.com/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"type":"text","query":"test"}'
```

### Verify CORS Configuration

```bash
# Test CORS from frontend domain
curl -H "Origin: https://icons.example.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: X-API-Key" \
  -X OPTIONS \
  https://api.icons.example.com/search \
  -v
```

## Security Headers

The load balancer can add security headers via Cloud Armor or by configuring the backend services. For application-level headers, configure in the Python API:

```python
# Already configured in embed.py via CORS middleware
# Additional security headers can be added via FastAPI middleware
```

## Environment Variables Summary

### Production HTTPS Configuration

```bash
# Python API Cloud Run Service
PYTHON_API_BASE_URL=https://api.icons.example.com
CORS_ORIGINS=https://icons.example.com
API_KEYS_SECRET_NAME=api-keys
ELASTICSEARCH_ENDPOINT=https://your-cluster.es.amazonaws.com
ELASTICSEARCH_API_KEY=<from Secret Manager>

# Frontend Cloud Run Service
EMBEDDING_SERVICE_URL=https://api.icons.example.com  # or internal URL
NEXT_PUBLIC_EMBEDDING_SERVICE_URL=https://api.icons.example.com
NEXT_PUBLIC_FRONTEND_URL=https://icons.example.com
FRONTEND_API_KEY=<from Secret Manager>
```

## Notes

- Services communicate over HTTP internally (GCP network is secure)
- SSL/TLS termination happens at the load balancer
- No SSL configuration needed in application code
- Google-managed certificates are recommended for automatic renewal
- DNS propagation can take up to 48 hours
- Certificate provisioning typically takes 30-60 minutes
- Use internal Cloud Run URLs for server-side requests when possible (better performance)
