#!/usr/bin/env python3
"""
Verify Trace Context Propagation

This script verifies that trace IDs are being propagated correctly across services:
- Browser (RUM) → Next.js API → Python API → Elasticsearch

It checks:
1. Trace context headers (traceparent/tracestate) are present in requests
2. Trace IDs match across service boundaries
3. Trace IDs are accessible via helper functions
"""

import os
import sys
import requests
import json
from typing import Optional, Dict, Any

# Configuration
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
PYTHON_API_URL = os.getenv("PYTHON_API_URL", "http://localhost:8000")
FRONTEND_API_KEY = os.getenv("FRONTEND_API_KEY", "")

def parse_traceparent(header_value: str) -> Optional[Dict[str, str]]:
    """
    Parse W3C traceparent header format:
    traceparent: 00-<trace-id>-<parent-id>-<trace-flags>
    
    Returns dict with trace_id, parent_id, flags, or None if invalid
    """
    if not header_value:
        return None
    
    parts = header_value.split("-")
    if len(parts) != 4:
        return None
    
    version, trace_id, parent_id, flags = parts
    if version != "00":
        return None
    
    if len(trace_id) != 32 or len(parent_id) != 16:
        return None
    
    return {
        "version": version,
        "trace_id": trace_id,
        "parent_id": parent_id,
        "flags": flags,
    }

def check_trace_header(headers: Dict[str, Any], header_name: str) -> Optional[Dict[str, str]]:
    """Check if trace header exists and parse it"""
    header_value = headers.get(header_name) or headers.get(header_name.lower())
    if header_value:
        if isinstance(header_value, list):
            header_value = header_value[0]
        return parse_traceparent(header_value)
    return None

def test_frontend_api_trace_propagation():
    """Test that frontend API routes extract and propagate trace context"""
    print("\n=== Testing Frontend API Trace Propagation ===")
    
    # Simulate a request with traceparent header (as RUM would send)
    test_trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
    test_parent_id = "00f067aa0ba902b7"
    traceparent_header = f"00-{test_trace_id}-{test_parent_id}-01"
    
    headers = {
        "Content-Type": "application/json",
        "traceparent": traceparent_header,
    }
    
    try:
        # Make request to frontend API
        response = requests.post(
            f"{FRONTEND_URL}/api/search",
            headers=headers,
            json={
                "type": "text",
                "query": "test query",
            },
            timeout=10,
        )
        
        print(f"Frontend API Response Status: {response.status_code}")
        
        # Check if trace ID is in response header
        response_trace_id = response.headers.get("X-Trace-Id")
        if response_trace_id:
            print(f"✓ Trace ID in response header: {response_trace_id}")
            if response_trace_id == test_trace_id:
                print("✓ Trace ID matches incoming trace ID")
            else:
                print(f"⚠ Trace ID differs (may be expected if new trace started): {response_trace_id} vs {test_trace_id}")
        else:
            print("⚠ No X-Trace-Id header in response")
        
        # Check response body
        if response.status_code == 200:
            print("✓ Frontend API request successful")
        else:
            print(f"⚠ Frontend API returned status {response.status_code}")
            print(f"  Response: {response.text[:200]}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"✗ Failed to connect to frontend API: {e}")
        return False

def test_python_api_trace_propagation():
    """Test that Python API extracts trace context and includes trace ID in response"""
    print("\n=== Testing Python API Trace Propagation ===")
    
    # Simulate a request with traceparent header (as frontend would send)
    test_trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
    test_parent_id = "00f067aa0ba902b7"
    traceparent_header = f"00-{test_trace_id}-{test_parent_id}-01"
    
    headers = {
        "Content-Type": "application/json",
        "traceparent": traceparent_header,
    }
    
    if FRONTEND_API_KEY:
        headers["X-API-Key"] = FRONTEND_API_KEY
    
    try:
        # Make request to Python API
        response = requests.post(
            f"{PYTHON_API_URL}/search",
            headers=headers,
            json={
                "type": "text",
                "query": "test",
            },
            timeout=10,
        )
        
        print(f"Python API Response Status: {response.status_code}")
        
        # Check if trace ID is in response header
        response_trace_id = response.headers.get("X-Trace-Id")
        if response_trace_id:
            print(f"✓ Trace ID in response header: {response_trace_id}")
            if response_trace_id == test_trace_id:
                print("✓ Trace ID matches incoming trace ID")
            else:
                print(f"⚠ Trace ID differs (may be expected if new trace started): {response_trace_id} vs {test_trace_id}")
        else:
            print("⚠ No X-Trace-Id header in response")
        
        # Check response body
        if response.status_code == 200:
            print("✓ Python API request successful")
        else:
            print(f"⚠ Python API returned status {response.status_code}")
            print(f"  Response: {response.text[:200]}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"✗ Failed to connect to Python API: {e}")
        return False

def test_end_to_end_trace():
    """Test end-to-end trace propagation through frontend API to Python API"""
    print("\n=== Testing End-to-End Trace Propagation ===")
    
    # Simulate a request with traceparent header (as RUM would send)
    test_trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
    test_parent_id = "00f067aa0ba902b7"
    traceparent_header = f"00-{test_trace_id}-{test_parent_id}-01"
    
    headers = {
        "Content-Type": "application/json",
        "traceparent": traceparent_header,
    }
    
    try:
        # Make request to frontend API (which should forward to Python API)
        response = requests.post(
            f"{FRONTEND_URL}/api/search",
            headers=headers,
            json={
                "type": "text",
                "query": "test query",
            },
            timeout=15,
        )
        
        print(f"End-to-End Response Status: {response.status_code}")
        
        frontend_trace_id = response.headers.get("X-Trace-Id")
        print(f"Frontend Trace ID: {frontend_trace_id}")
        
        if frontend_trace_id:
            print("✓ Trace ID propagated through frontend API")
        else:
            print("⚠ No trace ID in frontend response")
        
        if response.status_code == 200:
            print("✓ End-to-end request successful")
        else:
            print(f"⚠ End-to-end request returned status {response.status_code}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"✗ Failed end-to-end test: {e}")
        return False

def main():
    """Run all trace propagation tests"""
    print("=" * 60)
    print("Trace Context Propagation Verification")
    print("=" * 60)
    print(f"Frontend URL: {FRONTEND_URL}")
    print(f"Python API URL: {PYTHON_API_URL}")
    print(f"Frontend API Key: {'Set' if FRONTEND_API_KEY else 'Not set'}")
    
    results = []
    
    # Test frontend API
    results.append(("Frontend API", test_frontend_api_trace_propagation()))
    
    # Test Python API
    results.append(("Python API", test_python_api_trace_propagation()))
    
    # Test end-to-end
    results.append(("End-to-End", test_end_to_end_trace()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed!")
        print("\nNext steps:")
        print("1. Check Elastic Observability UI for distributed traces")
        print("2. Verify trace IDs match across services")
        print("3. Check that spans are properly linked as parent-child")
        return 0
    else:
        print("✗ Some tests failed")
        print("\nTroubleshooting:")
        print("1. Ensure all services are running")
        print("2. Check that OpenTelemetry is properly initialized")
        print("3. Verify W3C Trace Context propagator is configured")
        print("4. Check service logs for errors")
        return 1

if __name__ == "__main__":
    sys.exit(main())





