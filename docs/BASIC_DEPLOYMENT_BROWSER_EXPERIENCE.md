# Browser Experience with API Keys

## How It Works

When you set `FRONTEND_API_KEY`, the browser experience is **seamless** - users don't need to know about API keys at all!

### Request Flow

```
Browser (User)
  ↓
  fetch('/api/search', { ... })  ← No API key needed here!
  ↓
Next.js API Route (Server-side)
  ↓
  Reads FRONTEND_API_KEY from process.env
  ↓
  Adds X-API-Key header automatically
  ↓
Python API (Cloud Run)
  ↓
  Validates API key
  ↓
  Returns response
```

### Key Points

1. **Browser never sees the API key** - it's only used server-side
2. **No user interaction needed** - API key is added automatically
3. **Standard fetch requests** - just like any other API call
4. **Secure** - API key stays on the server, never exposed to browser

## Browser Code Example

Here's what the browser code looks like (from `frontend/components/mainPage/content.tsx`):

```typescript
// Browser makes request to Next.js API route
const response = await fetch("/api/search", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    type: "image",
    query: imageBase64,
    icon_type: iconTypeFilter,
    fields: selectedFields,
  }),
});
```

**Notice**: No API key in the browser code! Just a normal fetch request.

## What Happens Server-Side

The Next.js API route (`frontend/pages/api/search.ts`) handles the API key:

```typescript
// Server-side code (runs on Cloud Run, not in browser)
const apiKey = process.env.FRONTEND_API_KEY;  // Read from environment
const headers: Record<string, string> = {
  "Content-Type": "application/json",
};
if (apiKey) {
  headers["X-API-Key"] = apiKey;  // Add API key automatically
}

// Forward to Python API with API key included
const response = await fetch(`${pythonApiUrl}/search`, {
  method: "POST",
  headers,  // Includes X-API-Key header
  body: JSON.stringify({ ... }),
});
```

## User Experience

### ✅ With FRONTEND_API_KEY Set

**What users see:**
- Normal web app experience
- No authentication prompts
- No API key input fields
- Just works!

**What happens behind the scenes:**
- Next.js API routes automatically add API key
- Python API validates the key
- Requests succeed seamlessly

### ⚠️ Without FRONTEND_API_KEY Set

**If Python API requires API keys but FRONTEND_API_KEY is not set:**

- Browser requests to `/api/search` will work (Next.js route succeeds)
- But Next.js → Python API requests will fail with 401 Unauthorized
- Users will see error messages like "Search failed" or "API key required"

**Error flow:**
```
Browser → Next.js API (✅ works)
Next.js API → Python API (❌ 401 Unauthorized)
Python API → Next.js API (❌ error response)
Next.js API → Browser (❌ error shown to user)
```

## Testing in Browser

### Normal Usage (No API Key Needed)

```javascript
// In browser console or React component
fetch('https://your-frontend-url.run.app/api/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    type: 'text',
    query: 'search icon'
  })
})
.then(r => r.json())
.then(data => console.log(data))
```

**Works automatically** - no API key needed in browser!

### Direct Python API Access (Requires API Key)

If you want to call the Python API directly from the browser (not recommended):

```javascript
// Browser would need API key (NOT RECOMMENDED - exposes key!)
fetch('https://your-python-api-url.run.app/search', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'your-api-key'  // ⚠️ Exposes API key to browser!
  },
  body: JSON.stringify({ type: 'text', query: 'test' })
})
```

**Don't do this** - it exposes your API key to anyone who views the browser's network tab!

## Security Considerations

### ✅ Secure Pattern (Current Implementation)

- API key stored server-side only (`FRONTEND_API_KEY` env var)
- Browser never sees the API key
- Next.js API routes act as a secure proxy
- API key can't be extracted from browser DevTools

### ❌ Insecure Pattern (Don't Do This)

```typescript
// DON'T expose API key to browser!
const API_KEY = process.env.NEXT_PUBLIC_FRONTEND_API_KEY;  // ⚠️ Bad!

// Browser code
fetch('/api/search', {
  headers: {
    'X-API-Key': API_KEY  // ⚠️ Exposed in browser!
  }
})
```

**Why it's bad:**
- `NEXT_PUBLIC_*` variables are exposed to the browser
- Anyone can view the API key in browser DevTools
- API key can be extracted and reused

## Deployment Checklist

When deploying with `FRONTEND_API_KEY`:

- ✅ Set `FRONTEND_API_KEY` as environment variable (server-side only)
- ✅ Do NOT use `NEXT_PUBLIC_FRONTEND_API_KEY` (would expose to browser)
- ✅ Verify Next.js API routes read from `process.env.FRONTEND_API_KEY`
- ✅ Test that browser requests work without API key
- ✅ Verify Python API receives `X-API-Key` header from Next.js

## Troubleshooting

### Browser Shows "Search failed" Error

**Possible causes:**
1. `FRONTEND_API_KEY` not set in Cloud Run environment
2. API key doesn't match one in Python API's `API_KEYS`
3. Python API not accessible from Next.js

**Check:**
```bash
# Verify environment variable is set
gcloud run services describe eui-frontend \
  --region=us-central1 \
  --project=$PROJECT_ID \
  --format="value(spec.template.spec.containers[0].env)" | grep FRONTEND_API_KEY

# Check Next.js logs
gcloud run services logs read eui-frontend \
  --region=us-central1 \
  --project=$PROJECT_ID
```

### API Key Not Being Sent

**Check Next.js API route logs:**
- Look for "Python API error" messages
- Check if `FRONTEND_API_KEY` is undefined
- Verify the header is being added

**Debug in Next.js API route:**
```typescript
console.log('API Key present:', !!process.env.FRONTEND_API_KEY);
console.log('Headers:', headers);
```

## Summary

**Browser Experience:**
- ✅ No API key needed in browser code
- ✅ Normal fetch requests work
- ✅ Seamless user experience
- ✅ API key handled automatically server-side

**Security:**
- ✅ API key never exposed to browser
- ✅ Stored server-side only
- ✅ Next.js API routes act as secure proxy

**Result:** Users get a seamless experience while API keys are handled securely behind the scenes!

