# Move Search Functionality to Python API

## Overview

Move the search logic from `frontend/pages/api/search.ts` to the Python FastAPI service (`embed.py`), making the Node.js API a thin wrapper that calls Python. Update all consumers to use the Python API.

## Implementation Steps

### 1. Add Search Endpoint to Python API (`embed.py`)

Add a new `/search` endpoint that replicates the search logic from the Node.js API:

- **Request Model**: Create `SearchRequest` with fields:
- `type`: "text" | "image" | "svg"
- `query`: string (text, base64 image, or SVG code)
- `icon_type`: Optional["icon" | "token"]
- `fields`: Optional[List[str]]

- **Response Model**: Create `SearchResponse` with:
- `results`: List of `SearchResult` (icon_name, score, descriptions, release_tag, icon_type)
- `total`: int or dict

- **Search Logic**:
- For text: Generate embeddings via `/embed`, then hybrid search (KNN + text_expansion with ELSER)
- For image: Generate embeddings via `/embed-image`, then KNN search on specified fields
- For svg: Generate embeddings via `/embed-svg`, then KNN search on specified fields
- Support `fields` parameter for field selection (defaults based on `icon_type` if not provided)
- Use existing Elasticsearch client setup (already configured in `embed.py` for ELSER)
- Replicate the exact query structure from `frontend/pages/api/search.ts` (lines 100-210)

- **Elasticsearch Client**: 
- Initialize ES client similar to existing pattern (check env vars `ELASTICSEARCH_ENDPOINT`, `ELASTICSEARCH_API_KEY`)
- Use `INDEX_NAME = "icons"` constant

### 2. Update Node.js API (`frontend/pages/api/search.ts`)

Convert to a thin proxy that forwards requests to Python API:

- Remove all search logic (embedding generation, ES queries)
- Forward POST request to `http://localhost:8000/search` (or `process.env.EMBEDDING_SERVICE_URL + "/search"`)
- Pass through request body and return response
- Keep same interface for backward compatibility

### 3. Update MCP Server (`mcp_server.py`)

- Change `SEARCH_API_URL` default from `http://localhost:3001/api/search` to `http://localhost:8000/search`
- Update environment variable documentation
- Remove `USE_DIRECT_SEARCH` logic if no longer needed (or keep as fallback)
- Update `search_via_api()` function to use new Python endpoint

### 4. Update Test Scripts

**`test_svg_search.py`**:

- Change `SEARCH_API_URL` from `http://localhost:3001/api/search` to `http://localhost:8000/search`
- Update any documentation/comments referencing the Node API

**`test_image_search.py`**:

- Change `SEARCH_API_URL` from `http://localhost:3001/api/search` to `http://localhost:8000/search`
- Update any documentation/comments referencing the Node API

### 5. Update Frontend Component (`frontend/components/mainPage/content.tsx`)

Two options:

- **Option A**: Keep calling `/api/search` (Node proxy) - no changes needed
- **Option B**: Call Python API directly - update fetch URLs to `http://localhost:8000/search`

**Recommendation**: Option A to maintain separation of concerns and avoid CORS issues.

### 6. Update Documentation

**`docs/MCP_SERVER.md`**:

- Update `SEARCH_API_URL` references from `http://localhost:3001/api/search` to `http://localhost:8000/search`
- Update environment variable examples

**`README.md`**:

- Update search API endpoint documentation
- Update environment variable descriptions

**`mcp_server_config_example.json`**:

- Update `SEARCH_API_URL` to `http://localhost:8000/search`

### 7. Environment Variables

- Keep `EMBEDDING_SERVICE_URL` (default: `http://localhost:8000`)
- Update `SEARCH_API_URL` default to `http://localhost:8000/search` (or remove if always same as embedding service)
- Ensure `ELASTICSEARCH_ENDPOINT` and `ELASTICSEARCH_API_KEY` are available to Python service

## Files to Modify

1. `embed.py` - Add `/search` endpoint
2. `frontend/pages/api/search.ts` - Convert to proxy
3. `mcp_server.py` - Update search URL and logic
4. `test_svg_search.py` - Update API URL
5. `test_image_search.py` - Update API URL
6. `docs/MCP_SERVER.md` - Update documentation
7. `README.md` - Update documentation
8. `mcp_server_config_example.json` - Update example config

## Testing Considerations

- Verify Python API search endpoint works with all three types (text, image, svg)
- Verify Node.js proxy forwards requests correctly
- Test MCP server with new endpoint
- Test both test scripts with new endpoint
- Verify frontend still works (via Node proxy)