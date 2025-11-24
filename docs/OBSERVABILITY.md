# Observability Guide

This guide explains the OpenTelemetry observability setup for the EUI Icon Embeddings project, including how to view traces, metrics, and RUM (Real User Monitoring) data in Elastic Observability.

## Overview

The project uses OpenTelemetry to instrument both the Python API and Next.js frontend, sending telemetry data to a managed Elastic Observability cluster. This provides:

- **Distributed Tracing**: Track requests across services
- **Metrics**: Monitor performance, error rates, and throughput
- **Real User Monitoring (RUM)**: Track browser-side performance and user interactions

## Architecture

### Python API (`embed.py`)

- **Instrumentation**: OpenTelemetry Python SDK with auto-instrumentation
- **Auto-instrumentation**: FastAPI, requests, Elasticsearch
- **Manual instrumentation**: Key operations (embedding generation, search, model loading)
- **Export**: OTLP HTTP to Elastic Observability

### Next.js Frontend

- **Server-side**: OpenTelemetry Node.js SDK via Next.js instrumentation hook
- **Browser-side**: Elastic APM RUM Agent
- **Auto-instrumentation**: HTTP, Fetch
- **Manual instrumentation**: API routes (`/api/search`, `/api/saveIcon`)
- **Export**: OTLP HTTP for server-side, Elastic APM protocol for RUM

## Resource Attributes

All telemetry data includes resource attributes for service identification:

- **`service.name`**: Service identifier
  - Python API: `eui-python-api` (default)
  - Frontend: `eui-frontend` (default)
- **`service.version`**: Version identifier
  - Automatically set from git commit hash during deployment
  - Falls back to `unknown` if git is unavailable
- **`deployment.environment`**: Deployment environment
  - Default: `production`
  - Can be overridden via `OTEL_RESOURCE_ATTRIBUTES` or `NEXT_PUBLIC_DEPLOYMENT_ENVIRONMENT`

## OTLP Configuration

### Endpoint

- **URL**: `https://ff29e674b8bb4b06b3e71aaacf84879f.ingest.us-central1.gcp.elastic.cloud:443`
- **Protocol**: HTTP over TLS (port 443)
- **Paths**:
  - `/v1/traces` - Trace export
  - `/v1/metrics` - Metrics export

### Authentication

- **Method**: API Key via `Authorization` header
- **Format**: `ApiKey <base64-encoded-key>`
- **Environment Variable**: `OTEL_EXPORTER_OTLP_HEADERS=Authorization=ApiKey ...`

## Viewing Data in Elastic Observability

### Accessing the UI

1. Log into your Elastic Observability cluster
2. Navigate to **APM** > **Services**

### Services

You should see two services:

1. **`eui-python-api`**: Python FastAPI service
2. **`eui-frontend`**: Next.js frontend service

### Traces

#### Viewing Traces

1. Navigate to **APM** > **Services** > Select a service
2. Click on **Transactions** tab
3. Click on a transaction to see the trace detail

#### Expected Trace Structure

**Python API Traces** (`/embed`, `/embed-image`, `/embed-svg`, `/search`):

```
Root Span: FastAPI request
├── Child Span: embed_text / embed_image / embed_svg / search
│   ├── generate_text_embeddings / generate_image_embeddings
│   ├── elser_inference (for text searches)
│   └── elasticsearch_search (for search endpoint)
└── HTTP attributes (method, path, status_code, etc.)
```

**Frontend Traces** (`/api/search`, `/api/saveIcon`):

```
Root Span: api/search or api/saveIcon
├── HTTP attributes (method, status_code, etc.)
├── Search attributes (type, result_count, etc.)
└── Child spans from Python API (if distributed tracing is working)
```

#### Trace Attributes

Each span includes attributes:

- **HTTP**: `http.method`, `http.status_code`, `http.url`, `http.route`
- **Search**: `search.type`, `search.results_count`, `search.total_hits`
- **Embedding**: `embedding.dimensions`, `embedding.model`
- **Elasticsearch**: `elasticsearch.operation`, `elasticsearch.index`
- **Performance**: `duration_ms`, `latency_ms`

### Metrics

Navigate to **Metrics** to see:

- **Request Rate**: Requests per second/minute
- **Latency**: P50, P95, P99 percentiles
- **Error Rate**: Percentage of failed requests
- **Throughput**: Bytes transferred per second

### Service Map

The service map shows:

- **Services**: Python API and Frontend
- **Connections**: Frontend → Python API
- **Health**: Service health indicators

### Real User Monitoring (RUM)

#### Viewing RUM Data

1. Navigate to **APM** > **Services** > `eui-frontend`
2. Click on **RUM** tab
3. View:
   - **Page Loads**: Performance metrics for page loads
   - **User Sessions**: Individual user sessions
   - **JavaScript Errors**: Browser-side errors
   - **Performance Metrics**: Core Web Vitals (LCP, FID, CLS)

#### RUM Data Collection

The Elastic APM RUM Agent collects:

- **Page Loads**: Navigation timing, resource timing
- **User Interactions**: Clicks, form submissions
- **JavaScript Errors**: Uncaught exceptions, promise rejections
- **Performance Metrics**: Core Web Vitals
- **API Calls**: Requests made from the browser

## Configuration

### Python API

Environment variables (can be set in Dockerfile or at runtime):

```bash
OTEL_SERVICE_NAME=eui-python-api
OTEL_SERVICE_VERSION=<git-commit-hash>
OTEL_EXPORTER_OTLP_ENDPOINT=https://ff29e674b8bb4b06b3e71aaacf84879f.ingest.us-central1.gcp.elastic.cloud:443
OTEL_EXPORTER_OTLP_HEADERS=Authorization=ApiKey ZjlhVnRwb0JITGJzUkpwVXhNR0w6S1htMDVsWHJPbW1yczFMOEo0QTFxdw==
OTEL_RESOURCE_ATTRIBUTES=deployment.environment=production
```

### Next.js Frontend

**Server-side** (not prefixed with `NEXT_PUBLIC_`):

```bash
OTEL_SERVICE_NAME=eui-frontend
OTEL_SERVICE_VERSION=<git-commit-hash>
OTEL_EXPORTER_OTLP_ENDPOINT=https://ff29e674b8bb4b06b3e71aaacf84879f.ingest.us-central1.gcp.elastic.cloud:443
OTEL_EXPORTER_OTLP_HEADERS=Authorization=ApiKey ZjlhVnRwb0JITGJzUkpwVXhNR0w6S1htMDVsWHJPbW1yczFMOEo0QTFxdw==
```

**Browser-side** (prefixed with `NEXT_PUBLIC_`):

```bash
NEXT_PUBLIC_OTEL_SERVICE_NAME=eui-frontend
NEXT_PUBLIC_OTEL_SERVICE_VERSION=<git-commit-hash>
NEXT_PUBLIC_DEPLOYMENT_ENVIRONMENT=production
NEXT_PUBLIC_ELASTIC_APM_SERVER_URL=https://ff29e674b8bb4b06b3e71aaacf84879f.ingest.us-central1.gcp.elastic.cloud:443
```

## Verification

### Local Development

1. **Python API**:
   ```bash
   # Set environment variables
   export OTEL_SERVICE_NAME=eui-python-api
   export OTEL_EXPORTER_OTLP_ENDPOINT=https://ff29e674b8bb4b06b3e71aaacf84879f.ingest.us-central1.gcp.elastic.cloud:443
   export OTEL_EXPORTER_OTLP_HEADERS="Authorization=ApiKey ZjlhVnRwb0JITGJzUkpwVXhNR0w6S1htMDVsWHJPbW1yczFMOEo0QTFxdw=="
   
   # Run verification script
   python scripts/verify-otel.py
   
   # Start API
   python embed.py
   ```

2. **Frontend**:
   ```bash
   cd frontend
   # Set environment variables (create .env.local)
   echo "NEXT_PUBLIC_OTEL_SERVICE_NAME=eui-frontend" > .env.local
   echo "NEXT_PUBLIC_ELASTIC_APM_SERVER_URL=https://ff29e674b8bb4b06b3e71aaacf84879f.ingest.us-central1.gcp.elastic.cloud:443" >> .env.local
   
   # Start frontend
   npm run dev
   ```

3. **Test API calls**:
   ```bash
   # Make API calls to generate traces
   export FRONTEND_API_KEY="your-api-key"
   export EMBEDDING_SERVICE_URL="http://localhost:8000"
   ./scripts/test-otel-api.sh
   ```

### Production Deployment

The deployment script (`scripts/deploy-basic.sh`) automatically:

1. Detects git commit hash for `OTEL_SERVICE_VERSION`
2. Sets all OpenTelemetry environment variables
3. Configures both server-side and browser-side variables

Verify in Cloud Run:

```bash
# Check environment variables
gcloud run services describe eui-python-api \
  --region us-central1 \
  --format="value(spec.template.spec.containers[0].env)"

# Check logs for OpenTelemetry initialization
gcloud run services logs read eui-python-api \
  --region us-central1 \
  --limit 50
```

Look for: `[OTEL] OpenTelemetry initialized for service: eui-python-api`

## Troubleshooting

### No Traces Appearing

1. **Check OpenTelemetry initialization**:
   - Look for `[OTEL] OpenTelemetry initialized` in logs
   - Run `python scripts/verify-otel.py` for Python API
   - Check browser console for RUM initialization messages

2. **Verify environment variables**:
   ```bash
   # Python API
   echo $OTEL_EXPORTER_OTLP_ENDPOINT
   echo $OTEL_EXPORTER_OTLP_HEADERS
   
   # Frontend (server-side)
   echo $OTEL_EXPORTER_OTLP_ENDPOINT
   
   # Frontend (browser-side - check in browser DevTools)
   console.log(process.env.NEXT_PUBLIC_OTEL_SERVICE_NAME)
   ```

3. **Check network connectivity**:
   ```bash
   curl -v https://ff29e674b8bb4b06b3e71aaacf84879f.ingest.us-central1.gcp.elastic.cloud:443/v1/traces \
     -H "Authorization: ApiKey ZjlhVnRwb0JITGJzUkpwVXhNR0w6S1htMDVsWHJPbW1yczFMOEo0QTFxdw=="
   ```

4. **Check service version**:
   - Ensure `OTEL_SERVICE_VERSION` is set (should be git commit hash)
   - Check that services appear in Elastic Observability UI with correct version

### Traces Appearing but Missing Data

1. **Check span attributes**: Click on individual spans to see attributes
2. **Verify instrumentation**: Ensure endpoints are being called
3. **Check distributed tracing**: Verify trace IDs are being propagated between services

### High Latency in Traces

- OpenTelemetry adds minimal overhead (< 1ms per span)
- High latency is usually from actual application code
- Check if spans are being created correctly
- Verify batch export is working (spans are batched before export)

### RUM Data Not Appearing

1. **Check browser console**:
   - Look for `[RUM] Elastic APM RUM initialized` message
   - Check for any RUM-related errors

2. **Verify environment variables**:
   - Ensure `NEXT_PUBLIC_ELASTIC_APM_SERVER_URL` is set
   - Check that variables are prefixed with `NEXT_PUBLIC_` for browser access

3. **Check RUM agent initialization**:
   - Verify `frontend/lib/rum.ts` is imported in `_app.tsx`
   - Ensure `initRum()` is called in `useEffect` hook

## Best Practices

### Performance

- **Batch Export**: Spans are batched before export (default: 512 spans or 5 seconds)
- **Sampling**: Consider sampling for high-traffic services
- **Resource Attributes**: Keep resource attributes minimal (only essential metadata)

### Security

- **API Keys**: Store API keys securely (use Secret Manager in production)
- **HTTPS**: Always use HTTPS for OTLP export
- **Environment Variables**: Don't commit API keys to version control

### Monitoring

- **Alerts**: Set up alerts based on error rates and latency
- **Dashboards**: Create custom dashboards for key metrics
- **Correlation**: Correlate traces with logs using trace IDs

## Additional Resources

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Elastic APM Documentation](https://www.elastic.co/guide/en/apm/index.html)
- [Elastic Observability Guide](https://www.elastic.co/guide/en/observability/current/index.html)
- [OpenTelemetry Python SDK](https://opentelemetry.io/docs/instrumentation/python/)
- [OpenTelemetry Node.js SDK](https://opentelemetry.io/docs/instrumentation/js/)
- [Elastic APM RUM Agent](https://www.elastic.co/guide/en/apm/agent/rum-js/current/index.html)

