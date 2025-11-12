# Environment Variables Reference

This document describes all environment variables used across the EUI Icon Embeddings system.

## Service-Specific Prefixes

Variables are organized by service with prefixes:
- `PYTHON_API_*` - Python embedding/search service
- `FRONTEND_*` or `NEXT_PUBLIC_*` - Next.js frontend
- `TOKEN_RENDERER_*` - Token renderer service
- `MCP_*` - MCP server (optional)

## Python Embedding/Search Service (`embed.py`)

### Required Variables

- `ELASTICSEARCH_ENDPOINT` - Elasticsearch cluster endpoint URL
  - Example: `https://your-cluster.es.amazonaws.com`
  - Used for: Connecting to Elasticsearch for search and indexing

- `ELASTICSEARCH_API_KEY` - Elasticsearch API key for authentication
  - Example: `VnVhQ2ZHY0JDZGJrU...`
  - Used for: Authenticating with Elasticsearch

### Optional Variables

- `PYTHON_API_HOST` - Host to bind the server to
  - Default: `0.0.0.0` (all interfaces, suitable for Docker)
  - Local development: `127.0.0.1` or `localhost`
  - Used for: Server binding configuration

- `PYTHON_API_PORT` - Port to run the server on
  - Default: `8000`
  - Can be overridden by `PORT` (Cloud Run uses `PORT`)
  - Used for: Server port configuration

- `PYTHON_API_BASE_URL` - Base URL for the API (for CORS, redirects)
  - Example: `https://api.icons.example.com`
  - Used for: CORS configuration, generating absolute URLs

- `ELASTICSEARCH_TIMEOUT` - Elasticsearch request timeout in seconds
  - Default: `30`
  - Used for: Elasticsearch client configuration

- `ELASTICSEARCH_MAX_RETRIES` - Maximum number of retries for Elasticsearch requests
  - Default: `3`
  - Used for: Elasticsearch client configuration

- `CORS_ORIGINS` - Comma-separated list of allowed CORS origins
  - Default: `*` (allows all origins - change in production!)
  - Example: `https://icons.example.com,https://www.example.com`
  - Used for: CORS middleware configuration

- `API_KEY_HEADER` - HTTP header name for API key authentication
  - Default: `X-API-Key`
  - Used for: API key authentication middleware

- `API_KEYS_SECRET_NAME` - Google Secret Manager secret name containing API keys
  - Example: `api-keys`
  - Format: JSON array of strings: `["key1", "key2", ...]`
  - Used for: Reading API keys from Secret Manager (production)

- `API_KEYS` - Comma-separated list of API keys (alternative to Secret Manager)
  - Example: `key1,key2,key3`
  - Used for: Local development or when Secret Manager is not available

- `RATE_LIMIT_PER_MINUTE` - Rate limit per minute per API key
  - Default: `60`
  - Used for: Rate limiting middleware

- `RATE_LIMIT_PER_HOUR` - Rate limit per hour per API key
  - Default: `1000`
  - Used for: Rate limiting middleware

- `RATE_LIMIT_BURST` - Burst allowance for rate limiting
  - Default: `10`
  - Used for: Rate limiting middleware

## Next.js Frontend

### Required Variables

- `EMBEDDING_SERVICE_URL` - Python API URL for server-side requests
  - Example: `http://python-api:8000` (internal Docker network)
  - Example: `https://api.icons.example.com` (production)
  - Default: `http://localhost:8000` (local development)
  - Used for: Server-side API calls (Next.js API routes)

- `NEXT_PUBLIC_EMBEDDING_SERVICE_URL` - Python API URL for client-side requests
  - Example: `https://api.icons.example.com`
  - Default: `http://localhost:8000` (local development)
  - Used for: Client-side API calls (browser)

- `FRONTEND_API_KEY` - API key for frontend to authenticate with Python API
  - Example: `your-api-key-here`
  - Used for: Including API key in requests to Python API

### Optional Variables

- `NEXT_PUBLIC_FRONTEND_URL` - Frontend base URL (for CORS, redirects)
  - Example: `https://icons.example.com`
  - Used for: CORS configuration, generating absolute URLs

- `ELASTICSEARCH_ENDPOINT` - Elasticsearch cluster endpoint URL
  - Example: `https://your-cluster.es.amazonaws.com`
  - Used for: Direct Elasticsearch access (some API routes)

- `ELASTICSEARCH_API_KEY` - Elasticsearch API key
  - Example: `VnVhQ2ZHY0JDZGJrU...`
  - Used for: Direct Elasticsearch access (some API routes)

- `PORT` - Port to run Next.js server on
  - Default: `3000`
  - Used for: Server port configuration

## Token Renderer Service (`token_renderer/server.js`)

### Optional Variables

- `TOKEN_RENDERER_HOST` - Host to bind the server to
  - Default: `0.0.0.0` (all interfaces, suitable for Docker)
  - Used for: Server binding configuration

- `TOKEN_RENDERER_PORT` - Port to run the server on
  - Default: `3002`
  - Used for: Server port configuration

- `TOKEN_RENDERER_BASE_URL` - Base URL for the service (for health checks, etc.)
  - Example: `http://token-renderer:3002` (internal Docker network)
  - Used for: Generating absolute URLs, health checks

**Note**: Token renderer is typically only used during indexing and runs internally in Docker network (not exposed externally).

## MCP Server (`mcp_server.py`)

### Required Variables

- `ELASTICSEARCH_ENDPOINT` - Elasticsearch cluster endpoint URL
  - Example: `https://your-cluster.es.amazonaws.com`
  - Used for: MCP server configuration (if using direct Elasticsearch access)

- `ELASTICSEARCH_API_KEY` - Elasticsearch API key
  - Example: `VnVhQ2ZHY0JDZGJrU...`
  - Used for: MCP server configuration (if using direct Elasticsearch access)

- `EMBEDDING_SERVICE_URL` - Python API base URL
  - Example: `http://localhost:8000` (local)
  - Example: `https://api.icons.example.com` (production)
  - Default: `http://localhost:8000`
  - Used for: Connecting to Python API

### Optional Variables

- `SEARCH_API_URL` - Search API endpoint URL
  - Default: `{EMBEDDING_SERVICE_URL}/search`
  - Used for: Overriding search endpoint URL

## Indexing Scripts (`scripts/index_eui_icons.py`)

### Required Variables

- `ELASTICSEARCH_ENDPOINT` - Elasticsearch cluster endpoint URL
  - Example: `https://your-cluster.es.amazonaws.com`
  - Used for: Indexing icons into Elasticsearch

- `ELASTICSEARCH_API_KEY` - Elasticsearch API key
  - Example: `VnVhQ2ZHY0JDZGJrU...`
  - Used for: Authenticating with Elasticsearch

### Optional Variables

- `EMBEDDING_SERVICE_URL` - Python API base URL
  - Default: `http://localhost:8000`
  - Used for: Generating embeddings during indexing

- `TOKEN_RENDERER_URL` - Token renderer service URL
  - Default: `http://localhost:3002/render-token`
  - Example: `http://token-renderer:3002/render-token` (Docker network)
  - Used for: Rendering token icons during indexing

- `EUI_LOCATION` - Directory path for EUI repository
  - Default: `./data/eui`
  - Used for: Local EUI repository location

- `EUI_REPO` - Git repository URL for EUI
  - Default: `https://github.com/elastic/eui.git`
  - Used for: Cloning EUI repository

## Docker/Cloud Run Variables

### Common Cloud Run Variables

- `PORT` - Port to bind to (Cloud Run sets this automatically)
  - Used by: All services when deployed to Cloud Run
  - Note: Services should use `PORT` if available, fall back to service-specific defaults

### Google Cloud Secret Manager

When using Google Secret Manager (production), secrets are accessed via:
- Secret name: Defined in `API_KEYS_SECRET_NAME` or similar
- Service account: Must have `roles/secretmanager.secretAccessor` permission

## Environment-Specific Examples

### Local Development

```bash
# Python API
ELASTICSEARCH_ENDPOINT=https://your-cluster.es.amazonaws.com
ELASTICSEARCH_API_KEY=your-api-key
PYTHON_API_HOST=0.0.0.0
PYTHON_API_PORT=8000
CORS_ORIGINS=http://localhost:3000

# Frontend
EMBEDDING_SERVICE_URL=http://localhost:8000
NEXT_PUBLIC_EMBEDDING_SERVICE_URL=http://localhost:8000
FRONTEND_API_KEY=dev-api-key
PORT=3000

# Token Renderer
TOKEN_RENDERER_HOST=0.0.0.0
TOKEN_RENDERER_PORT=3002
```

### Docker Compose

```bash
# Python API
ELASTICSEARCH_ENDPOINT=https://your-cluster.es.amazonaws.com
ELASTICSEARCH_API_KEY=your-api-key
PYTHON_API_HOST=0.0.0.0
PYTHON_API_PORT=8000
CORS_ORIGINS=http://localhost:3000

# Frontend
EMBEDDING_SERVICE_URL=http://python-api:8000
NEXT_PUBLIC_EMBEDDING_SERVICE_URL=http://localhost:8000
FRONTEND_API_KEY=dev-api-key
PORT=3000

# Token Renderer (internal)
TOKEN_RENDERER_HOST=0.0.0.0
TOKEN_RENDERER_PORT=3002
TOKEN_RENDERER_URL=http://token-renderer:3002
```

### Production (GCP Cloud Run)

```bash
# Python API
ELASTICSEARCH_ENDPOINT=https://your-cluster.es.amazonaws.com
ELASTICSEARCH_API_KEY=<from Secret Manager>
PYTHON_API_BASE_URL=https://api.icons.example.com
CORS_ORIGINS=https://icons.example.com
API_KEYS_SECRET_NAME=api-keys
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# Frontend
EMBEDDING_SERVICE_URL=https://api.icons.example.com
NEXT_PUBLIC_EMBEDDING_SERVICE_URL=https://api.icons.example.com
FRONTEND_API_KEY=<from Secret Manager>
NEXT_PUBLIC_FRONTEND_URL=https://icons.example.com
```

## Notes

- Variables prefixed with `NEXT_PUBLIC_` are exposed to the browser and should not contain secrets
- Use Secret Manager or environment variable injection for sensitive values in production
- Default values are provided for local development convenience
- All URLs should use HTTPS in production
- Internal Docker network URLs use service names (e.g., `http://python-api:8000`)

