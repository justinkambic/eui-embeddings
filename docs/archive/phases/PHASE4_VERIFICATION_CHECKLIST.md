# Phase 4: API Key Authentication - Verification Checklist

This checklist helps verify that Phase 4 implementation is complete and working correctly.

## Automated Verification

### Run the verification script:
```bash
./scripts/verify-phase4.sh
```

Expected output: **✓ Phase 4 verification PASSED!** with 25+ passed checks.

## Manual Verification Steps

### 1. API Key Management Script Testing

#### Test Key Generation
```bash
# Set project ID
export GOOGLE_CLOUD_PROJECT=your-project-id

# Test key generation (dry run - won't actually add to Secret Manager without proper setup)
./scripts/manage-api-keys.sh generate
```

**Expected**: Generates a secure random key (32+ characters)

#### Test Script Help
```bash
./scripts/manage-api-keys.sh
```

**Expected**: Shows usage instructions and available commands

#### Test Script Syntax
```bash
bash -n scripts/manage-api-keys.sh
```

**Expected**: No syntax errors

### 2. Python API Authentication Testing

#### Test Without API Key (Should Fail if Keys Configured)
```bash
# Start Python API
export ELASTICSEARCH_ENDPOINT=your-endpoint
export ELASTICSEARCH_API_KEY=your-key
export API_KEYS=test-key-123
python embed.py

# In another terminal, test without API key
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"type":"text","query":"test"}'
```

**Expected**: `401 Unauthorized` with message "API key required"

#### Test With Invalid API Key
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: invalid-key" \
  -d '{"type":"text","query":"test"}'
```

**Expected**: `401 Unauthorized` with message "Invalid API key"

#### Test With Valid API Key
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-key-123" \
  -d '{"type":"text","query":"test"}'
```

**Expected**: `200 OK` with search results

#### Test Health Endpoint (No Auth Required)
```bash
curl http://localhost:8000/health
```

**Expected**: `200 OK` with health status (no API key needed)

#### Test Custom API Key Header
```bash
# Set custom header name
export API_KEY_HEADER=X-Custom-API-Key

# Restart API, then test
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -H "X-Custom-API-Key: test-key-123" \
  -d '{"type":"text","query":"test"}'
```

**Expected**: `200 OK` (works with custom header)

### 3. Frontend API Key Inclusion Testing

#### Test Search Endpoint Includes API Key
```bash
# Start frontend with API key
export FRONTEND_API_KEY=test-key-123
cd frontend && npm run dev

# Check logs when making a search request
# Should see X-API-Key header in requests to Python API
```

**Expected**: Frontend includes `X-API-Key` header in all Python API requests

#### Test Frontend Without API Key (Backward Compatible)
```bash
# Start frontend without API key
unset FRONTEND_API_KEY
cd frontend && npm run dev

# Make search request
curl -X POST http://localhost:3000/api/search \
  -H "Content-Type: application/json" \
  -d '{"type":"text","query":"test"}'
```

**Expected**: 
- If Python API has keys configured: Request fails (401)
- If Python API has no keys: Request succeeds (backward compatible)

### 4. Admin Endpoint Authentication Testing

#### Test Admin Endpoint Without Auth (When ADMIN_API_KEY Not Set)
```bash
# Start frontend without ADMIN_API_KEY
unset ADMIN_API_KEY
cd frontend && npm run dev

# Test admin endpoint
curl -X POST http://localhost:3000/api/batchIndexImages \
  -H "Content-Type: application/json" \
  -d '{"iconNames":["test"]}'
```

**Expected**: Request proceeds (admin auth is optional)

#### Test Admin Endpoint With Auth (When ADMIN_API_KEY Set)
```bash
# Start frontend with ADMIN_API_KEY
export ADMIN_API_KEY=admin-key-123
cd frontend && npm run dev

# Test without admin key (should fail)
curl -X POST http://localhost:3000/api/batchIndexImages \
  -H "Content-Type: application/json" \
  -d '{"iconNames":["test"]}'
```

**Expected**: `401 Unauthorized`

#### Test Admin Endpoint With Valid Key (Bearer Token)
```bash
curl -X POST http://localhost:3000/api/batchIndexImages \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin-key-123" \
  -d '{"iconNames":["test"]}'
```

**Expected**: `200 OK` (or appropriate response based on endpoint logic)

#### Test Admin Endpoint With Valid Key (Header)
```bash
curl -X POST http://localhost:3000/api/batchIndexImages \
  -H "Content-Type: application/json" \
  -H "X-Admin-API-Key: admin-key-123" \
  -d '{"iconNames":["test"]}'
```

**Expected**: `200 OK`

#### Test Admin Endpoint With Valid Key (Query Parameter)
```bash
curl -X POST "http://localhost:3000/api/batchIndexImages?admin_key=admin-key-123" \
  -H "Content-Type: application/json" \
  -d '{"iconNames":["test"]}'
```

**Expected**: `200 OK` (works but less secure - for testing only)

### 5. Secret Manager Integration Testing (If Deployed to GCP)

#### Test Secret Manager Access
```bash
# Set project and secret name
export GOOGLE_CLOUD_PROJECT=your-project-id
export API_KEYS_SECRET_NAME=api-keys

# List keys from Secret Manager
./scripts/manage-api-keys.sh list
```

**Expected**: Shows list of API keys (masked) or empty array if none exist

#### Test Adding Key to Secret Manager
```bash
# Generate and add new key
./scripts/manage-api-keys.sh generate
```

**Expected**: 
- Generates new key
- Adds to Secret Manager
- Displays key (save it - won't be shown again!)

#### Test Python API Reads from Secret Manager
```bash
# Deploy Python API to Cloud Run with Secret Manager config
# Or test locally with gcloud auth
gcloud auth application-default login

# Set environment variables
export API_KEYS_SECRET_NAME=api-keys
export GOOGLE_CLOUD_PROJECT=your-project-id
# Don't set API_KEYS (should read from Secret Manager)

# Start API
python embed.py

# Test with key from Secret Manager
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: key-from-secret-manager" \
  -d '{"type":"text","query":"test"}'
```

**Expected**: `200 OK` (API reads keys from Secret Manager)

### 6. Integration Testing

#### Test Full Flow: Frontend → Python API
```bash
# Terminal 1: Start Python API
export ELASTICSEARCH_ENDPOINT=your-endpoint
export ELASTICSEARCH_API_KEY=your-key
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
```

**Expected**: 
- Frontend receives request
- Frontend includes `X-API-Key: frontend-key-123` in Python API request
- Python API validates key and returns results
- Frontend returns results to client

#### Test Admin Flow: Client → Frontend Admin → Python API
```bash
# Set up services with admin key
export ADMIN_API_KEY=admin-key-123
export FRONTEND_API_KEY=frontend-key-123

# Test admin endpoint with proper auth
curl -X POST http://localhost:3000/api/batchIndexImages \
  -H "Content-Type: application/json" \
  -H "X-Admin-API-Key: admin-key-123" \
  -d '{"iconNames":["testIcon"]}'
```

**Expected**: 
- Admin endpoint validates admin key
- Frontend includes `X-API-Key: frontend-key-123` in Python API requests
- Python API validates frontend key
- Request completes successfully

### 7. Docker Testing

#### Test with Docker Compose
```bash
# Set environment variables
export ELASTICSEARCH_ENDPOINT=your-endpoint
export ELASTICSEARCH_API_KEY=your-key
export API_KEYS=test-key-123
export FRONTEND_API_KEY=test-key-123

# Start services
docker-compose up -d

# Test API authentication
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-key-123" \
  -d '{"type":"text","query":"test"}'

# Test frontend includes API key
curl -X POST http://localhost:3000/api/search \
  -H "Content-Type: application/json" \
  -d '{"type":"text","query":"test"}'

# Check logs
docker-compose logs python-api | grep -i "api key"
docker-compose logs frontend | grep -i "api key"
```

**Expected**: 
- Services start successfully
- API key authentication works
- Frontend includes API key in requests

### 8. Error Handling Testing

#### Test Missing API Key Error Message
```bash
curl -v -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"type":"text","query":"test"}'
```

**Expected**: 
- Status: `401 Unauthorized`
- Body: `{"detail": "API key required"}`

#### Test Invalid API Key Error Message
```bash
curl -v -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: wrong-key" \
  -d '{"type":"text","query":"test"}'
```

**Expected**: 
- Status: `401 Unauthorized`
- Body: `{"detail": "Invalid API key"}`

### 9. Security Testing

#### Test API Key Header Name Customization
```bash
# Set custom header
export API_KEY_HEADER=X-My-Custom-Header

# Restart API, test with custom header
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -H "X-My-Custom-Header: test-key-123" \
  -d '{"type":"text","query":"test"}'
```

**Expected**: Works with custom header name

#### Test Multiple API Keys
```bash
# Set multiple keys
export API_KEYS=key1,key2,key3

# Restart API, test with each key
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: key1" \
  -d '{"type":"text","query":"test"}'

curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: key2" \
  -d '{"type":"text","query":"test"}'
```

**Expected**: All keys work independently

### 10. Backward Compatibility Testing

#### Test Without Any API Keys Configured
```bash
# Don't set API_KEYS or API_KEYS_SECRET_NAME
unset API_KEYS
unset API_KEYS_SECRET_NAME

# Start API
python embed.py

# Test request without API key
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"type":"text","query":"test"}'
```

**Expected**: Request succeeds (backward compatible - no keys = no auth required)

## Expected Results Summary

### Python API
- ✅ Requires API key when keys are configured
- ✅ Returns 401 for missing/invalid keys
- ✅ Health endpoint doesn't require auth
- ✅ Supports multiple keys
- ✅ Backward compatible (works without keys)

### Frontend
- ✅ Includes API key in all Python API requests
- ✅ Admin endpoints support optional authentication
- ✅ Multiple auth methods supported (Bearer, header, query)

### API Key Management
- ✅ Script can generate, list, add, remove keys
- ✅ Integrates with Google Secret Manager
- ✅ Keys are securely generated (32+ characters)

## Troubleshooting

### API Key Not Working
1. **Check environment variables**: `echo $API_KEYS` or `echo $API_KEYS_SECRET_NAME`
2. **Check Python API logs**: Look for key loading messages
3. **Verify key format**: Keys should match exactly (no extra spaces)
4. **Check header name**: Default is `X-API-Key`, can be customized

### Secret Manager Not Working
1. **Verify gcloud auth**: `gcloud auth application-default login`
2. **Check project ID**: `gcloud config get-value project`
3. **Verify permissions**: Service account needs `roles/secretmanager.secretAccessor`
4. **Check secret exists**: `gcloud secrets describe api-keys`

### Admin Auth Not Working
1. **Check ADMIN_API_KEY is set**: `echo $ADMIN_API_KEY`
2. **Verify auth method**: Try Bearer token, header, or query param
3. **Check frontend logs**: Look for authentication errors

## Sign-off

Once all checks pass:

- [ ] All automated tests pass
- [ ] All manual verification steps completed
- [ ] API key authentication works correctly
- [ ] Frontend includes API keys in requests
- [ ] Admin endpoints support optional authentication
- [ ] API key management script works
- [ ] Secret Manager integration works (if deployed)
- [ ] Documentation is complete

**Phase 4 Status**: ☐ Complete ☐ In Progress ☐ Blocked

**Verified by**: _________________ **Date**: ___________

