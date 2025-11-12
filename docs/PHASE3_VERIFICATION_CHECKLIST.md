# Phase 3: HTTPS/SSL Configuration - Verification Checklist

This checklist helps verify that Phase 3 implementation is complete and working correctly.

## Automated Verification

### Run the verification script:
```bash
./scripts/verify-phase3.sh
```

### Run the test suite:
```bash
python test_phase3_https.py
# Or with pytest:
pytest test_phase3_https.py -v
```

## Manual Verification Steps

### 1. Code Implementation Checks

#### Security Headers Middleware
- [ ] Security headers middleware is added to `embed.py`
- [ ] `X-Content-Type-Options: nosniff` header is present
- [ ] `X-Frame-Options: DENY` header is present
- [ ] `X-XSS-Protection: 1; mode=block` header is present
- [ ] `Strict-Transport-Security` (HSTS) header is conditionally added for HTTPS
- [ ] `Content-Security-Policy` header is present
- [ ] HTTPS detection works via `PYTHON_API_BASE_URL`
- [ ] HTTPS detection works via `X-Forwarded-Proto` header (for load balancer)

**Test command:**
```bash
# Start the API locally
python embed.py

# In another terminal, test headers
curl -I http://localhost:8000/health

# Test with X-Forwarded-Proto header
curl -I http://localhost:8000/health -H "X-Forwarded-Proto: https"
```

#### Environment Variables
- [ ] `PYTHON_API_BASE_URL` is read from environment
- [ ] `CORS_ORIGINS` is read from environment
- [ ] CORS origins are parsed correctly (comma-separated)
- [ ] Default CORS allows all origins (for development)

**Test command:**
```bash
# Test with environment variables
export PYTHON_API_BASE_URL=https://api.example.com
export CORS_ORIGINS=https://icons.example.com
python embed.py
```

### 2. Configuration Files

#### Cloud Run YAML Files
- [ ] `cloud-run-python.yaml` exists and is valid YAML
- [ ] `cloud-run-frontend.yaml` exists and is valid YAML
- [ ] Both files include required environment variables
- [ ] Health check configuration is present
- [ ] Resource limits are configured
- [ ] Scaling configuration is present

**Test command:**
```bash
# Validate YAML syntax (if yamllint is installed)
yamllint cloud-run-python.yaml
yamllint cloud-run-frontend.yaml

# Or use Python
python -c "import yaml; yaml.safe_load(open('cloud-run-python.yaml'))"
python -c "import yaml; yaml.safe_load(open('cloud-run-frontend.yaml'))"
```

#### Docker Compose
- [ ] `docker-compose.yml` includes HTTPS configuration comments
- [ ] Comments explain how to configure HTTPS URLs
- [ ] Comments explain internal vs external service communication

**Test command:**
```bash
# Validate docker-compose.yml
docker-compose config
```

### 3. Setup Script

#### HTTPS Setup Script
- [ ] `scripts/setup-https.sh` exists and is executable
- [ ] Script includes static IP reservation
- [ ] Script includes SSL certificate creation
- [ ] Script includes health check creation
- [ ] Script includes NEG creation
- [ ] Script includes backend service creation
- [ ] Script includes URL map creation
- [ ] Script includes forwarding rule creation

**Test command:**
```bash
# Check script syntax
bash -n scripts/setup-https.sh

# Check if executable
test -x scripts/setup-https.sh && echo "Executable" || echo "Not executable"
```

### 4. Local Testing

#### Start Services Locally
```bash
# Start Python API
export ELASTICSEARCH_ENDPOINT=your-endpoint
export ELASTICSEARCH_API_KEY=your-key
export PYTHON_API_BASE_URL=https://api.example.com
export CORS_ORIGINS=https://icons.example.com
python embed.py
```

#### Test Security Headers
```bash
# Test health endpoint
curl -v http://localhost:8000/health

# Verify headers:
# - X-Content-Type-Options: nosniff
# - X-Frame-Options: DENY
# - X-XSS-Protection: 1; mode=block
# - Content-Security-Policy: default-src 'self'
# - Strict-Transport-Security (if HTTPS detected)
```

#### Test CORS
```bash
# Test CORS preflight
curl -X OPTIONS http://localhost:8000/search \
  -H "Origin: https://icons.example.com" \
  -H "Access-Control-Request-Method: POST" \
  -v

# Should include Access-Control-Allow-Origin header
```

#### Test Health Endpoint
```bash
# Health endpoint should not require authentication
curl http://localhost:8000/health

# Should return:
# {
#   "status": "ok",
#   "service": "eui-icon-embeddings",
#   "elasticsearch": "connected" or "not_configured"
# }
```

### 5. Docker Testing

#### Build and Test Docker Images
```bash
# Build Python API image
docker build -f Dockerfile.python -t eui-python-api:test .

# Run container
docker run -p 8000:8000 \
  -e ELASTICSEARCH_ENDPOINT=your-endpoint \
  -e ELASTICSEARCH_API_KEY=your-key \
  -e PYTHON_API_BASE_URL=https://api.example.com \
  -e CORS_ORIGINS=https://icons.example.com \
  eui-python-api:test

# Test in another terminal
curl -v http://localhost:8000/health
```

#### Test Docker Compose
```bash
# Start services
docker-compose up -d

# Check logs
docker-compose logs python-api
docker-compose logs frontend

# Test endpoints
curl http://localhost:8000/health
curl http://localhost:3000

# Stop services
docker-compose down
```

### 6. GCP Deployment Testing (If Deployed)

#### Verify Cloud Run Services
```bash
# List services
gcloud run services list --region us-central1

# Check service configuration
gcloud run services describe eui-python-api --region us-central1
gcloud run services describe eui-frontend --region us-central1

# Check environment variables
gcloud run services describe eui-python-api --region us-central1 \
  --format='value(spec.template.spec.containers[0].env)'
```

#### Test HTTPS Endpoints
```bash
# Test frontend
curl https://icons.example.com

# Test API health check
curl https://api.icons.example.com/health

# Test API search (requires API key)
curl -X POST https://api.icons.example.com/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"type":"text","query":"test"}'
```

#### Verify SSL Certificate
```bash
# Check certificate status
gcloud compute ssl-certificates describe eui-icons-ssl-cert --global

# Test SSL connection
openssl s_client -connect icons.example.com:443 -servername icons.example.com

# Verify certificate chain
curl -vI https://icons.example.com
```

#### Verify Load Balancer
```bash
# Check forwarding rules
gcloud compute forwarding-rules list --global

# Check backend services
gcloud compute backend-services list --global

# Check health checks
gcloud compute health-checks list --global
```

### 7. Integration Testing

#### Test Full Flow
1. [ ] Frontend can make requests to API via HTTPS
2. [ ] CORS headers allow frontend domain
3. [ ] Security headers are present in API responses
4. [ ] Health checks work correctly
5. [ ] API key authentication still works
6. [ ] Internal service communication uses HTTP (faster)

**Test script:**
```bash
# Set up test environment
export FRONTEND_URL=https://icons.example.com
export API_URL=https://api.icons.example.com
export API_KEY=your-api-key

# Test health check
curl "$API_URL/health"

# Test search
curl -X POST "$API_URL/search" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -H "Origin: $FRONTEND_URL" \
  -d '{"type":"text","query":"test"}'

# Verify CORS headers in response
```

### 8. Documentation Verification

- [ ] `docs/HTTPS_SETUP.md` exists and is complete
- [ ] `docs/ENVIRONMENT_VARIABLES.md` includes HTTPS examples
- [ ] `docs/PHASE3_HTTPS_IMPLEMENTATION.md` exists
- [ ] `docs/PHASE3_VERIFICATION_CHECKLIST.md` exists (this file)
- [ ] All documentation is accurate and up-to-date

## Expected Results

### Security Headers (All Responses)
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Content-Security-Policy: default-src 'self'
Strict-Transport-Security: max-age=31536000; includeSubDomains (if HTTPS)
```

### CORS Headers (When Applicable)
```
Access-Control-Allow-Origin: https://icons.example.com
Access-Control-Allow-Methods: POST, GET, OPTIONS, etc.
Access-Control-Allow-Headers: Content-Type, X-API-Key, etc.
```

### Health Check Response
```json
{
  "status": "ok",
  "service": "eui-icon-embeddings",
  "elasticsearch": "connected"
}
```

## Troubleshooting

### Security Headers Not Present
- Check that middleware is added before CORS middleware
- Verify middleware is not being bypassed
- Check that response headers are not being stripped by proxy

### HSTS Header Not Added
- Verify `PYTHON_API_BASE_URL` starts with `https://`
- Check that `X-Forwarded-Proto: https` header is present (from load balancer)
- Ensure request scheme is `https`

### CORS Errors
- Verify `CORS_ORIGINS` includes the frontend domain
- Check that origin header matches exactly (including protocol)
- Ensure CORS middleware is configured correctly

### SSL Certificate Issues
- Wait 30-60 minutes for certificate provisioning
- Verify DNS records point to load balancer IP
- Check certificate status: `gcloud compute ssl-certificates describe ...`

## Sign-off

Once all checks pass:

- [ ] All automated tests pass
- [ ] All manual verification steps completed
- [ ] Documentation is complete
- [ ] Services are deployed and accessible via HTTPS
- [ ] Security headers are present
- [ ] CORS is configured correctly

**Phase 3 Status**: ☐ Complete ☐ In Progress ☐ Blocked

**Verified by**: _________________ **Date**: ___________

