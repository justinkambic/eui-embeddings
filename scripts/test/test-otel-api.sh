#!/bin/bash
# Test script to generate OpenTelemetry traces from API calls

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "OpenTelemetry API Test Script"
echo "=========================================="
echo ""

# Check if API is running
API_URL="${EMBEDDING_SERVICE_URL:-http://localhost:8000}"
API_KEY="${FRONTEND_API_KEY:-${API_KEYS%%,*}}"

if [ -z "$API_KEY" ]; then
    echo -e "${YELLOW}Warning: No API key set. Set FRONTEND_API_KEY or API_KEYS${NC}"
    echo "Attempting requests without API key..."
fi

echo "API URL: $API_URL"
echo ""

# Test health endpoint
echo "1. Testing health endpoint..."
curl -s "$API_URL/health" | jq '.' || echo "Health check failed"
echo ""

# Test embed endpoint (if API key available)
if [ -n "$API_KEY" ]; then
    echo "2. Testing /embed endpoint (generates trace)..."
    curl -s -X POST "$API_URL/embed" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $API_KEY" \
        -d '{"content": "test query for telemetry"}' | jq '.embeddings | length' || echo "Embed failed"
    echo ""
    
    echo "3. Testing /search endpoint (generates trace)..."
    curl -s -X POST "$API_URL/search" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $API_KEY" \
        -d '{"type": "text", "query": "user icon"}' | jq '.results | length' || echo "Search failed"
    echo ""
else
    echo "2-3. Skipping authenticated endpoints (no API key)"
    echo ""
fi

echo "=========================================="
echo "Test complete!"
echo ""
echo "Check Elastic Observability for traces:"
echo "1. Log into Elastic Observability cluster"
echo "2. Navigate to APM > Services"
echo "3. Look for service: eui-python-api"
echo "4. Check for traces from these requests"
echo "   (may take 1-2 minutes to appear)"
echo "=========================================="

