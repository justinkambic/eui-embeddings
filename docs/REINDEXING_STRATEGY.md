# Automated EUI Icon Indexing Strategy

## Overview

Revise the indexing strategy to automate EUI icon scraping, handle filename-to-icon-name mapping before indexing, and support version tracking. This eliminates the need for downstream clients to handle EUI-specific mapping logic.

## Goals

1. Automate EUI repository cloning and version management
2. Extract and use `typeToPathMap` for filename-to-icon-name conversion
3. Index both bare SVG and EuiToken versions of each icon
4. Add version tracking to prevent duplicate results across EUI versions
5. Store processed version tags for incremental updates

## Implementation

### 1. Create Automated Indexing Script

**File**: `scripts/index_eui_icons.py`

Create a new Python script that orchestrates the entire indexing process:

- **Repository Management**:
  - Check if `$EUI_LOCATION` directory exists, create if missing
  - Clone `$EUI_REPO` into `$EUI_LOCATION` if not already present
  - If repo exists, fetch latest tags and checkout the most recent major release tag (e.g., `v109.0.0`)
  - Use git commands to identify latest major release (tags matching `v\d+\.0\.0` pattern)

- **Version Tracking**:
  - Read processed version from `data/processed_version.txt` (or similar)
  - Compare with latest major release tag
  - Skip processing if already processed, or prompt for re-indexing
  - Write successful version tag to file after completion

- **Icon Mapping Extraction**:
  - Read `packages/eui/src/components/icon/icon_map.ts` from cloned repo
  - Parse TypeScript file to extract `typeToPathMap` object
  - Handle TypeScript syntax (export const, object literals, comments)
  - Create reverse mapping: `filename -> icon_name` for indexing

- **SVG Discovery**:
  - Find all SVG files in EUI repo (typically in `packages/eui/src/components/icon/assets/`)
  - Match SVG filenames (without extension) to `typeToPathMap` values
  - Warn for SVGs that don't match any map entry
  - Warn for map entries that don't have corresponding SVG files

- **Indexing Process**:
  - For each matched icon:
    1. Read bare SVG file content
    2. Generate SVG embedding using existing `/embed-svg` endpoint
    3. Index with document ID: `{icon_name}_{release_tag}` (e.g., `app_discover_v109.0.0`)
    4. Render EuiToken version (requires Node.js/React rendering - see Token Rendering section)
    5. Generate token SVG embedding
    6. Index with document ID: `{icon_name}_token_{release_tag}` (e.g., `app_discover_token_v109.0.0`)

- **Document Structure**:
  ```python
  {
    "icon_name": "app_discover",  # From typeToPathMap key
    "filename": "app_discover",   # Original SVG filename
    "release_tag": "v109.0.0",    # EUI version
    "icon_type": "regular",       # or "token"
    "token_type": "string",       # Only for token icons
    "svg_embedding": [...],       # 512-dim CLIP embedding
    "svg_content": "...",         # Optional: full SVG content
  }
  ```

### 2. Update Elasticsearch Index Mapping

**File**: `utils/es_index_setup.py`

Add new fields to index mapping:

- `release_tag` (keyword) - EUI version tag
- `icon_type` (keyword) - "regular" or "token"
- `token_type` (keyword) - Token type for token icons (optional)
- `filename` (keyword) - Original SVG filename

Update `INDEX_MAPPING` to include these fields.

### 3. Token Rendering Implementation

**Option A: Python-based (Recommended for standalone API)**

Create a Python function that uses a headless browser or SVG manipulation:

- Use `playwright` or `selenium` to render React components
- Or use `cairosvg` with custom preprocessing to simulate EuiToken outline
- Render EuiToken component with icon and extract SVG

**File**: `scripts/render_token.py` or integrate into `index_eui_icons.py`

**Option B: Node.js Service**

Create a Node.js microservice that uses the existing `frontend/utils/icon_renderer.ts`:

- Expose HTTP endpoint: `POST /render-token` with `{ iconName: string, tokenType?: string }`
- Return SVG string
- Python script calls this service

**File**: `scripts/token_renderer_service.js` or extend existing frontend API

### 4. Environment Variables

Add to `.env` or document required variables:

- `EUI_LOCATION` - Directory path for EUI repository (e.g., `./data/eui`)
- `EUI_REPO` - Git repository URL (e.g., `https://github.com/elastic/eui.git`)
- `EMBEDDING_SERVICE_URL` - URL for embedding service (default: `http://localhost:8000`)
- `TOKEN_RENDERER_URL` - URL for token rendering service (if using Option B)

### 5. Update Batch Embedding Script

**File**: `batch_embed_svgs.py`

Deprecate or update to work alongside new automated script:

- Keep for manual/legacy use cases
- Add note that automated script is preferred
- Or refactor shared functions into a common module

### 6. Version Management

**File**: `data/processed_version.txt` (or `data/processed_versions.json`)

Store processed versions:

- Simple text file: single line with latest processed tag
- Or JSON file: `{ "latest": "v109.0.0", "processed": ["v109.0.0", "v108.0.0"] }`

### 7. Error Handling and Warnings

- **Unmapped SVGs**: Warn and skip (don't index)
- **Missing SVGs**: Warn for icons in `typeToPathMap` without corresponding files
- **Git errors**: Handle network issues, authentication, tag not found
- **Rendering errors**: Log and continue with other icons
- **Indexing errors**: Track failures and report at end

### 8. Search API Updates

**File**: `frontend/pages/api/search.ts`

Update search to handle version filtering:

- Add optional `release_tag` filter parameter
- Default to latest version or all versions
- Group results by `icon_name` and show best match per icon
- Or allow filtering by version in query

## Files to Create

- `scripts/index_eui_icons.py` - Main automation script
- `scripts/render_token.py` - Token rendering (if Option A)
- `data/processed_version.txt` - Version tracking file
- `docs/AUTOMATED_INDEXING.md` - Usage documentation

## Files to Modify

- `utils/es_index_setup.py` - Add new fields to index mapping
- `batch_embed_svgs.py` - Add deprecation notice or refactor
- `frontend/pages/api/search.ts` - Add version filtering support
- `.env.example` - Document new environment variables

## Dependencies

- `gitpython` or subprocess for git operations
- `playwright` or `selenium` for token rendering (Option A)
- `requests` for API calls (already present)
- `elasticsearch` client (already present)

## Testing Strategy

1. Test with a single icon first
2. Test version detection and tag checkout
3. Test mapping extraction and validation
4. Test token rendering with a few icons
5. Test full indexing run with `--limit` flag
6. Verify version tracking file updates
7. Test search with version filtering

## Migration Considerations

- Existing indexed icons won't have `release_tag` field
- Consider adding migration script to backfill `release_tag` for existing documents
- Or use separate index for new automated indexing
- Document breaking changes for search API consumers