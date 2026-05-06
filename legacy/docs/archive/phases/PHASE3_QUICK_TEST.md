# Phase 3: Quick Test Guide

Quick commands to verify Phase 3 implementation is complete.

## Quick Verification (30 seconds)

```bash
# Run automated verification script
./scripts/verify-phase3.sh
```

Expected output: **✓ Phase 3 verification PASSED!** with 24+ passed checks.

## Quick Local Test (2 minutes)

### 1. Test Security Headers
```bash
# Start API (in one terminal)
export ELASTICSEARCH_ENDPOINT=your-endpoint
export ELASTICSEARCH_API_KEY=your-key
export PYTHON_API_BASE_URL=https://api.example.com
python embed.py

# Test headers (in another terminal)
curl -I http://localhost:8000/health | grep -i "x-content-type\|x-frame\|xss\|strict-transport\|content-security"
```

Should see:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Content-Security-Policy: default-src 'self'`
- `Strict-Transport-Security` (if HTTPS detected)

### 2. Test Health Endpoint
```bash
curl http://localhost:8000/health
```

Should return:
```json
{"status":"ok","service":"eui-icon-embeddings","elasticsearch":"..."}
```

### 3. Test CORS Configuration
```bash
curl -X OPTIONS http://localhost:8000/search \
  -H "Origin: https://icons.example.com" \
  -H "Access-Control-Request-Method: POST" \
  -v 2>&1 | grep -i "access-control"
```

Should include CORS headers.

## Quick Docker Test (3 minutes)

```bash
# Build and test
docker-compose up -d

# Check services are running
docker-compose ps

# Test API
curl http://localhost:8000/health

# Test Frontend
curl http://localhost:3000

# Cleanup
docker-compose down
```

## Quick Python Test Suite (1 minute)

```bash
# Run Phase 3 tests
python test_phase3_https.py

# Or with pytest
pytest test_phase3_https.py -v
```

## What to Check

✅ **All checks should pass:**
- Security headers present
- HTTPS detection works
- CORS configured correctly
- Health endpoint accessible
- Configuration files valid
- Documentation complete

## If Something Fails

1. **Security headers missing**: Check `embed.py` has `SecurityHeadersMiddleware`
2. **CORS errors**: Verify `CORS_ORIGINS` environment variable
3. **Health check fails**: Check Elasticsearch connection
4. **Docker issues**: Verify Dockerfiles exist and are valid

See `docs/PHASE3_VERIFICATION_CHECKLIST.md` for detailed troubleshooting.

