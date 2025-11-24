"""
OpenTelemetry configuration for EUI Embeddings services

This module initializes OpenTelemetry SDK with OTLP export to Elastic Observability.
It configures auto-instrumentation for FastAPI, uvicorn, requests, and elasticsearch.
"""

import os
import sys
import logging
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION, DEPLOYMENT_ENVIRONMENT
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.elasticsearch import ElasticsearchInstrumentor
# Note: Uvicorn instrumentation is not available as a separate package
# FastAPI instrumentation already covers uvicorn ASGI server instrumentation

logger = logging.getLogger(__name__)

# Configuration from environment variables
OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "eui-python-api")
OTEL_SERVICE_VERSION = os.getenv("OTEL_SERVICE_VERSION", "unknown")
OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv(
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "https://ff29e674b8bb4b06b3e71aaacf84879f.ingest.us-central1.gcp.elastic.cloud:443"
)
OTEL_EXPORTER_OTLP_HEADERS = os.getenv(
    "OTEL_EXPORTER_OTLP_HEADERS",
    "Authorization=ApiKey ZjlhVnRwb0JITGJzUkpwVXhNR0w6S1htMDVsWHJPbW1yczFMOEo0QTFxdw=="
)
OTEL_RESOURCE_ATTRIBUTES = os.getenv("OTEL_RESOURCE_ATTRIBUTES", "deployment.environment=production")

# Parse resource attributes
resource_attributes = {
    SERVICE_NAME: OTEL_SERVICE_NAME,
    SERVICE_VERSION: OTEL_SERVICE_VERSION,
}

# Parse additional resource attributes from OTEL_RESOURCE_ATTRIBUTES
# Format: key1=value1,key2=value2
for attr in OTEL_RESOURCE_ATTRIBUTES.split(","):
    if "=" in attr:
        key, value = attr.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key == "deployment.environment":
            resource_attributes[DEPLOYMENT_ENVIRONMENT] = value
        else:
            resource_attributes[key] = value

# Create resource with attributes
resource = Resource.create(resource_attributes)

# Initialize TracerProvider
tracer_provider = TracerProvider(resource=resource)
trace.set_tracer_provider(tracer_provider)

# Initialize MeterProvider
metric_reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(
        endpoint=f"{OTEL_EXPORTER_OTLP_ENDPOINT}/v1/metrics",
        headers=dict([h.split("=", 1) for h in OTEL_EXPORTER_OTLP_HEADERS.split(",") if "=" in h])
    ),
    export_interval_millis=60000,  # Export every 60 seconds
)
meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)

# Configure OTLP span exporter
otlp_exporter = OTLPSpanExporter(
    endpoint=f"{OTEL_EXPORTER_OTLP_ENDPOINT}/v1/traces",
    headers=dict([h.split("=", 1) for h in OTEL_EXPORTER_OTLP_HEADERS.split(",") if "=" in h])
)

# Add span processor
span_processor = BatchSpanProcessor(otlp_exporter)
tracer_provider.add_span_processor(span_processor)

# Get tracer and meter
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

# Initialize auto-instrumentation
# Note: FastAPI instrumentation will be done in embed.py after app creation
# to ensure proper ordering with other middleware

def instrument_fastapi(app):
    """Instrument FastAPI application"""
    FastAPIInstrumentor.instrument_app(app)

def initialize_instrumentation():
    """Initialize auto-instrumentation for libraries"""
    # Instrument requests library (for HTTP calls)
    RequestsInstrumentor().instrument()
    
    # Instrument Elasticsearch client
    ElasticsearchInstrumentor().instrument()
    
    # Note: Uvicorn instrumentation is handled automatically by FastAPI instrumentation
    # FastAPIInstrumentor.instrument_app() in embed.py will instrument both FastAPI and uvicorn
    
    logger.info(f"OpenTelemetry initialized for service: {OTEL_SERVICE_NAME} (version: {OTEL_SERVICE_VERSION})")
    logger.info(f"OTLP endpoint: {OTEL_EXPORTER_OTLP_ENDPOINT}")
    
    # Log initialization success (also print to stderr for visibility)
    print(f"[OTEL] OpenTelemetry initialized: service={OTEL_SERVICE_NAME}, endpoint={OTEL_EXPORTER_OTLP_ENDPOINT}", file=sys.stderr, flush=True)

def shutdown():
    """Shutdown OpenTelemetry exporters"""
    tracer_provider.shutdown()
    meter_provider.shutdown()
    logger.info("OpenTelemetry shutdown complete")

