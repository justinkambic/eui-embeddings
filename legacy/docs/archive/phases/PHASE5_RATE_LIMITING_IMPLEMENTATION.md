# Phase 5: Rate Limiting - Implementation Summary

This document summarizes the implementation of Phase 5 (Rate Limiting) from the dockerization plan.

## What Was Implemented

### 1. Python API Rate Limiting

**Library**: `slowapi` - Simple rate limiting library for FastAPI

**Features:**
- Rate limiting middleware integrated with FastAPI
- Tracks requests by API key (if available) or IP address
- Per-endpoint rate limits:
  - `/search` - Stricter limits: 30 requests/minute, 500 requests/hour
  - `/embed`, `/embed-image`, `/embed-svg` - Moderate limits: 60 requests/minute, 1000 requests/hour (configurable)
- In-memory rate limiting (sufficient for low traffic)
- Rate limit headers added to responses (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`)

**Configuration:**
- `RATE_LIMIT_PER_MINUTE` - Default: 60 requests/minute
- `RATE_LIMIT_PER_HOUR` - Default: 1000 requests/hour
- `RATE_LIMIT_BURST` - Default: 10 (reserved for future use)

**Implementation:**
- `get_rate_limit_key()` function prioritizes API key over IP address
- Rate limiter initialized after API keys are loaded
- Decorators added to all protected endpoints
- Health endpoint excluded from rate limiting

### 2. Frontend API Rate Limiting

**Library**: Custom in-memory rate limiting (`frontend/lib/rateLimit.ts`)

**Features:**
- In-memory rate limiting for Next.js API routes
- Tracks requests by IP address
- Automatic cleanup of expired entries
- Rate limit headers included in responses

**Implementation:**
- Added to admin endpoints (`/api/batchIndexImages`, `/api/batchIndexSVG`, `/api/batchIndexText`)
- Stricter limits: 10 requests per minute (admin operations)
- Rate limit headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

**Note**: `/api/search` forwards to Python API, which handles rate limiting.

### 3. Token Renderer Rate Limiting

**Library**: `express-rate-limit` - Express.js rate limiting middleware

**Features:**
- Rate limiting middleware for all routes
- Stricter limits (rendering is resource-intensive)
- Default: 10 requests per minute per IP
- Configurable via `TOKEN_RENDERER_RATE_LIMIT` environment variable

**Implementation:**
- Applied to all routes in token renderer service
- Uses standard rate limit headers
- Tracks by IP address (internal network IPs)

### 4. Rate Limit Headers

All services now include rate limit headers in responses:

- `X-RateLimit-Limit` - Maximum number of requests allowed
- `X-RateLimit-Remaining` - Number of requests remaining in current window
- `X-RateLimit-Reset` - Time when the rate limit resets (ISO 8601 format)

## Architecture

### Rate Limiting Flow

```
Client Request
    ↓
[Rate Limiter]
    ├─ Extract identifier (API key or IP)
    ├─ Check current count vs limit
    ├─ Increment count if under limit
    └─ Return 429 if exceeded
    ↓
[Endpoint Handler]
    ↓
[Response with Rate Limit Headers]
```

### Tracking Strategy

**Python API:**
- Primary: API key (if available and valid)
- Fallback: IP address
- Benefits: Per-key tracking allows different limits per client

**Frontend API:**
- IP address (for unauthenticated routes)
- Benefits: Simple, works for admin endpoints

**Token Renderer:**
- IP address (internal network)
- Benefits: Simple, sufficient for internal service

## Configuration

### Python API

```bash
# Default limits
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000
RATE_LIMIT_BURST=10

# Per-endpoint limits (hardcoded):
# /search: 30/min, 500/hour
# /embed, /embed-image, /embed-svg: 60/min, 1000/hour (configurable)
```

### Frontend API

```bash
# Admin endpoints: 10 requests/minute (hardcoded)
# No environment variables needed
```

### Token Renderer

```bash
TOKEN_RENDERER_RATE_LIMIT=10  # requests per minute
```

## Testing

### Test Rate Limiting

```bash
# Test Python API rate limiting
export API_KEYS=test-key-123
python embed.py

# Make requests rapidly (should hit rate limit)
for i in {1..65}; do
  curl -X POST http://localhost:8000/search \
    -H "Content-Type: application/json" \
    -H "X-API-Key: test-key-123" \
    -d '{"type":"text","query":"test"}' \
    -w "\nStatus: %{http_code}\n"
done

# Should see 429 Too Many Requests after limit exceeded
```

### Test Rate Limit Headers

```bash
curl -v -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-key-123" \
  -d '{"type":"text","query":"test"}' \
  2>&1 | grep -i "rate"
```

**Expected headers:**
- `X-RateLimit-Limit: 30`
- `X-RateLimit-Remaining: 29` (or lower)
- `X-RateLimit-Reset: <timestamp>`

## Files Created/Modified

### New Files:
- `frontend/lib/rateLimit.ts` - In-memory rate limiting utilities for Next.js
- `scripts/verify-phase5.sh` - Phase 5 verification script
- `docs/PHASE5_RATE_LIMITING_IMPLEMENTATION.md` - This file

### Modified Files:
- `embed.py` - Added rate limiting middleware and decorators
- `requirements.txt` - Added `slowapi>=0.1.9`
- `frontend/pages/api/batchIndexImages.ts` - Added rate limiting
- `frontend/pages/api/batchIndexSVG.ts` - Added rate limiting
- `frontend/pages/api/batchIndexText.ts` - Added rate limiting
- `token_renderer/server.js` - Added express-rate-limit middleware
- `token_renderer/package.json` - Added `express-rate-limit` dependency
- `docs/ENVIRONMENT_VARIABLES.md` - Updated with rate limit variables

## Rate Limit Configuration Summary

### Python API Endpoints

| Endpoint | Per Minute | Per Hour | Notes |
|----------|------------|----------|-------|
| `/search` | 30 | 500 | Stricter (hardcoded) |
| `/embed` | 60 | 1000 | Configurable via env vars |
| `/embed-image` | 60 | 1000 | Configurable via env vars |
| `/embed-svg` | 60 | 1000 | Configurable via env vars |
| `/health` | No limit | No limit | Excluded from rate limiting |

### Frontend API Endpoints

| Endpoint | Per Minute | Notes |
|----------|------------|-------|
| `/api/search` | Forwarded to Python API | Python handles rate limiting |
| `/api/batchIndexImages` | 10 | Admin endpoint (hardcoded) |
| `/api/batchIndexSVG` | 10 | Admin endpoint (hardcoded) |
| `/api/batchIndexText` | 10 | Admin endpoint (hardcoded) |

### Token Renderer

| Endpoint | Per Minute | Notes |
|----------|------------|-------|
| All routes | 10 | Configurable via `TOKEN_RENDERER_RATE_LIMIT` |

## Error Responses

When rate limit is exceeded:

**Python API:**
```json
{
  "detail": "Rate limit exceeded: 30 per 1 minute"
}
```
Status: `429 Too Many Requests`

**Frontend API:**
```json
{
  "error": "Rate limit exceeded",
  "rateLimit": {
    "limit": 10,
    "remaining": 0,
    "reset": 1234567890
  }
}
```
Status: `429 Too Many Requests`

## Next Steps

Phase 5 is complete. The next phases are:
- **Phase 6**: GCP Deployment Configuration (partially done)
- **Phase 7**: Production Hardening

## Notes

- Rate limiting uses in-memory storage (clears on restart)
- For high-traffic production, consider Redis-based rate limiting
- Rate limits are per API key (Python API) or per IP (Frontend/Token Renderer)
- Health endpoints are excluded from rate limiting
- Rate limit headers are included in all responses for transparency


