# Changelog

All notable changes to the EUI Icon Embeddings project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [Unreleased]

### Added
- **Automated EUI Icon Indexing Script** (`scripts/index_eui_icons.py`)
  - Automated repository cloning and version detection
  - Extracts `typeToPathMap` from EUI repository for icon name resolution
  - Recursive SVG file discovery across entire repository
  - Version tracking with `data/processed_version.txt`
  - Skips version only if all icons for that version are already indexed
  - Indexes both regular icons and tokenized versions
  - Document ID format: `{icon_name}_{release_tag}` for icons, `{icon_name}_token_{release_tag}` for tokens
  - Error handling and progress reporting

- **Token Renderer Service** (`token_renderer/`)
  - Standalone Node.js service for rendering EuiToken components to SVG
  - Decoupled from web UI for use by Python scripts
  - REST API endpoints:
    - `GET /health` - Health check
    - `POST /render-token` - Render single token
    - `POST /render-tokens` - Batch render tokens
  - Runs on port 3002 by default (configurable via `TOKEN_RENDERER_PORT`)

- **Elasticsearch Index Mapping Updates**
  - Added `filename` field (keyword) - Original SVG filename
  - Added `release_tag` field (keyword) - EUI version tag (e.g., "v109.0.0")
  - Added `icon_type` field (keyword) - "icon" or "token"
  - Added `token_type` field (keyword) - Token type for token icons (optional)
  - Added `svg_content` field (text, not indexed) - Full SVG content for reference

- **Documentation**
  - `docs/REINDEXING_STRATEGY.md` - Plan for automated indexing strategy
  - `docs/TOKEN_INDEXING_PLAN.md` - Plan for indexing tokenized icon versions
  - `docs/IMAGE_NORMALIZATION_PLAN.md` - Plan for normalizing search images
  - `docs/FRONTEND_SEARCH.md` - Plan for frontend search implementation

### Changed
- **Index Mapping** (`utils/es_index_setup.py`)
  - Changed `icon_type` values from "regular" to "icon"
  - Updated `svg_embedding` dimensions from 384 to 512 to match CLIP model output
  - Added version tracking and icon type fields

- **Frontend Search** (`frontend/pages/index.tsx`)
  - Added image paste functionality (Ctrl/Cmd+V)
  - Added file upload for image search
  - Added SVG code paste with debounced search
  - Added image preview using `EuiImage` component
  - Added loading states and result filtering
  - Improved icon display with similarity scores

- **Search API Response** (`frontend/pages/api/search.ts`)
  - Returns `icon_name` from document source instead of document ID
  - Added `release_tag` and `icon_type` fields to response
  - Document IDs include version tag (e.g., "search_v109.0.0"), but `icon_name` field returns clean name (e.g., "search")

- **Test Scripts** (`test_svg_search.py`)
  - Updated `--icon-name` flag to use EUI repository mapping
  - Extracts `typeToPathMap` from EUI repository to convert icon names to filenames
  - Searches EUI repository recursively for SVG files

### Fixed
- **Search API Bug**
  - Fixed issue where search API returned document ID (e.g., "search_v109.0.0") instead of icon name (e.g., "search")
  - Now returns `icon_name` field from document source

- **SVG Rendering**
  - Fixed issue where SVGs without explicit `fill` attributes were rendered as all-black images
  - Added preprocessing to ensure paths have `fill="black"` and white background
  - Fixed dimension mismatch (384 vs 512) for CLIP embeddings

- **Image Search**
  - Fixed field mismatch where image search was querying `image_embedding` but SVGs were indexed in `svg_embedding`
  - Updated search API to query `svg_embedding` for image searches (both use CLIP, compatible)
  - Implemented automatic background detection and inversion for image normalization

## [2025-11-11] - Frontend Search Improvements

### Added
- **Frontend Search UI** (`frontend/pages/index.tsx`)
  - Image paste support (Ctrl/Cmd+V)
  - File upload for image search
  - SVG code paste with debounced search
  - Image preview display
  - Filtered results display with similarity scores
  - Loading states and error handling

- **File Name Mapping** (`frontend/utils/file_to_name.ts`)
  - Complete mapping of EUI icon filenames to icon names
  - 524 icon mappings extracted from EUI codebase

- **Documentation**
  - `docs/FRONTEND_SEARCH.md` - Frontend search implementation plan
  - `docs/REINDEXING_STRATEGY.md` - Automated indexing strategy plan

### Changed
- Updated frontend to use icon name mapping instead of direct filename usage
- Improved search result display with icon names and scores

## [2025-11-10] - Image Normalization & Token Indexing Planning

### Added
- **Image Normalization** (`image_processor.py`)
  - `normalize_search_image()` function for preprocessing search images
  - Automatic background detection (light/dark)
  - Automatic inversion for dark backgrounds
  - Grayscale conversion and contrast normalization
  - Ensures consistency with indexed SVG embeddings

- **Image Normalization Tests** (`test_image_normalization.py`)
  - Test script for visualizing normalized images
  - Comparison view (original vs normalized)
  - Image analysis (pixel values, unique colors, etc.)

- **SVG Normalization Tests** (`test_svg_normalization.py`)
  - Test script for visualizing SVG preprocessing
  - Tests the same preprocessing used in `embed.py`
  - Validates SVG-to-image conversion

- **Documentation**
  - `docs/IMAGE_NORMALIZATION_PLAN.md` - Image normalization strategy
  - `docs/TOKEN_INDEXING_PLAN.md` - Token indexing implementation plan

### Changed
- **Embedding Service** (`embed.py`)
  - Updated `/embed-image` endpoint to use `normalize_search_image()`
  - Improved image preprocessing for better search accuracy

### Fixed
- Fixed issue where real-world screenshots didn't match indexed embeddings
- Improved search accuracy for screenshots from different backgrounds (light/dark mode)

## [2025-11-10] - Initial Project Setup

### Added
- **Core Infrastructure**
  - FastAPI embedding service (`embed.py`)
    - Text embeddings using `all-MiniLM-L6-v2` (384 dimensions)
    - ELSER sparse embeddings via Elasticsearch inference API
    - Image embeddings using CLIP (`clip-ViT-B-32`, 512 dimensions)
    - SVG embeddings via SVG-to-image conversion using CLIP
  - Next.js frontend with API routes
  - Elasticsearch integration with vector search support

- **Elasticsearch Setup** (`utils/es_index_setup.py`)
  - Index creation with proper mappings
  - Support for dense vectors (384 and 512 dimensions)
  - Support for sparse vectors (ELSER)
  - KNN search configuration

- **Batch Processing Scripts**
  - `batch_embed_svgs.py` - Batch process SVG files and generate embeddings
  - Support for reading SVG paths from `.svgpaths` file
  - Optional Elasticsearch indexing
  - Skip already-indexed files with `--force` override
  - Limit processing with `--limit` flag

- **API Endpoints** (`frontend/pages/api/`)
  - `search.ts` - Unified search API (text, image, SVG)
  - `saveIcon.ts` - Single icon indexing
  - `batchIndexText.ts` - Batch text description indexing
  - `batchIndexImages.ts` - Batch image embedding indexing
  - `batchIndexSVG.ts` - Batch SVG embedding indexing
  - `getAllIndexedIcons.ts` - List all indexed icons

- **Icon Rendering Utilities**
  - `frontend/utils/icon_renderer.ts` - React-based icon rendering
  - `utils/icon_renderer.js` - Node.js icon rendering utilities
  - SVG normalization and standardization

- **Testing & Diagnostics**
  - `test_elasticsearch_setup.py` - Elasticsearch validation
  - `test_svg_search.py` - SVG search testing
  - `test_image_search.py` - Image search testing
  - `test_svg_conversion.py` - SVG conversion testing
  - `diagnose_embeddings.py` - Embedding diagnostics (duplicates, similarity)
  - `check_index.py` - Index document count checker

- **Image Processing** (`image_processor.py`)
  - Image normalization utilities
  - Image-to-bytes conversion
  - Size standardization

- **SVG Processing** (`svg_processor.py`)
  - SVG normalization utilities
  - ViewBox extraction and standardization

- **Documentation**
  - `README.md` - Project overview and setup instructions
  - `docs/PROJECT_PLAN.md` - High-level project plan and architecture
  - `docs/IMPLEMENTATION_PLAN.md` - Detailed implementation plan
  - `docs/SETUP_GUIDE.md` - Setup instructions
  - `docs/TROUBLESHOOTING.md` - Common issues and solutions
  - `docs/KNOWN_ISSUES_FIXES.md` - Known issues and their fixes

- **Configuration**
  - `.gitignore` - Ignore patterns
  - `.svgpaths` - SVG file paths for batch processing
  - `requirements.txt` - Python dependencies
  - `frontend/package.json` - Node.js dependencies

### Features
- **Multi-Modal Search**
  - Text-based semantic search with dense and sparse embeddings
  - Image-based visual similarity search
  - SVG code-based structural search

- **Hybrid Search**
  - Combines dense vector search (KNN) with sparse vector search (ELSER)
  - Improved relevance for text queries

- **Batch Indexing**
  - Batch processing of hundreds of icons
  - Progress tracking and error reporting
  - Resume capability (skip already-indexed files)

## Technical Details

### Embedding Models
- **Text (Dense)**: `all-MiniLM-L6-v2` - 384 dimensions
- **Text (Sparse)**: Elasticsearch ELSER (`.elser_model_2`)
- **Image/SVG**: `sentence-transformers/clip-ViT-B-32` - 512 dimensions

### Elasticsearch Index Structure
```
Index: "icons"
Fields:
  - icon_name (keyword)
  - filename (keyword)
  - release_tag (keyword)
  - icon_type (keyword) - "icon" or "token"
  - token_type (keyword) - optional
  - descriptions (text array)
  - text_embedding (dense_vector, 384 dims, cosine similarity)
  - text_embedding_sparse (sparse_vector for ELSER)
  - image_embedding (dense_vector, 512 dims, cosine similarity)
  - svg_embedding (dense_vector, 512 dims, cosine similarity)
  - svg_content (text, not indexed)
```

### Document ID Format
- Regular icons: `{icon_name}_{release_tag}` (e.g., `app_discover_v109.0.0`)
- Token icons: `{icon_name}_token_{release_tag}` (e.g., `app_discover_token_v109.0.0`)

### Environment Variables
- `ELASTICSEARCH_ENDPOINT` - Elasticsearch cluster endpoint
- `ELASTICSEARCH_API_KEY` - Elasticsearch API key
- `EUI_LOCATION` - Directory path for EUI repository (default: `./data/eui`)
- `EUI_REPO` - Git repository URL (default: `https://github.com/elastic/eui.git`)
- `EMBEDDING_SERVICE_URL` - Embedding service URL (default: `http://localhost:8000`)
- `TOKEN_RENDERER_URL` - Token renderer service URL (default: `http://localhost:3002`)
- `TOKEN_RENDERER_PORT` - Token renderer service port (default: `3002`)

## Future Plans

- Complete automated indexing implementation
- Token rendering integration
- Version filtering in search API
- Support for multiple EUI versions in search results
- Enhanced frontend UI improvements
- Performance optimizations for large-scale indexing

