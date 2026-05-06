"""
OpenTelemetry configuration for EUI Embeddings services

This module initializes OpenTelemetry SDK with OTLP export to Elastic Observability.
It configures auto-instrumentation for FastAPI, uvicorn, requests, and elasticsearch.
"""

import os
import sys
import logging
from typing import Optional
from opentelemetry import trace, metrics, propagate
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

# Try to import W3C Trace Context propagator
# The default propagator in OpenTelemetry Python SDK is already W3C Trace Context,
# but we'll try to set it explicitly if available
try:
    from opentelemetry.propagators.tracecontext import TraceContextTextMapPropagator
    TRACE_CONTEXT_PROPAGATOR_AVAILABLE = True
except ImportError:
    # Fallback: use default propagator (which is W3C Trace Context)
    # The default global propagator is already W3C Trace Context in OpenTelemetry Python SDK
    TRACE_CONTEXT_PROPAGATOR_AVAILABLE = False
    logger.warning("TraceContextTextMapPropagator not available, using default propagator (W3C Trace Context)")

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

# Configure W3C Trace Context propagator for distributed tracing
# This ensures trace context (traceparent/tracestate headers) is properly propagated
# Note: The default propagator in OpenTelemetry Python SDK is already W3C Trace Context,
# but we set it explicitly to ensure it's configured correctly
if TRACE_CONTEXT_PROPAGATOR_AVAILABLE:
    propagate.set_global_textmap(TraceContextTextMapPropagator())
    logger.info("W3C Trace Context propagator configured explicitly")
else:
    # Default propagator is already W3C Trace Context, so we're good
    logger.info("Using default W3C Trace Context propagator")

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

def get_trace_id() -> Optional[str]:
    """
    Get the current trace ID for logging/debugging.
    
    Returns:
        The trace ID as a hex string, or None if no active span exists.
    """
    current_span = trace.get_current_span()
    if current_span:
        span_context = current_span.get_span_context()
        if span_context.is_valid:
            return format(span_context.trace_id, '032x')  # Format as 32-character hex string
    return None

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

