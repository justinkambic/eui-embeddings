# OpenTelemetry Verification Guide

This guide explains how to verify that OpenTelemetry instrumentation is working and shipping data to the Elastic Observability cluster.

## Quick Verification

### 1. Run the Verification Script

```bash
# Set environment variables (if not already set)
export OTEL_SERVICE_NAME=eui-python-api
export OTEL_EXPORTER_OTLP_ENDPOINT=https://ff29e674b8bb4b06b3e71aaacf84879f.ingest.us-central1.gcp.elastic.cloud:443
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=ApiKey ZjlhVnRwb0JITGJzUkpwVXhNR0w6S1htMDVsWHJPbW1yczFMOEo0QTFxdw=="

# Run verification script
python scripts/verify/verify-otel.py
```

This script will:
- Check environment variables are set correctly
- Test OTLP endpoint connectivity
- Verify OpenTelemetry SDK initialization
- Create a test span to verify export functionality

### 2. Test with API Calls

```bash
# Start the Python API (if not already running)
python embed.py

# In another terminal, run the API test script
export FRONTEND_API_KEY="your-api-key"
export EMBEDDING_SERVICE_URL="http://localhost:8000"
./scripts/test/test-otel-api.sh
```

This will make actual API calls that generate traces.

## Verifying in Elastic Observability

### 1. Access Elastic Observability UI

1. Log into your Elastic Observability cluster
2. Navigate to **APM** > **Services**

### 2. Find Your Service

Look for the service named `eui-python-api` (or whatever `OTEL_SERVICE_NAME` is set to).

### 3. Check for Traces

- **Recent traces**: Should appear within 1-2 minutes of API calls
- **Service map**: Should show connections between services
- **Transactions**: Should show individual API endpoint calls
- **Spans**: Should show detailed operation breakdowns

### 4. Expected Trace Structure

When you click on a trace, you should see:

- **Root span**: FastAPI request handling
  - **Child spans**:
    - `embed_text`, `embed_image`, `embed_svg`, or `search` (depending on endpoint)
    - `generate_text_embeddings`, `generate_image_embeddings`, etc.
    - `elser_inference` (for text searches)
    - `elasticsearch_search` (for search endpoint)

### 5. Check Metrics

Navigate to **Metrics** to see:
- Request rates
- Latency percentiles
- Error rates
- Throughput

## Troubleshooting

### No Traces Appearing

1. **Check OpenTelemetry initialization**:
   ```bash
   python scripts/verify/verify-otel.py
   ```

2. **Check API logs**:
   Look for `[OTEL] OpenTelemetry initialized` message when the API starts

3. **Verify environment variables**:
   ```bash
   echo $OTEL_EXPORTER_OTLP_ENDPOINT
   echo $OTEL_EXPORTER_OTLP_HEADERS
   ```

4. **Check network connectivity**:
   ```bash
   curl -v https://ff29e674b8bb4b06b3e71aaacf84879f.ingest.us-central1.gcp.elastic.cloud:443/v1/traces \
     -H "Authorization: ApiKey ZjlhVnRwb0JITGJzUkpwVXhNR0w6S1htMDVsWHJPbW1yczFMOEo0QTFxdw=="
   ```

### Traces Appearing but Missing Data

1. **Check span attributes**: Click on individual spans to see attributes
2. **Verify instrumentation**: Ensure endpoints are being called
3. **Check span context**: Verify trace IDs are being propagated

### High Latency in Traces

- This is expected - OpenTelemetry adds minimal overhead
- Check if spans are being created correctly
- Verify batch export is working (spans are batched before export)

## Manual Testing

### Create a Test Span

You can manually create a test span in Python:

```python
from otel_config import tracer

with tracer.start_as_current_span("manual_test") as span:
    span.set_attribute("test.type", "manual")
    span.set_attribute("test.value", 42)
    # Your code here
```

### Check Span Export

To verify spans are being exported, you can temporarily add console export:

```python
# In otel_config.py, add ConsoleSpanExporter for debugging
from opentelemetry.sdk.trace.export import ConsoleSpanExporter

console_exporter = ConsoleSpanExporter()
console_processor = BatchSpanProcessor(console_exporter)
tracer_provider.add_span_processor(console_processor)
```

This will print spans to stdout/stderr for debugging.

## Expected Behavior

### On API Startup

You should see:
```
[OTEL] OpenTelemetry initialized: service=eui-python-api, endpoint=https://...
```

### During API Calls

- Each request should generate a trace
- Spans should include:
  - HTTP method and path
  - Request duration
  - Status code
  - Custom attributes (embedding dimensions, search types, etc.)

### In Elastic Observability

- Traces should appear within 1-2 minutes
- Service should show up in APM services list
- Service map should show connections
- Metrics should show request rates and latency

## Next Steps

Once verification is complete:
1. Monitor traces in production
2. Set up alerts based on metrics
3. Use traces for performance debugging
4. Correlate traces with logs (if trace IDs are added to logs)

