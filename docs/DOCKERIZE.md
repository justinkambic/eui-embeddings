# Dockerize and Productionize Services for GCP Deployment

## Overview

Prepare all services for containerized deployment on GCP with HTTPS, rate limiting, API key authentication, and production-ready configuration. Four main services need containerization: Python embedding/search service, Next.js frontend, token renderer service (optional, internal), and MCP server (local container).

## Current State Analysis

### Hardcoded URLs Found:
- `http://localhost:8000` - Python embedding service (62 occurrences)
- `http://localhost:3001` - Next.js API (legacy, mostly removed)
- `http://localhost:3002` - Token renderer service
- Hardcoded in: `embed.py`, `frontend/pages/api/*.ts`, `mcp_server.py`, `scripts/index_eui_icons.py`, test scripts, documentation

### Environment Variables Currently Used:
- `ELASTICSEARCH_ENDPOINT` - Elasticsearch cluster endpoint
- `ELASTICSEARCH_API_KEY` - Elasticsearch API key
- `EMBEDDING_SERVICE_URL` - Python service URL (defaults to localhost:8000)
- `SEARCH_API_URL` - Search endpoint (defaults to localhost:8000/search)
- `TOKEN_RENDERER_URL` - Token renderer URL (defaults to localhost:3002)
- `TOKEN_RENDERER_PORT` - Token renderer port (default: 3002)
- `EUI_LOCATION` - EUI repo directory path
- `EUI_REPO` - EUI git repository URL

## Implementation Plan

### Phase 1: Environment Variable Standardization

#### 1.1 Create Environment Variable Schema
- Create `docs/ENVIRONMENT_VARIABLES.md` documenting all required/optional variables
- Define service-specific variable prefixes (e.g., `PYTHON_API_*`, `FRONTEND_*`, `TOKEN_RENDERER_*`)
- Document defaults and when they're appropriate

#### 1.2 Update Python Service (`embed.py`)
- Replace all hardcoded URLs with environment variables
- Add variables:
  - `PYTHON_API_HOST` (default: `0.0.0.0` for Docker)
  - `PYTHON_API_PORT` (default: `8000`)
  - `PYTHON_API_BASE_URL` (for CORS/redirects, e.g., `https://api.example.com`)
- Add CORS middleware configuration via env vars
- Make Elasticsearch connection configurable (timeout, retries, etc.)
- Add API key authentication middleware

#### 1.3 Update Next.js Frontend
- Update all API routes to use environment variables:
  - `NEXT_PUBLIC_EMBEDDING_SERVICE_URL` - Public-facing Python API URL
  - `EMBEDDING_SERVICE_URL` - Server-side Python API URL (can differ for internal networking)
  - `NEXT_PUBLIC_FRONTEND_URL` - Frontend base URL for CORS
  - `FRONTEND_API_KEY` - API key for frontend to authenticate with Python API
- Update `frontend/pages/api/*.ts` files:
  - `saveIcon.ts` - Use env var for embedding service
  - `batchIndexImages.ts` - Use env var for embedding service
  - `batchIndexSVG.ts` - Use env var for embedding service
  - `batchIndexText.ts` - Use env var for embedding service
- Update `frontend/client/es.ts` - Ensure Elasticsearch config uses env vars

#### 1.4 Update Token Renderer Service
- Add environment variables:
  - `TOKEN_RENDERER_HOST` (default: `0.0.0.0`)
  - `TOKEN_RENDERER_PORT` (default: `3002`)
  - `TOKEN_RENDERER_BASE_URL` (for health checks, etc.)
- Note: Service will be internal to Docker network, not exposed externally

#### 1.5 Update MCP Server
- Ensure all env vars are properly documented
- Add Docker-specific configuration notes
- Create example docker run command with env vars

#### 1.6 Update Indexing Scripts
- `scripts/index_eui_icons.py` - Ensure all service URLs use env vars
- Test scripts - Update to use env vars with sensible defaults

### Phase 2: Docker Configuration

#### 2.1 Python Service Dockerfile
- Create `Dockerfile.python`:
  - Base: `python:3.13-slim` or `python:3.11-slim` (check compatibility)
  - Install system dependencies (cairo, pango, etc. for cairosvg)
  - Copy requirements.txt and install Python dependencies
  - Copy application code
  - Expose port 8000
  - Health check endpoint (`/health` or `/docs`)
  - Non-root user for security
  - Set working directory
  - CMD: `uvicorn embed:app --host 0.0.0.0 --port ${PORT:-8000}`

#### 2.2 Next.js Frontend Dockerfile
- Create `Dockerfile.frontend`:
  - Multi-stage build:
    - Stage 1: Build Next.js app (`npm run build`)
    - Stage 2: Production runtime (`node:20-alpine`)
  - Copy built files and node_modules
  - Expose port 3000 (or configurable via PORT)
  - Health check endpoint
  - Non-root user
  - CMD: `next start -p ${PORT:-3000}`

#### 2.3 Token Renderer Dockerfile
- Create `Dockerfile.token-renderer`:
  - Base: `node:20-slim`
  - Install Playwright browsers (required for rendering)
  - Copy package files and install dependencies
  - Build webpack bundle (`npm run build`)
  - Expose port 3002 (internal only)
  - Health check endpoint
  - CMD: `node server.js`
  - Note: Will be used internally in Docker network, not exposed externally

#### 2.4 MCP Server Dockerfile
- Create `Dockerfile.mcp`:
  - Base: `python:3.13-slim`
  - Install dependencies from requirements.txt
  - Copy `mcp_server.py`
  - Configure for stdio transport
  - Create entrypoint script that accepts env vars
  - Document usage: `docker run -e ELASTICSEARCH_ENDPOINT=... -e ELASTICSEARCH_API_KEY=... -e EMBEDDING_SERVICE_URL=... image-name`
  - Publish image to container registry (Docker Hub or GCP Artifact Registry)

#### 2.5 Docker Compose Configuration
- Create `docker-compose.yml`:
  - Services: `python-api`, `frontend`, `token-renderer` (optional, commented out by default)
  - Environment variable files (`.env.docker` or `.env.production`)
  - Network configuration:
    - Internal Docker network for service communication
    - Token renderer accessible only via internal network (no external ports)
    - Python API and frontend exposed externally
  - Health checks for all services
  - Restart policies
  - Volume mounts for development (optional)

#### 2.6 .dockerignore Files
- Create `.dockerignore` files to exclude:
  - `venv/`, `node_modules/`, `.git/`
  - Test files, documentation, data directories
  - IDE configs, temporary files

### Phase 3: HTTPS/SSL Configuration

#### 3.1 GCP Load Balancer/Ingress (Recommended Approach)
- Use GCP Cloud Load Balancing for HTTPS termination
- Configure SSL certificates (Google-managed certificates recommended)
- Set up health checks for backend services
- Configure routing rules:
  - Frontend: `https://icons.example.com` → Cloud Run frontend service
  - API: `https://api.icons.example.com` → Cloud Run Python API service
- Backend services communicate over HTTP internally (within GCP network)

#### 3.2 Domain and DNS Recommendation
- **Recommended Setup:**
  - Frontend: `icons.example.com` (or `search.example.com`)
  - API: `api.icons.example.com` (or `api.search.example.com`)
- Use Google Cloud DNS or external DNS provider
- Configure A/CNAME records pointing to Cloud Load Balancer IP
- Use Google-managed SSL certificates (automatic renewal)
- Alternative: Single domain with path-based routing (`example.com/api/*` → API, `example.com/*` → Frontend)

#### 3.3 Service-to-Service Communication
- Services communicate over HTTP within GCP internal network
- No SSL needed for internal communication (GCP network is secure)
- Frontend → Python API: Use internal service URL or Cloud Run service URL

### Phase 4: API Key Authentication

#### 4.1 Python Service Authentication
- Implement API key middleware using FastAPI dependencies
- Store API keys in Google Secret Manager
- Environment variables:
  - `API_KEYS_SECRET_NAME` - Secret Manager secret name containing API keys (JSON array)
  - `API_KEY_HEADER` - Header name for API key (default: `X-API-Key`)
- Middleware checks:
  - Extract API key from request header
  - Validate against stored keys
  - Return 401 Unauthorized if invalid/missing
- Exclude health check endpoints from authentication
- Rate limiting per API key (track by key, not IP)

#### 4.2 Frontend Authentication
- Frontend stores API key in environment variable (`FRONTEND_API_KEY`)
- Frontend includes API key in all requests to Python API
- Frontend API routes (`/api/*`) can remain unauthenticated (or add optional auth)
- Consider adding basic authentication for admin endpoints (`/api/batchIndex*`)

#### 4.3 Token Renderer Authentication (Optional)
- Since it's internal-only, authentication may not be necessary
- If desired, add simple API key check for internal requests

#### 4.4 API Key Management
- Create `scripts/manage-api-keys.sh`:
  - Generate new API keys
  - Add/remove keys from Secret Manager
  - List active keys
- Document key rotation process
- Use strong, randomly generated keys (32+ characters)

### Phase 5: Rate Limiting

#### 5.1 Python Service Rate Limiting
- Add `slowapi` or `fastapi-limiter` middleware
- Configure rate limits via environment variables:
  - `RATE_LIMIT_PER_MINUTE` - Default: 60 requests/minute per API key
  - `RATE_LIMIT_PER_HOUR` - Default: 1000 requests/hour per API key
  - `RATE_LIMIT_BURST` - Burst allowance (default: 10)
- Per-endpoint rate limits:
  - `/search` - Moderate limits (e.g., 30/min, 500/hour)
  - `/embed`, `/embed-image`, `/embed-svg` - Moderate limits (e.g., 60/min, 1000/hour)
- Use in-memory rate limiting (sufficient for low traffic)
- Track by API key (not IP address)
- Add rate limit headers to responses (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`)

#### 5.2 Next.js API Rate Limiting
- Add `@upstash/ratelimit` or in-memory rate limiting
- Configure rate limits for API routes
- Per-route limits:
  - `/api/search` - Forward to Python API (Python handles rate limiting)
  - `/api/batchIndex*` - Stricter limits (e.g., 10/min) - admin operations
- Track by IP address (for unauthenticated routes)

#### 5.3 Token Renderer Rate Limiting
- Add Express rate limiting middleware
- Stricter limits (rendering is resource-intensive)
- Default: 10 requests/minute per IP (internal network IPs)

#### 5.4 DDoS Protection
- Configure Cloud Armor for additional protection:
  - Rate limiting rules at load balancer level
  - IP-based blocking for known bad actors
  - Geographic restrictions (if applicable)
- Set up WAF rules for common attack patterns
- Monitor and alert on unusual traffic patterns

### Phase 6: GCP Deployment Configuration

#### 6.1 Cloud Run Deployment
- Create `cloud-run-python.yaml`:
  - Service configuration for Python API
  - Environment variables (from Secret Manager where appropriate)
  - Resource limits:
    - CPU: 1-2 vCPU
    - Memory: 1-2 GB (embedding models need memory)
    - Timeout: 60s (max for Cloud Run)
  - Concurrency: 10-20 requests per instance
  - Min instances: 0 (scale to zero)
  - Max instances: 5-10 (low traffic)
  - Health check configuration

- Create `cloud-run-frontend.yaml`:
  - Next.js frontend service configuration
  - Resource limits:
    - CPU: 0.5-1 vCPU
    - Memory: 512MB-1GB
  - Min instances: 0
  - Max instances: 3-5
  - Environment variables

- Create `cloud-run-token-renderer.yaml` (optional, for when needed):
  - Token renderer service configuration
  - Higher resource allocation:
    - CPU: 1-2 vCPU
    - Memory: 2-4 GB (Playwright needs memory)
  - Only deploy when indexing is needed
  - Can be triggered manually or via Cloud Run Jobs

#### 6.2 Cloud Build Configuration
- Create `cloudbuild.yaml`:
  - Build Docker images for each service
  - Push to Google Container Registry/Artifact Registry
  - Deploy to Cloud Run
  - Multi-stage builds
  - Tag images with git commit SHA

#### 6.3 Service Account and IAM
- Create service accounts for each service
- Configure IAM roles:
  - Cloud Run services: `roles/run.invoker`
  - Secret Manager access: `roles/secretmanager.secretAccessor`
  - Cloud Storage (if needed for assets): `roles/storage.objectViewer`

#### 6.4 Secret Management
- Use Google Secret Manager for:
  - `ELASTICSEARCH_API_KEY` - Store as secret
  - `API_KEYS` - JSON array of valid API keys
  - Other sensitive credentials
- Update services to read from Secret Manager
- Create `scripts/setup-secrets.sh` for secret creation:
  - Create secrets in Secret Manager
  - Grant service accounts access
  - Document secret naming conventions

#### 6.5 Environment Configuration
- Create environment-specific configs:
  - `.env.development` - Local development
  - `.env.staging` - Staging environment (if needed)
  - `.env.production` - Production (stored in Secret Manager/Cloud Run env vars)
- Use Cloud Run environment variables for non-sensitive config
- Use Secret Manager for sensitive values

### Phase 7: Production Hardening

#### 7.1 Logging and Monitoring
- Add structured logging (JSON format)
- Python: Use `python-json-logger` or `structlog`
- Node.js: Use `pino` or `winston`
- Configure Cloud Logging integration (automatic with Cloud Run)
- Set up Cloud Monitoring alerts:
  - Error rate thresholds (> 5% error rate)
  - Latency thresholds (p95 > 5s)
  - Resource utilization (CPU > 80%, Memory > 90%)
- Add request ID tracking for debugging

#### 7.2 Health Checks
- Add `/health` endpoints to all services:
  - Python: Check Elasticsearch connectivity, return 200 if healthy
  - Frontend: Check Python API connectivity, return 200 if healthy
  - Token renderer: Check Playwright availability, return 200 if healthy
- Liveness and readiness probes for Cloud Run
- Graceful shutdown handling (SIGTERM)

#### 7.3 Error Handling
- Standardize error responses across services
- Add request ID tracking for debugging
- Implement error aggregation and alerting
- Add retry logic for external dependencies (Elasticsearch)
- Don't expose internal error details to clients

#### 7.4 Security Headers
- Add security headers to all HTTP responses:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `X-XSS-Protection: 1; mode=block`
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains` (HSTS)
  - `Content-Security-Policy: default-src 'self'`
- Configure CORS properly:
  - Allow only frontend domain
  - Not `*` (wildcard)

#### 7.5 Input Validation
- Add request size limits:
  - Python: Max request body size (e.g., 10MB for images)
  - Next.js: Max payload size
- Validate all inputs (already using Pydantic, verify coverage)
- Sanitize user inputs
- Reject malformed requests early

#### 7.6 Resource Limits
- Configure Cloud Run resource limits (see Phase 6.1)
- Set appropriate timeouts
- Configure request concurrency limits
- Monitor resource usage and adjust as needed

#### 7.7 Caching Strategy
- Add response caching where appropriate:
  - Embedding results (cache key: content hash, TTL: 24 hours)
  - Search results (short TTL, e.g., 5 minutes, cache key: query + filters)
- Use Cloud CDN for static assets (if applicable)
- Configure cache headers (`Cache-Control`)

#### 7.8 Database Connection Pooling
- Configure Elasticsearch connection pooling
- Set appropriate connection limits (e.g., max 10 connections per instance)
- Add connection retry logic with exponential backoff
- Handle connection failures gracefully

### Phase 8: MCP Server Container Distribution

#### 8.1 Build and Publish MCP Server Image
- Create automated build process for MCP server Docker image
- Tag images with version numbers
- Push to container registry:
  - Option A: Docker Hub (public or private)
  - Option B: GCP Artifact Registry (private)
- Create `latest` tag for convenience

#### 8.2 Documentation for MCP Server Usage
- Create `docs/MCP_SERVER_DOCKER.md`:
  - Docker pull command
  - Example `docker run` command with required env vars
  - Example MCP client configuration (Claude Desktop)
  - Troubleshooting guide

#### 8.3 Update MCP Server Configuration Example
- Update `mcp_server_config_example.json`:
  - Show Docker command usage
  - Document required environment variables
  - Provide example for local Docker usage

### Phase 9: Documentation and Deployment Guides

#### 9.1 Deployment Documentation
- Create `docs/DEPLOYMENT.md`:
  - GCP setup instructions
  - Docker build and run instructions
  - Environment variable reference
  - API key setup and management
  - Troubleshooting guide
  - Rollback procedures

#### 9.2 CI/CD Pipeline
- Create GitHub Actions workflow (or Cloud Build):
  - Build and test on PR
  - Build Docker images on merge to main
  - Deploy to staging (if applicable)
  - Deploy to production (manual approval)
  - Tag releases

#### 9.3 Migration Guide
- Document migration from localhost to production
- Environment variable migration checklist
- Service dependency order for startup
- API key distribution process

#### 9.4 API Documentation
- Update API documentation with authentication requirements
- Document rate limits
- Provide example requests with API keys
- Document error responses

## Files to Create/Modify

### New Files:
1. `Dockerfile.python` - Python service container
2. `Dockerfile.frontend` - Next.js frontend container
3. `Dockerfile.token-renderer` - Token renderer container
4. `Dockerfile.mcp` - MCP server container
5. `docker-compose.yml` - Local development orchestration
6. `.dockerignore` - Docker ignore patterns
7. `cloudbuild.yaml` - GCP Cloud Build configuration
8. `cloud-run-python.yaml` - Cloud Run service config
9. `cloud-run-frontend.yaml` - Cloud Run service config
10. `cloud-run-token-renderer.yaml` - Cloud Run service config (optional)
11. `docs/ENVIRONMENT_VARIABLES.md` - Environment variable reference
12. `docs/DEPLOYMENT.md` - Deployment guide
13. `docs/MCP_SERVER_DOCKER.md` - MCP server Docker usage guide
14. `scripts/setup-secrets.sh` - Secret management script
15. `scripts/manage-api-keys.sh` - API key management script
16. `.env.example` - Example environment file
17. `.github/workflows/deploy.yml` - CI/CD workflow (optional)

### Files to Modify:
1. `embed.py` - Add env vars, rate limiting, health checks, CORS, API key auth
2. `frontend/pages/api/*.ts` - Replace hardcoded URLs with env vars, add API key headers
3. `frontend/next.config.js` - Add production config, env vars
4. `token_renderer/server.js` - Add env vars, rate limiting, health checks
5. `mcp_server.py` - Verify env var usage, add Docker usage notes
6. `scripts/index_eui_icons.py` - Update service URLs to use env vars
7. `requirements.txt` - Add rate limiting, logging, secret manager libraries
8. `frontend/package.json` - Add rate limiting, logging dependencies
9. `token_renderer/package.json` - Add rate limiting dependencies
10. `README.md` - Update with Docker and deployment instructions
11. `mcp_server_config_example.json` - Update with Docker usage examples

## Additional Production Considerations

### Performance:
- Add request/response compression (gzip) - Cloud Run handles this automatically
- Optimize Docker image sizes (multi-stage builds, alpine images)
- Configure connection keep-alive
- Add database query optimization

### Scalability:
- Design for horizontal scaling (stateless services) - Already stateless
- Use Cloud Run auto-scaling (min: 0, max: 5-10 instances)
- Consider Cloud Load Balancer for multiple regions (if needed later)
- Token renderer can scale independently when needed

### Observability:
- Add distributed tracing (OpenTelemetry) - Optional for low traffic
- Implement structured logging with correlation IDs
- Set up error tracking (Sentry or similar) - Optional
- Add metrics endpoints (Prometheus format) - Optional

### Backup and Recovery:
- Document Elasticsearch backup strategy (Elastic Cloud handles this)
- Create disaster recovery plan
- Document rollback procedures (Cloud Run revision rollback)

### Cost Optimization:
- Use Cloud Run (pay per request) - Already planned
- Configure appropriate resource limits - Already planned
- Use Cloud CDN for static assets - Optional
- Scale to zero when not in use - Already planned

## Resolved Decisions:

1. **Token Renderer Deployment**: 
   - Included in docker-compose.yml but commented out by default
   - Accessible only via internal Docker network (no external ports)
   - Started manually when indexing is needed
   - Can also be deployed as Cloud Run job for one-off indexing tasks

2. **MCP Server Deployment**: 
   - Distributed as Docker image (Docker Hub or GCP Artifact Registry)
   - Users run locally with `docker run` command
   - Users provide env vars (Elasticsearch endpoint, API key, embedding service URL)
   - Documented in `docs/MCP_SERVER_DOCKER.md`

3. **Elasticsearch**: 
   - Self-managed in Elastic Cloud
   - Services only need endpoint and API key (via env vars or Secret Manager)

4. **Domain and DNS**: 
   - Recommended: Subdomain approach
   - Frontend: `icons.example.com` (or `search.example.com`)
   - API: `api.icons.example.com` (or `api.search.example.com`)
   - Use Google Cloud DNS or external DNS provider
   - Use Google-managed SSL certificates

5. **Authentication/Authorization**: 
   - API key authentication required for all Python API endpoints
   - API keys stored in Google Secret Manager
   - Frontend includes API key in requests to Python API
   - Rate limiting per API key (not per IP)
   - Admin endpoints (`/api/batchIndex*`) may have additional restrictions

6. **Budget and Resource Limits**: 
   - Low traffic expected, performance can be slow
   - Cloud Run scale-to-zero enabled
   - Moderate resource limits (1-2 vCPU, 1-2GB RAM per service)
   - Rate limiting to prevent abuse
   - Cloud Armor for DDoS protection