# Phase 5: Rate Limiting - Pre-Commit Checklist

Use this checklist before committing Phase 5 changes.

## Automated Verification

- [ ] **Run Phase 5 verification script**
  ```bash
  ./scripts/verify-phase5.sh
  ```
  Expected: All checks pass (22 passed, 0 warnings, 0 failed)

- [ ] **Run functional rate limiting tests** (optional but recommended)
  ```bash
  # Start Python API first:
  API_KEYS="test-key-123" python embed.py
  
  # In another terminal, run tests:
  python test_phase5_rate_limiting.py
  ```
  Expected: All tests pass or skip gracefully

## Manual Testing

### Python API Rate Limiting

- [ ] **Start Python API with API keys**
  ```bash
  API_KEYS="test-key-123" python embed.py
  ```
  Expected: Server starts without errors, shows "API keys configured: 1 key(s)"

- [ ] **Test rate limit headers**
  ```bash
  curl -v -X POST http://localhost:8000/search \
    -H "Content-Type: application/json" \
    -H "X-API-Key: test-key-123" \
    -d '{"type":"text","query":"test"}' \
    2>&1 | grep -i "rate"
  ```
  Expected: Headers include `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

- [ ] **Test rate limit enforcement** (optional - requires many requests)
  ```bash
  # Make 35 requests rapidly (limit is 30/minute)
  for i in {1..35}; do
    curl -X POST http://localhost:8000/search \
      -H "Content-Type: application/json" \
      -H "X-API-Key: test-key-123" \
      -d '{"type":"text","query":"test"}' \
      -w "\nStatus: %{http_code}\n" 2>/dev/null | tail -1
  done
  ```
  Expected: First 30 requests succeed (200), requests 31+ return 429

- [ ] **Test health endpoint is not rate limited**
  ```bash
  # Make multiple rapid requests
  for i in {1..10}; do
    curl -s http://localhost:8000/health | jq -r '.status'
  done
  ```
  Expected: All requests succeed (status: "ok")

### Frontend API Rate Limiting

- [ ] **Start Next.js dev server**
  ```bash
  cd frontend
  npm run dev
  ```
  Expected: Server starts, `.env.local` is loaded with `FRONTEND_API_KEY`

- [ ] **Test admin endpoint rate limiting** (optional)
  ```bash
  # Make multiple requests to admin endpoint
  for i in {1..12}; do
    curl -X POST http://localhost:3000/api/batchIndexImages \
      -H "Content-Type: application/json" \
      -d '{"iconNames":["test"]}' \
      -w "\nStatus: %{http_code}\n" 2>/dev/null | tail -1
    sleep 0.1
  done
  ```
  Expected: First 10 requests succeed or return expected errors, request 11+ returns 429

### Code Quality

- [ ] **Check for linter errors**
  - Linter warnings about unresolved imports are expected (virtual environment not detected)
  - No actual code errors should be present

- [ ] **Verify all files are saved**
  - Check that all modified files are saved in your editor

## Files to Commit

### New Files
- [ ] `frontend/lib/rateLimit.ts` - Rate limiting utility for Next.js
- [ ] `scripts/verify-phase5.sh` - Phase 5 verification script
- [ ] `test_phase5_rate_limiting.py` - Functional rate limiting tests
- [ ] `docs/PHASE5_RATE_LIMITING_IMPLEMENTATION.md` - Implementation documentation
- [ ] `docs/PHASE5_PRE_COMMIT_CHECKLIST.md` - This file

### Modified Files
- [ ] `embed.py` - Added rate limiting middleware and decorators
- [ ] `requirements.txt` - Added `slowapi>=0.1.9`
- [ ] `frontend/pages/api/batchIndexImages.ts` - Added rate limiting
- [ ] `frontend/pages/api/batchIndexSVG.ts` - Added rate limiting
- [ ] `frontend/pages/api/batchIndexText.ts` - Added rate limiting
- [ ] `token_renderer/server.js` - Added express-rate-limit middleware
- [ ] `token_renderer/package.json` - Added `express-rate-limit` dependency
- [ ] `docs/ENVIRONMENT_VARIABLES.md` - Updated with rate limit variables
- [ ] `CHANGELOG.md` - Added Phase 5 entry

### Environment Files (DO NOT COMMIT)
- [ ] `frontend/.env.local` - Should be in `.gitignore` (contains API keys)

## Final Checks

- [ ] **Verify multiprocessing fix works**
  - Start Python API: `API_KEYS="test" python embed.py`
  - Expected: Server starts without semaphore warnings
  - Expected: Server stays running (doesn't immediately exit)

- [ ] **Test with actual frontend**
  - Start both Python API and Next.js frontend
  - Perform a search in the UI
  - Expected: Search works, rate limit headers are present in network tab

- [ ] **Review CHANGELOG.md**
  - Verify Phase 5 entry is complete and accurate

## Ready to Commit?

Once all checks pass:

1. **Stage files:**
   ```bash
   git add embed.py requirements.txt frontend/lib/rateLimit.ts \
     frontend/pages/api/batchIndex*.ts token_renderer/server.js \
     token_renderer/package.json scripts/verify-phase5.sh \
     test_phase5_rate_limiting.py docs/PHASE5*.md \
     docs/ENVIRONMENT_VARIABLES.md CHANGELOG.md
   ```

2. **Verify staged files:**
   ```bash
   git status
   ```
   Make sure `.env.local` is NOT staged!

3. **Commit:**
   ```bash
   git commit -m "Phase 5: Implement rate limiting for all services

   - Add slowapi rate limiting to Python API (per-endpoint limits)
   - Add in-memory rate limiting to Next.js API routes
   - Add express-rate-limit to token renderer
   - Configure rate limit headers in all responses
   - Add verification scripts and documentation
   - Fix multiprocessing start method for macOS compatibility"
   ```

## Notes

- The functional tests (`test_phase5_rate_limiting.py`) require the services to be running
- Rate limiting tests that exceed limits may take time (waiting for rate limit windows)
- Some tests may skip gracefully if services aren't running (not a failure)
- The semaphore warning fix should prevent multiprocessing issues on macOS


