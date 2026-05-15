# Add OpenTelemetry Observability to EUI Embeddings

## Overview

Implement comprehensive observability using OpenTelemetry SDKs with collectors, Elastic RUM agent, and OTLP export to Elastic Observability cluster. This will enable monitoring of page hits, transaction duration, spans, and RUM data.

## Architecture

- **Python API**: OpenTelemetry Python SDK with auto-instrumentation + in-process collector
- **Next.js Frontend**: OpenTelemetry Node.js SDK + Elastic RUM Agent + in-process collector
- **Export**: OTLP over HTTPS to Elastic Observability endpoint
- **Resource Attributes**: service.name, service.version, deployment.environment

## Implementation Steps

### Phase 1: Python API Instrumentation

**1.1 Add OpenTelemetry dependencies**

- Update `requirements.txt`:
- `opentelemetry-api>=1.21.0`
- `opentelemetry-sdk>=1.21.0`
- `opentelemetry-instrumentation-fastapi>=0.42b0`
- `opentelemetry-instrumentation-requests>=0.42b0`
- `opentelemetry-instrumentation-elasticsearch>=0.42b0`
- `opentelemetry-exporter-otlp-proto-http>=1.21.0`
- `opentelemetry-instrumentation-uvicorn>=0.42b0`

**1.2 Create OpenTelemetry configuration module**

- Create `otel_config.py`:
- Initialize OpenTelemetry SDK
- Configure resource attributes (service.name="eui-python-api", service.version from env, deployment.environment="production")
- Set up OTLP HTTP exporter with endpoint and API key authentication
- Configure auto-instrumentation for FastAPI, uvicorn, requests, elasticsearch
- Initialize tracer and meter providers

**1.3 Integrate into embed.py**

- Import and initialize OpenTelemetry at startup (before FastAPI app creation)
- Add manual instrumentation for key operations:
- `/embed`, `/embed-image`, `/embed-svg` endpoints (track embedding operations)
- `/search` endpoint (track search latency and result counts)
- Elasticsearch operations (track query performance)
- Model loading operations (track initialization time)

**1.4 Add environment variables**

- `OTEL_SERVICE_NAME=eui-python-api`
- `OTEL_SERVICE_VERSION` (from git or build)
- `OTEL_EXPORTER_OTLP_ENDPOINT=https://ff29e674b8bb4b06b3e71aaacf84879f.ingest.us-central1.gcp.elastic.cloud:443`
- `OTEL_EXPORTER_OTLP_HEADERS=Authorization=ApiKey ZjlhVnRwb0JITGJzUkpwVXhNR0w6S1htMDVsWHJPbW1yczFMOEo0QTFxdw==`
- `OTEL_RESOURCE_ATTRIBUTES=deployment.environment=production`

### Phase 2: Next.js Frontend Instrumentation

**2.1 Add OpenTelemetry Node.js dependencies**

- Update `frontend/package.json`:
- `@opentelemetry/api@^1.7.0`
- `@opentelemetry/sdk-node@^0.45.0`
- `@opentelemetry/instrumentation@^0.45.0`
- `@opentelemetry/instrumentation-http@^0.45.0`
- `@opentelemetry/instrumentation-fetch@^0.45.0`
- `@opentelemetry/exporter-trace-otlp-http@^0.45.0`
- `@opentelemetry/exporter-metrics-otlp-http@^0.45.0`
- `@opentelemetry/resources@^1.17.0`
- `@opentelemetry/semantic-conventions@^1.17.0`

**2.2 Add Elastic RUM Agent**

- Add to `frontend/package.json`:
- `@elastic/apm-rum@^5.17.0`

**2.3 Create OpenTelemetry instrumentation file**

- Create `frontend/instrumentation.ts` (Next.js instrumentation hook):
- Initialize OpenTelemetry SDK for Node.js
- Configure resource attributes (service.name="eui-frontend", service.version, deployment.environment)
- Set up OTLP HTTP exporter with endpoint and API key
- Enable HTTP and fetch instrumentation
- Configure trace and metric exporters

**2.4 Create RUM initialization**

- Create `frontend/lib/rum.ts`:
- Initialize Elastic APM RUM agent
- Configure service name, service version, environment
- Set up error tracking and performance monitoring
- Configure transaction sampling

**2.5 Integrate RUM into app**

- Update `frontend/pages/_app.tsx`:
- Import and initialize RUM agent on client-side only
- Add error boundary for error tracking

**2.6 Add manual instrumentation to API routes**

- Update `frontend/pages/api/search.ts`:
- Add span for search operations
- Track search query parameters and result counts
- Update `frontend/pages/api/saveIcon.ts`:
- Add span for save operations
- Update other API routes as needed

**2.7 Add environment variables**

- Update `frontend/.env.local` and deployment config:
- `NEXT_PUBLIC_OTEL_SERVICE_NAME=eui-frontend`
- `NEXT_PUBLIC_OTEL_SERVICE_VERSION`
- `NEXT_PUBLIC_ELASTIC_APM_SERVER_URL` (if different from OTLP endpoint)
- `NEXT_PUBLIC_DEPLOYMENT_ENVIRONMENT=production`

### Phase 3: Docker Configuration

**3.1 Update Python Dockerfile**

- Add OpenTelemetry environment variables to `Dockerfile.python`
- Ensure OTEL configuration is available at runtime

**3.2 Update Frontend Dockerfile**

- Add OpenTelemetry environment variables to `Dockerfile.frontend`
- Ensure instrumentation.ts is included in build

**3.3 Update deployment script**

- Update `scripts/deploy/deploy-basic.sh`:
- Add OTEL environment variables to Cloud Run deployment
- Set service version from git or build metadata

### Phase 4: Documentation and Testing ✅ COMPLETE

**4.1 Create observability documentation** ✅

- Created `docs/OBSERVABILITY.md`:
- Explains OpenTelemetry setup for both Python API and Next.js frontend
- Documents resource attributes (service.name, service.version, deployment.environment)
- Explains how to view traces/metrics in Elastic Observability
- Documents RUM data collection and viewing
- Includes troubleshooting guide
- Includes configuration examples for local development and production

**4.2 Update environment variables documentation** ✅

- Updated `docs/ENVIRONMENT_VARIABLES.md`:
- Added OpenTelemetry configuration variables for Python API
- Added OpenTelemetry configuration variables for Next.js frontend (server-side and browser-accessible)
- Added RUM configuration variables
- Documented NEXT_PUBLIC_* prefix requirements

**4.3 Add verification script** ✅

- Created `scripts/verify/verify-observability.sh`:
- Checks Python OpenTelemetry dependencies are installed
- Checks Node.js OpenTelemetry dependencies are installed
- Verifies environment variables are set (with defaults)
- Checks for instrumentation files (otel_config.py, instrumentation.ts, rum.ts)
- Tests OTLP export connectivity (optional, can be disabled)
- Provides summary with pass/fail/warning counts

## Key Files to Modify

- `requirements.txt` - Add OpenTelemetry Python packages
- `embed.py` - Add OpenTelemetry initialization and instrumentation
- `otel_config.py` - New file for OpenTelemetry configuration
- `frontend/package.json` - Add OpenTelemetry and RUM packages
- `frontend/instrumentation.ts` - New file for Next.js instrumentation
- `frontend/lib/rum.ts` - New file for Elastic RUM agent
- `frontend/pages/_app.tsx` - Integrate RUM agent
- `frontend/pages/api/search.ts` - Add manual instrumentation
- `frontend/pages/api/saveIcon.ts` - Add manual instrumentation
- `Dockerfile.python` - Add OTEL env vars
- `Dockerfile.frontend` - Add OTEL env vars
- `scripts/deploy/deploy-basic.sh` - Add OTEL env vars to deployment
- `docs/OBSERVABILITY.md` - New documentation file
- `docs/ENVIRONMENT_VARIABLES.md` - Update with OTEL vars

## Resource Attributes

- `service.name`: "eui-python-api" or "eui-frontend"
- `service.version`: From git commit or build metadata
- `deployment.environment`: "production"

## OTLP Configuration

- **Endpoint**: `https://ff29e674b8bb4b06b3e71aaacf84879f.ingest.us-central1.gcp.elastic.cloud:443`
- **Protocol**: HTTP (port 443)
- **Authentication**: API Key via Authorization header
- **API Key**: `ZjlhVnRwb0JITGJzUkpwVXhNR0w6S1htMDVsWHJPbW1yczFMOEo0QTFxdw==`

## Expected Observability Data

- **Traces**: Request spans, database queries, external API calls
- **Metrics**: Request counts, latency, error rates, throughput
- **RUM**: Page loads, user interactions, JavaScript errors, performance metrics
- **Logs**: Can be correlated via trace IDs (if logging is enhanced)

### Phase 5: MCP Server Instrumentation

**5.1 Add OpenTelemetry dependencies**
- Update `requirements.txt` (already includes OpenTelemetry packages from Phase 1):
  - Ensure `opentelemetry-instrumentation-requests>=0.42b0` is included (for API calls)
  - MCP server will reuse same OpenTelemetry packages as Python API

**5.2 Import OpenTelemetry configuration**
- Update `mcp_server.py`:
  - Import OpenTelemetry configuration from `otel_config.py` (shared with Python API)
  - Initialize OpenTelemetry at startup (before MCP server creation)
  - Configure resource attributes:
    - `service.name="eui-mcp-server"`
    - `service.version` (from env or git)
    - `deployment.environment="production"`

**5.3 Add manual instrumentation**
- Instrument key operations in `mcp_server.py`:
  - `search_via_api()` function: Track API call latency, success/failure, result counts
  - `call_tool()` async function: Track tool execution time, tool name, arguments
  - `search_by_svg()` tool: Track SVG search operations
  - `search_by_image()` tool: Track image search operations
  - HTTP requests to embedding service: Auto-instrumented via requests instrumentation

**5.4 Add span context propagation**
- Ensure trace context is propagated in HTTP requests to embedding service
- Add trace context to MCP protocol responses (if supported)
- Link MCP tool calls to downstream API calls

**5.5 Add environment variables**
- Update `Dockerfile.mcp` and deployment config:
  - `OTEL_SERVICE_NAME=eui-mcp-server`
  - `OTEL_SERVICE_VERSION` (from git or build)
  - `OTEL_EXPORTER_OTLP_ENDPOINT=https://ff29e674b8bb4b06b3e71aaacf84879f.ingest.us-central1.gcp.elastic.cloud:443`
  - `OTEL_EXPORTER_OTLP_HEADERS=Authorization=ApiKey ZjlhVnRwb0JITGJzUkpwVXhNR0w6S1htMDVsWHJPbW1yczFMOEo0QTFxdw==`
  - `OTEL_RESOURCE_ATTRIBUTES=deployment.environment=production`
  - `EMBEDDING_SERVICE_URL` (existing, used for API calls)

**5.6 Update MCP server documentation**
- Update `docs/MCP_SERVER.md`:
  - Add observability section explaining OpenTelemetry integration
  - Document how to view MCP server traces/metrics in Elastic Observability
  - Explain resource attributes and service naming

## Additional Files to Modify (Phase 5)

- `mcp_server.py` - Add OpenTelemetry initialization and instrumentation
- `Dockerfile.mcp` - Add OTEL environment variables
- `docs/MCP_SERVER.md` - Add observability documentation