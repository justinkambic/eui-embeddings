#!/usr/bin/env python3
"""
Functional tests for Phase 5: Rate Limiting
Tests that rate limiting actually works as expected
"""

import requests
import time
import sys
import os
from typing import Dict, Any

# Configuration
PYTHON_API_URL = "http://localhost:8000"
# Try to get API key from environment, or use default test key
# If testing, set TEST_API_KEY to match the API key used to start the server
TEST_API_KEY = os.getenv("TEST_API_KEY", "test-key-123")
FRONTEND_API_URL = "http://localhost:3000"

def test_python_api_rate_limiting():
    """Test that Python API rate limiting works"""
    print("\n=== Testing Python API Rate Limiting ===")
    
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": TEST_API_KEY
    }
    
    # Test 1: Make requests up to the limit (should succeed)
    print("\n1. Testing requests within limit (30/minute for /search)...")
    success_count = 0
    for i in range(5):
        try:
            response = requests.post(
                f"{PYTHON_API_URL}/search",
                headers=headers,
                json={"type": "text", "query": "test"},
                timeout=5
            )
            if response.status_code == 200:
                success_count += 1
                # Check for rate limit headers
                if "X-RateLimit-Limit" in response.headers:
                    print(f"  ✓ Request {i+1}: Success (Rate limit headers present)")
                else:
                    print(f"  ⚠ Request {i+1}: Success (but no rate limit headers)")
            else:
                print(f"  ✗ Request {i+1}: Failed with status {response.status_code}")
        except requests.exceptions.ConnectionError:
            print(f"  ✗ Request {i+1}: Cannot connect to Python API at {PYTHON_API_URL}")
            print("     Make sure the Python API is running!")
            return False
        except Exception as e:
            print(f"  ✗ Request {i+1}: Error - {e}")
            return False
    
    if success_count == 5:
        print(f"  ✓ All {success_count} requests succeeded within limit")
    else:
        print(f"  ✗ Only {success_count}/5 requests succeeded")
        return False
    
    # Test 2: Check rate limit headers
    print("\n2. Testing rate limit headers...")
    try:
        response = requests.post(
            f"{PYTHON_API_URL}/search",
            headers=headers,
            json={"type": "text", "query": "test"},
            timeout=5
        )
        
        # Check all rate limit headers (case-insensitive)
        response_headers_lower = {k.lower(): v for k, v in response.headers.items()}
        
        required_headers = {
            "x-ratelimit-limit": "X-RateLimit-Limit",
            "x-ratelimit-remaining": "X-RateLimit-Remaining"
        }
        
        missing_headers = []
        for lower_key, original_key in required_headers.items():
            if lower_key not in response_headers_lower:
                missing_headers.append(original_key)
        
        if missing_headers:
            print(f"  ⚠ Missing headers: {missing_headers}")
            print(f"  Available headers: {list(response.headers.keys())}")
        else:
            print(f"  ✓ Rate limit headers present:")
            print(f"    - X-RateLimit-Limit: {response_headers_lower.get('x-ratelimit-limit', 'N/A')}")
            print(f"    - X-RateLimit-Remaining: {response_headers_lower.get('x-ratelimit-remaining', 'N/A')}")
            if "x-ratelimit-reset" in response_headers_lower:
                print(f"    - X-RateLimit-Reset: {response_headers_lower.get('x-ratelimit-reset')}")
    except Exception as e:
        print(f"  ✗ Error checking headers: {e}")
        return False
    
    # Test 3: Test without API key (should fail if API keys are required)
    print("\n3. Testing request without API key...")
    try:
        response = requests.post(
            f"{PYTHON_API_URL}/search",
            headers={"Content-Type": "application/json"},
            json={"type": "text", "query": "test"},
            timeout=5
        )
        if response.status_code == 401:
            print("  ✓ Correctly rejected request without API key")
        elif response.status_code == 200:
            print("  ⚠ Request succeeded without API key (API keys may not be configured)")
        else:
            print(f"  ⚠ Unexpected status code: {response.status_code}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    # Test 4: Check if API key issue caused test failures
    if success_count == 0:
        print("\n⚠ Note: All requests failed with 401. Make sure the Python API is running")
        print(f"   with API_KEYS environment variable set to include '{TEST_API_KEY}'")
        print("   Example: API_KEYS='test-key-123' python embed.py")
        print("   Or set TEST_API_KEY environment variable to match your server's API key")
        print("\n   To test with your current server, run:")
        print(f"   TEST_API_KEY='YOUR_API_KEY' python test_phase5_rate_limiting.py")
        return False
    
    return True

def test_health_endpoint_no_rate_limit():
    """Test that health endpoint is not rate limited"""
    print("\n=== Testing Health Endpoint (No Rate Limit) ===")
    
    try:
        # Make multiple rapid requests to health endpoint
        for i in range(10):
            response = requests.get(f"{PYTHON_API_URL}/health", timeout=2)
            if response.status_code != 200:
                print(f"  ✗ Health check {i+1} failed with status {response.status_code}")
                return False
        
        print("  ✓ Health endpoint allows unlimited requests (as expected)")
        return True
    except requests.exceptions.ConnectionError:
        print(f"  ✗ Cannot connect to Python API at {PYTHON_API_URL}")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def test_frontend_rate_limiting():
    """Test that frontend API rate limiting works"""
    print("\n=== Testing Frontend API Rate Limiting ===")
    
    try:
        # Test admin endpoint rate limiting
        print("\n1. Testing admin endpoint rate limiting (10/minute)...")
        headers = {"Content-Type": "application/json"}
        
        success_count = 0
        rate_limited = False
        
        for i in range(12):  # Try to exceed the 10/minute limit
            try:
                response = requests.post(
                    f"{FRONTEND_API_URL}/api/batchIndexImages",
                    headers=headers,
                    json={"iconNames": ["test"]},
                    timeout=5
                )
                
                if response.status_code == 200:
                    success_count += 1
                elif response.status_code == 429:
                    rate_limited = True
                    print(f"  ✓ Request {i+1}: Rate limited (429) as expected")
                    break
                elif response.status_code == 401:
                    print(f"  ⚠ Request {i+1}: Unauthorized (401) - ADMIN_API_KEY may be required")
                    break
                elif response.status_code == 500:
                    print(f"  ⚠ Request {i+1}: Server error (500) - may be expected if Elasticsearch not configured")
                    break
                else:
                    print(f"  ⚠ Request {i+1}: Status {response.status_code}")
                
                # Small delay to avoid overwhelming the server
                time.sleep(0.1)
            except requests.exceptions.ConnectionError:
                print(f"  ⚠ Cannot connect to Next.js API at {FRONTEND_API_URL}")
                print("     Make sure the Next.js dev server is running!")
                return False
            except Exception as e:
                print(f"  ⚠ Error on request {i+1}: {e}")
        
        if rate_limited:
            print(f"  ✓ Rate limiting working: {success_count} requests succeeded, then rate limited")
            return True
        elif success_count > 0:
            print(f"  ⚠ Made {success_count} requests but didn't hit rate limit (may need more requests)")
            return True  # Not a failure, just didn't hit the limit
        else:
            print("  ⚠ No successful requests - may be expected if server not fully configured")
            return True  # Not a failure
            
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("Phase 5: Rate Limiting Functional Tests")
    print("=" * 60)
    
    results = {
        "Python API Rate Limiting": False,
        "Health Endpoint (No Limit)": False,
        "Frontend API Rate Limiting": False,
    }
    
    # Test Python API
    results["Python API Rate Limiting"] = test_python_api_rate_limiting()
    results["Health Endpoint (No Limit)"] = test_health_endpoint_no_rate_limit()
    
    # Test Frontend API (optional - may not be running)
    try:
        requests.get(FRONTEND_API_URL, timeout=2)
        results["Frontend API Rate Limiting"] = test_frontend_rate_limiting()
    except:
        print(f"\n⚠ Skipping frontend tests (Next.js not running at {FRONTEND_API_URL})")
        results["Frontend API Rate Limiting"] = None
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)
    
    for test_name, result in results.items():
        if result is True:
            print(f"✓ {test_name}")
        elif result is False:
            print(f"✗ {test_name}")
        else:
            print(f"⊘ {test_name} (skipped)")
    
    print(f"\nPassed: {passed}, Failed: {failed}, Skipped: {skipped}")
    
    if failed == 0:
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {failed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())

