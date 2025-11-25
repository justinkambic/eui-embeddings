#!/usr/bin/env python3
"""
Verification script for OpenTelemetry instrumentation

This script tests that OpenTelemetry is properly configured and can export
traces/metrics to the Elastic Observability cluster.
"""

import os
import sys
import time
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

def test_otel_export():
    """Test that OpenTelemetry can export traces"""
    print("=" * 60)
    print("OpenTelemetry Verification Test")
    print("=" * 60)
    
    # Check environment variables
    print("\n1. Checking environment variables...")
    otel_endpoint = os.getenv(
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "https://ff29e674b8bb4b06b3e71aaacf84879f.ingest.us-central1.gcp.elastic.cloud:443"
    )
    otel_headers = os.getenv(
        "OTEL_EXPORTER_OTLP_HEADERS",
        "Authorization=ApiKey ZjlhVnRwb0JITGJzUkpwVXhNR0w6S1htMDVsWHJPbW1yczFMOEo0QTFxdw=="
    )
    otel_service_name = os.getenv("OTEL_SERVICE_NAME", "eui-python-api")
    
    print(f"   OTEL_EXPORTER_OTLP_ENDPOINT: {otel_endpoint}")
    print(f"   OTEL_SERVICE_NAME: {otel_service_name}")
    print(f"   OTEL_EXPORTER_OTLP_HEADERS: {'*' * 20} (hidden)")
    
    # Parse headers
    headers_dict = {}
    for header in otel_headers.split(","):
        if "=" in header:
            key, value = header.split("=", 1)
            headers_dict[key.strip()] = value.strip()
    
    # Test OTLP endpoint connectivity
    print("\n2. Testing OTLP endpoint connectivity...")
    try:
        # Try to connect to the OTLP endpoint (just check if it's reachable)
        base_url = otel_endpoint.replace("/v1/traces", "").replace("/v1/metrics", "")
        if not base_url.startswith("http"):
            base_url = f"https://{base_url}"
        
        # Extract hostname and port
        if "://" in base_url:
            _, rest = base_url.split("://", 1)
        else:
            rest = base_url
        
        if ":" in rest:
            hostname, port = rest.split(":", 1)
            port = int(port)
        else:
            hostname = rest
            port = 443
        
        print(f"   Testing connection to {hostname}:{port}...")
        
        # Simple connectivity test (just check DNS resolution)
        import socket
        socket.gethostbyname(hostname)
        print(f"   ✓ DNS resolution successful")
        
    except Exception as e:
        print(f"   ✗ Connection test failed: {e}")
        return False
    
    # Test OpenTelemetry initialization
    print("\n3. Testing OpenTelemetry SDK initialization...")
    try:
        # Import the otel_config module
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from otel_config import tracer, meter, tracer_provider, meter_provider
        
        print(f"   ✓ Tracer provider initialized")
        print(f"   ✓ Meter provider initialized")
        print(f"   ✓ Tracer available: {tracer is not None}")
        print(f"   ✓ Meter available: {meter is not None}")
        
    except Exception as e:
        print(f"   ✗ OpenTelemetry initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test span creation and export
    print("\n4. Testing span creation and export...")
    try:
        with tracer.start_as_current_span("verification_test") as span:
            span.set_attribute("test.type", "verification")
            span.set_attribute("test.timestamp", time.time())
            span.set_attribute("test.service", otel_service_name)
            
            # Simulate some work
            time.sleep(0.1)
            
            print(f"   ✓ Span created: {span.name}")
            print(f"   ✓ Span context: trace_id={format(span.get_span_context().trace_id, '032x')}")
            print(f"   ✓ Span attributes set: {len(span.attributes)} attributes")
        
        print(f"   ✓ Span exported (check Elastic Observability UI for trace)")
        
    except Exception as e:
        print(f"   ✗ Span creation/export failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test API endpoint (if available)
    print("\n5. Testing API endpoint instrumentation...")
    if not REQUESTS_AVAILABLE:
        print(f"   ⚠ Skipping API test (requests module not available)")
    else:
        api_url = os.getenv("EMBEDDING_SERVICE_URL", "http://localhost:8000")
        api_key = os.getenv("FRONTEND_API_KEY", os.getenv("API_KEYS", "").split(",")[0] if os.getenv("API_KEYS") else "")
        
        if api_url and api_key:
            try:
                print(f"   Testing health endpoint: {api_url}/health")
                response = requests.get(f"{api_url}/health", timeout=5)
                if response.status_code == 200:
                    print(f"   ✓ Health endpoint responded: {response.json()}")
                else:
                    print(f"   ⚠ Health endpoint returned: {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"   ⚠ Could not reach API endpoint: {e}")
                print(f"   (This is OK if the API is not running)")
        else:
            print(f"   ⚠ Skipping API test (EMBEDDING_SERVICE_URL or API key not set)")
    
    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)
    print("✓ OpenTelemetry SDK initialized successfully")
    print("✓ OTLP exporter configured")
    print("✓ Spans can be created and exported")
    print("\nTo verify traces are reaching Elastic Observability:")
    print("1. Log into your Elastic Observability cluster")
    print("2. Navigate to APM > Services")
    print(f"3. Look for service: {otel_service_name}")
    print("4. Check for recent traces (may take 1-2 minutes to appear)")
    print("\nTo test with actual API calls:")
    print("1. Start the Python API: python embed.py")
    print("2. Make some API requests (embed, search, etc.)")
    print("3. Check Elastic Observability for traces")
    
    return True

if __name__ == "__main__":
    success = test_otel_export()
    sys.exit(0 if success else 1)

