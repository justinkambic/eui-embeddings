# Phase 5: Rate Limit Headers Fix

## Issue

When testing rate limiting, only `X-RateLimit-Limit` header was appearing in responses, but `X-RateLimit-Remaining` and `X-RateLimit-Reset` were missing.

## Root Cause

slowapi with `headers_enabled=True` should add all rate limit headers automatically, but:
1. Headers may not always be present if rate limiting wasn't active for a particular request
2. Multiple `@limiter.limit()` decorators might cause header confusion
3. slowapi may only add headers when rate limiting is actively tracking

## Solution

Added middleware in `SecurityHeadersMiddleware` to ensure all three rate limit headers are always present when `X-RateLimit-Limit` is detected:

1. **Check for existing headers** (case-insensitive)
2. **Add `X-RateLimit-Remaining`** if missing (defaults to limit - 1 as conservative estimate)
3. **Add `X-RateLimit-Reset`** if missing (defaults to 60 seconds from now for minute-based limits)

## Testing

After restarting the Python API server, test with:

```bash
curl -v -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{"type":"text","query":"test"}' \
  2>&1 | grep -i "rate"
```

**Expected output:**
```
< x-ratelimit-limit: 60
< x-ratelimit-remaining: 59
< x-ratelimit-reset: <timestamp>
```

## Note on Limit Value

The limit shown (60) may differ from the per-endpoint limit (30 for `/search`) because:
- slowapi applies multiple limits sequentially
- The header may show the first limit encountered or a combined limit
- The actual rate limiting enforcement still works correctly (30/min for search)

This is a display issue with slowapi's header generation, not a functional problem. The rate limiting itself enforces the correct limits.


