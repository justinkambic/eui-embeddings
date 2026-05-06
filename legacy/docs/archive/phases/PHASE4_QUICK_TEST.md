# Phase 4: Quick Test Guide

Quick commands to verify Phase 4 (API Key Authentication) implementation is complete.

## Quick Verification (30 seconds)

```bash
# Run automated verification script
./scripts/verify-phase4.sh
```

Expected output: **✓ Phase 4 verification PASSED!** with 25+ passed checks.

## Quick Local Test (5 minutes)

### 1. Test Python API Authentication

```bash
# Terminal 1: Start API with test key
export ELASTICSEARCH_ENDPOINT=your-endpoint
export ELASTICSEARCH_API_KEY=your-key
export API_KEYS=test-key-123
python embed.py

# Terminal 2: Test without API key (should fail)
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"type":"text","query":"test"}'
# Expected: 401 Unauthorized

# Test with valid API key (should work)
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-key-123" \
  -d '{"type":"text","query":"test"}'
# Expected: 200 OK (or 500 if Elasticsearch not configured, but auth passed)

# Test health endpoint (no auth required)
curl http://localhost:8000/health
# Expected: 200 OK
```

### 2. Test Frontend Includes API Key

```bash
# Terminal 1: Start Python API
export API_KEYS=frontend-key-123
python embed.py

# Terminal 2: Start Frontend
export FRONTEND_API_KEY=frontend-key-123
export EMBEDDING_SERVICE_URL=http://localhost:8000
cd frontend && npm run dev

# Terminal 3: Test search via frontend
curl -X POST http://localhost:3000/api/search \
  -H "Content-Type: application/json" \
  -d '{"type":"text","query":"test"}'
# Expected: 200 OK (frontend includes API key automatically)
```

### 3. Test Admin Authentication

```bash
# Start frontend with admin key
export ADMIN_API_KEY=admin-key-123
cd frontend && npm run dev

# Test without admin key (should fail)
curl -X POST http://localhost:3000/api/batchIndexImages \
  -H "Content-Type: application/json" \
  -d '{"iconNames":["test"]}'
# Expected: 401 Unauthorized

# Test with admin key (should work)
curl -X POST http://localhost:3000/api/batchIndexImages \
  -H "Content-Type: application/json" \
  -H "X-Admin-API-Key: admin-key-123" \
  -d '{"iconNames":["test"]}'
# Expected: 200 OK (or appropriate response)
```

### 4. Test API Key Management Script

```bash
# Test script help
./scripts/manage-api-keys.sh

# Test script syntax
bash -n scripts/manage-api-keys.sh
# Expected: No errors

# Test key generation (dry run - requires GCP setup)
export GOOGLE_CLOUD_PROJECT=your-project-id
./scripts/manage-api-keys.sh generate
# Expected: Generates a secure random key
```

## Quick Python Test Suite (1 minute)

```bash
# Run Phase 4 tests
python test_phase4_api_keys.py

# Or with pytest
pytest test_phase4_api_keys.py -v
```

## What to Check

✅ **All checks should pass:**
- API key authentication works
- Health endpoint excluded from auth
- Frontend includes API keys
- Admin endpoints support optional auth
- API key management script works
- Documentation complete

## Common Test Scenarios

### Scenario 1: No API Keys Configured (Backward Compatible)
```bash
unset API_KEYS
python embed.py
curl -X POST http://localhost:8000/search -d '{"type":"text","query":"test"}'
# Expected: Works (backward compatible)
```

### Scenario 2: Multiple API Keys
```bash
export API_KEYS=key1,key2,key3
python embed.py

# Test with each key
curl -H "X-API-Key: key1" -X POST http://localhost:8000/search -d '{"type":"text","query":"test"}'
curl -H "X-API-Key: key2" -X POST http://localhost:8000/search -d '{"type":"text","query":"test"}'
# Expected: Both work
```

### Scenario 3: Custom Header Name
```bash
export API_KEY_HEADER=X-Custom-Key
export API_KEYS=test-key
python embed.py

curl -H "X-Custom-Key: test-key" -X POST http://localhost:8000/search -d '{"type":"text","query":"test"}'
# Expected: Works with custom header
```

## If Something Fails

1. **401 Unauthorized**: Check API keys are set correctly, verify header name
2. **Admin auth not working**: Check ADMIN_API_KEY is set, verify auth method
3. **Script errors**: Check gcloud is installed and authenticated
4. **Frontend not including keys**: Check FRONTEND_API_KEY environment variable

See `docs/PHASE4_VERIFICATION_CHECKLIST.md` for detailed troubleshooting.

