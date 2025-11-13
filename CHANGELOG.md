# Changelog

All notable changes to the EUI Icon Embeddings project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2025-11-12] - Phase 5: Rate Limiting

### Added
- **Rate limiting for Python API** (`embed.py`):
  - Integrated `slowapi` library for FastAPI rate limiting
  - Per-endpoint rate limits:
    - `/search`: 30 requests/minute, 500 requests/hour (stricter limits)
    - `/embed`, `/embed-image`, `/embed-svg`: 60 requests/minute, 1000 requests/hour (configurable)
  - Rate limiting tracks by API key (if available) or IP address
  - Rate limit headers added to all responses (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`)
  - Health endpoint excluded from rate limiting
  - Manual header injection in middleware to ensure all headers are present
- **Rate limiting for Next.js API routes**:
  - Created `frontend/lib/rateLimit.ts` for in-memory rate limiting
  - Added rate limiting to admin endpoints (`/api/batchIndexImages`, `/api/batchIndexSVG`, `/api/batchIndexText`)
  - Stricter limits: 10 requests per minute for admin operations
  - Rate limit headers included in responses
- **Rate limiting for Token Renderer**:
  - Integrated `express-rate-limit` middleware
  - Default: 10 requests per minute per IP (configurable via `TOKEN_RENDERER_RATE_LIMIT`)
  - Applied to all routes (rendering is resource-intensive)
- **Environment variables**:
  - `RATE_LIMIT_PER_MINUTE` - Default: 60 requests/minute
  - `RATE_LIMIT_PER_HOUR` - Default: 1000 requests/hour
  - `RATE_LIMIT_BURST` - Default: 10 (reserved for future use)
  - `TOKEN_RENDERER_RATE_LIMIT` - Default: 10 requests/minute
- **Functional test script**:
  - `test_phase5_rate_limiting.py` - Comprehensive test script for rate limiting functionality
  - Tests rate limit headers, request limits, and API key authentication
  - Supports `TEST_API_KEY` environment variable for testing with specific keys
- **Documentation**:
  - `docs/PHASE5_RATE_LIMITING_IMPLEMENTATION.md` - Phase 5 implementation details
  - `docs/PHASE5_PRE_COMMIT_CHECKLIST.md` - Pre-commit verification checklist
  - `docs/PHASE5_RATE_LIMIT_HEADERS_FIX.md` - Documentation for rate limit header fixes
  - `scripts/verify-phase5.sh` - Automated verification script for Phase 5

### Changed
- **Python API** (`embed.py`):
  - Added rate limiting middleware and decorators to protected endpoints
  - Modified endpoint signatures to include `Request` parameter for rate limiting
  - Updated security headers middleware to extract rate limit info from `request.state.view_rate_limit` and add headers manually
  - Set `headers_enabled=False` in slowapi to avoid response parameter requirement issues
  - Added multiprocessing start method configuration (`spawn`) to prevent semaphore leaks on macOS
  - Modified uvicorn startup to remove `reload=True` and set explicit `log_level="info"` when running directly
  - Middleware order: `SlowAPIMiddleware` added after limiter initialization, before security headers
- **Frontend API routes**:
  - Added rate limiting checks before admin authentication
  - Added rate limit headers to responses
  - Improved error handling in `frontend/pages/api/search.ts` with detailed connection error messages
- **Token Renderer** (`token_renderer/server.js`):
  - Added express-rate-limit middleware to all routes
- **Dependencies**:
  - Added `slowapi>=0.1.9` to `requirements.txt`
  - Added `express-rate-limit>=7.1.5` to `token_renderer/package.json`
- **Documentation**:
  - Updated `docs/ENVIRONMENT_VARIABLES.md` with rate limiting configuration

### Fixed
- **Rate limit headers**:
  - Fixed issue where `X-RateLimit-Remaining` and `X-RateLimit-Reset` headers were missing from responses
  - Implemented manual header injection in middleware to ensure all three headers are always present
  - Headers now correctly extracted from slowapi's `request.state.view_rate_limit` object
- **Python API startup**:
  - Fixed semaphore leak warnings on macOS by setting multiprocessing start method to `spawn`
  - Fixed server shutdown issues when running directly with `python embed.py`
- **slowapi integration**:
  - Fixed `Exception: parameter 'response' must be an instance of starlette.responses.Response` error
  - Disabled slowapi's automatic header injection (`headers_enabled=False`) and handled headers manually
- **Frontend error handling**:
  - Improved error messages for connection failures (`ECONNREFUSED`, `ETIMEDOUT`) in search API proxy
  - Added detailed error information including Python API URL for debugging

### Security
- Rate limiting protects against abuse and DoS attacks
- Per-API-key rate limiting allows different limits per client
- Stricter limits on resource-intensive endpoints (search, rendering)
- Rate limit headers provide transparency to clients

## [2025-11-12] - Phase 4: API Key Authentication

### Added
- **API Key Management Script** (`scripts/manage-api-keys.sh`)
  - Generate secure random API keys (32+ characters)
  - List all active API keys (masked for security)
  - Add existing API keys to Google Secret Manager
  - Remove API keys from Secret Manager
  - Full integration with `gcloud` CLI for Secret Manager operations
  - Supports multiple authentication methods and key formats

- **Admin Endpoint Authentication** (`frontend/lib/auth.ts`)
  - `verifyAdminAuth()` function for optional admin authentication
  - Supports Bearer token, custom header, or query parameter authentication
  - Only enforced when `ADMIN_API_KEY` environment variable is set (backward compatible)
  - Added to all batch indexing endpoints (`/api/batchIndexImages`, `/api/batchIndexSVG`, `/api/batchIndexText`)

- **API Key Rotation Documentation** (`docs/API_KEY_ROTATION.md`)
  - Comprehensive guide for rotating API keys
  - Step-by-step rotation process with zero-downtime procedures
  - Emergency rotation procedures for compromised keys
  - Best practices and security recommendations
  - Troubleshooting guide for common issues

- **Verification and Testing**
  - `scripts/verify-phase4.sh` - Automated verification script (25 checks)
  - `test_phase4_api_keys.py` - Python test suite for API key authentication
  - Comprehensive verification of all Phase 4 requirements

- **Documentation**
  - `docs/PHASE4_API_KEY_IMPLEMENTATION.md` - Implementation summary and architecture
  - `docs/PHASE4_VERIFICATION_CHECKLIST.md` - Detailed verification checklist with testing procedures
  - `docs/PHASE4_QUICK_TEST.md` - Quick reference guide for fast verification

### Changed
- **Python API** (`embed.py`)
  - Added startup block to allow running directly with `python embed.py`
  - Prints startup information including API key count, Elasticsearch status, and service URLs
  - Improved user experience when starting the server locally

- **Frontend Admin Endpoints** (`frontend/pages/api/batchIndex*.ts`)
  - Added optional authentication to all batch indexing endpoints
  - Admin endpoints now support multiple authentication methods
  - Backward compatible - only enforced when `ADMIN_API_KEY` is configured

### Security
- API key authentication already implemented (from Phase 1/2)
- Admin endpoints can now be protected with separate authentication
- API keys stored securely in Google Secret Manager
- Strong key generation (32+ character random keys)
- Health endpoint correctly excluded from authentication

### Notes
- API key authentication was already implemented in previous phases
- Phase 4 focused on management tools, admin endpoint protection, and documentation
- All authentication is backward compatible - works without keys for development
- Admin authentication is optional and only enforced when configured

## [2025-11-12] - Phase 3: HTTPS/SSL Configuration

### Added
- **Security Headers Middleware** (`embed.py`)
  - `SecurityHeadersMiddleware` class for adding security headers to all responses
  - `X-Content-Type-Options: nosniff` header to prevent MIME type sniffing
  - `X-Frame-Options: DENY` header to prevent clickjacking attacks
  - `X-XSS-Protection: 1; mode=block` header for XSS protection
  - `Strict-Transport-Security` (HSTS) header conditionally added for HTTPS requests
  - `Content-Security-Policy: default-src 'self'` header for CSP protection
  - HTTPS detection via `PYTHON_API_BASE_URL`, request scheme, or `X-Forwarded-Proto` header

- **Cloud Run Deployment Configurations**
  - `cloud-run-python.yaml` - Production-ready Cloud Run service configuration for Python API
  - `cloud-run-frontend.yaml` - Production-ready Cloud Run service configuration for Next.js frontend
  - Includes health checks, resource limits, scaling configuration, and environment variables
  - Supports both public HTTPS URLs and internal Cloud Run URLs for optimal performance

- **HTTPS Setup Automation** (`scripts/setup-https.sh`)
  - Automated script for setting up GCP Cloud Load Balancer with HTTPS
  - Creates static IP address reservation
  - Provisions Google-managed SSL certificates
  - Sets up health checks, Network Endpoint Groups (NEGs), backend services, URL maps, and forwarding rules
  - Supports subdomain-based routing (frontend and API on separate subdomains)

- **Verification and Testing**
  - `scripts/verify-phase3.sh` - Automated verification script for Phase 3 implementation
  - `test_phase3_https.py` - Python test suite for security headers and HTTPS configuration
  - Comprehensive verification of all Phase 3 requirements

- **Documentation**
  - `docs/HTTPS_SETUP.md` - Complete guide for HTTPS/SSL configuration on GCP
  - `docs/PHASE3_HTTPS_IMPLEMENTATION.md` - Implementation summary and architecture details
  - `docs/PHASE3_VERIFICATION_CHECKLIST.md` - Detailed verification checklist with testing procedures
  - `docs/PHASE3_QUICK_TEST.md` - Quick reference guide for fast verification

### Changed
- **Python API** (`embed.py`)
  - Added security headers middleware before CORS middleware
  - Security headers are now automatically added to all API responses
  - HSTS header is conditionally added only when HTTPS is detected

- **Docker Compose** (`docker-compose.yml`)
  - Added HTTPS configuration comments explaining how to configure services behind reverse proxy/load balancer
  - Documents options for internal vs external service communication
  - Includes examples for configuring HTTPS URLs

- **Environment Variables Documentation** (`docs/ENVIRONMENT_VARIABLES.md`)
  - Added HTTPS configuration examples for production deployment
  - Documented `PYTHON_API_BASE_URL` usage for HTTPS
  - Added notes about internal vs public URL configuration

### Security
- All API responses now include security headers by default
- HSTS header ensures browsers enforce HTTPS connections
- CSP header helps prevent XSS attacks
- Security headers work correctly with GCP Load Balancer via `X-Forwarded-Proto` header

## [2025-11-12] - Docker Configuration and Environment Variable Standardization

### Added
- **Docker Configuration**
  - `Dockerfile.python` - Python embedding/search service container
  - `Dockerfile.frontend` - Next.js frontend container with multi-stage build
  - `Dockerfile.token-renderer` - Token renderer service container
  - `Dockerfile.mcp` - MCP server container for local Docker usage
  - `docker-compose.yml` - Local development orchestration with internal networking
  - `.dockerignore` files for optimized builds

- **Environment Variable Documentation** (`docs/ENVIRONMENT_VARIABLES.md`)
  - Comprehensive reference for all environment variables across services
  - Service-specific variable prefixes and usage examples
  - Environment-specific configuration examples (local, Docker, production)

- **Python API Enhancements** (`embed.py`)
  - Environment variable configuration: `PYTHON_API_HOST`, `PYTHON_API_PORT`, `PYTHON_API_BASE_URL`
  - CORS middleware with configurable origins via `CORS_ORIGINS`
  - API key authentication middleware (supports env vars and Google Secret Manager)
  - Health check endpoint (`/health`) for container health checks
  - Configurable Elasticsearch connection settings (`ELASTICSEARCH_TIMEOUT`, `ELASTICSEARCH_MAX_RETRIES`)
  - Support for `PORT` environment variable (Cloud Run compatibility)

- **Next.js Configuration** (`frontend/next.config.js`)
  - Standalone output mode for Docker deployment
  - Environment variable exposure configuration

### Changed
- **Python API** (`embed.py`)
  - All endpoints now require API key authentication when keys are configured
  - Health check endpoint excluded from authentication
  - Backward compatible: works without API keys if none are configured
  - Improved error handling with HTTPException for better error messages

- **Frontend API Routes** (`frontend/pages/api/*.ts`)
  - All routes now use `EMBEDDING_SERVICE_URL` environment variable instead of hardcoded URLs
  - Added `FRONTEND_API_KEY` support for authenticating with Python API
  - Improved TypeScript type safety for API responses
  - Added null checks for Elasticsearch client (build-time safety)

- **Frontend Elasticsearch Client** (`frontend/client/es.ts`)
  - Made client initialization conditional (null if env vars not set)
  - Prevents build-time errors when Elasticsearch is not configured

- **Token Renderer Service** (`token_renderer/server.js`)
  - Added `TOKEN_RENDERER_HOST`, `TOKEN_RENDERER_PORT`, `TOKEN_RENDERER_BASE_URL` environment variables
  - Server binds to configurable host/port for Docker compatibility

- **MCP Server Documentation** (`docs/MCP_SERVER.md`)
  - Added Docker usage section with build and run examples
  - Added Claude Desktop Docker configuration example
  - Added Docker Compose example for MCP server

- **MCP Server Configuration** (`mcp_server_config_example.json`)
  - Added Docker usage example configuration

- **Frontend Components** (`frontend/pages/icon/[iconName].tsx`, `frontend/utils/icon_renderer.ts`)
  - Fixed TypeScript type errors for EuiLink and EuiIcon components
  - Fixed regex compatibility issues for older TypeScript targets

### Technical Details
- **Docker Features**:
  - All containers run as non-root users for security
  - Health check endpoints configured for all services
  - Multi-stage builds for optimized image sizes
  - Token renderer service accessible only via internal Docker network
  - Support for Cloud Run `PORT` environment variable

- **Environment Variables**:
  - Python API: `PYTHON_API_HOST`, `PYTHON_API_PORT`, `CORS_ORIGINS`, `API_KEYS`, `API_KEYS_SECRET_NAME`
  - Frontend: `EMBEDDING_SERVICE_URL`, `NEXT_PUBLIC_EMBEDDING_SERVICE_URL`, `FRONTEND_API_KEY`
  - Token Renderer: `TOKEN_RENDERER_HOST`, `TOKEN_RENDERER_PORT`, `TOKEN_RENDERER_BASE_URL`
  - Elasticsearch: `ELASTICSEARCH_ENDPOINT`, `ELASTICSEARCH_API_KEY`, `ELASTICSEARCH_TIMEOUT`, `ELASTICSEARCH_MAX_RETRIES`

## [2025-11-12] - MCP Server and Frontend Enhancements

### Added
- **MCP Server** (`mcp_server.py`)
  - Model Context Protocol server for exposing EUI icon search capabilities to AI agents
  - Provides two tools: `search_by_svg` and `search_by_image`
  - Supports `icon_type` parameter to distinguish between icons and tokens
  - Supports `fields` parameter to specify which embedding fields to search
  - Defaults to `icon_svg_embedding` for SVG searches and `icon_image_embedding` for image searches
  - Automatically selects token fields when `icon_type` is set to "token"
  - Includes signal handling for graceful shutdown on Ctrl+C
  - Logs startup information and tool calls to stderr
  - Falls back to CLI mode when MCP SDK is not available

- **MCP Server Test Script** (`test_mcp_server.py`)
  - Standalone test script for verifying MCP server functionality
  - Supports testing SVG search with `--svg-file` or `--svg-string` arguments
  - Supports testing image search with `--image-file` argument
  - Supports `--icon-type` parameter to specify icon or token search
  - Supports field override flags: `--icon-image`, `--icon-svg`, `--token-image`, `--token-svg`
  - Provides test results summary with pass/fail status

- **MCP Server Documentation** (`docs/MCP_SERVER.md`)
  - Installation and configuration instructions
  - Tool descriptions and usage examples
  - Integration guide for Claude Desktop and other MCP clients
  - Testing guide with multiple methods
  - Troubleshooting section

- **MCP Server Configuration Example** (`mcp_server_config_example.json`)
  - Example configuration file for Claude Desktop integration

- **Frontend Component Refactoring**
  - Extracted main page content into `frontend/components/mainPage/content.tsx`
  - Added `frontend/pages/_app.tsx` with EuiProvider wrapper for EUI context
  - Replaced EuiFlexGrid with EuiBasicTable for search results display
  - Added field selection UI with checkbox group for choosing embedding fields
  - Added conditional column rendering based on selected embedding fields
  - Added SVG rendering display when SVG code is pasted

### Changed
- **Dependencies** (`requirements.txt`)
  - Added `mcp>=0.9.0` dependency for MCP server functionality

- **Documentation** (`README.md`)
  - Added MCP Server section with quick start instructions and link to detailed documentation

- **Search API Architecture** (`frontend/pages/api/search.ts`)
  - Converted from full search implementation to thin proxy
  - Now forwards requests to Python API at `/search` endpoint
  - Improved error handling to parse FastAPI error responses
  - Removed direct Elasticsearch client dependency
  - Removed embedding generation logic (now handled by Python API)

- **Frontend Search** (`frontend/components/mainPage/content.tsx`)
  - Added field selection checkbox group for choosing embedding fields to search
  - Replaced grid layout with EuiBasicTable for structured results display
  - Added separate Icon and Token columns that render conditionally based on selected fields
  - Added pagination support with configurable page sizes
  - Added SVG rendering display when SVG code is pasted
  - Results maintain Elasticsearch score-based ordering
  - Improved error handling to display actual error messages from API

- **Search Endpoint in Python API** (`embed.py`)
  - Added `/search` endpoint that handles text, image, and SVG search
  - Supports `icon_type` and `fields` parameters for field selection
  - Implements hybrid search (dense + sparse embeddings) for text queries
  - Supports multiple KNN queries for image/SVG searches across multiple fields
  - Uses HTTPException for proper error responses
  - Handles base64 image decoding and validation

- **Search Migration Documentation** (`docs/MOVE_SEARCH_TO_PYTHON_API.md`)
  - Implementation plan for moving search functionality to Python API
  - Testing considerations and migration steps

### Changed
- **MCP Server** (`mcp_server.py`)
  - Updated `SEARCH_API_URL` default to use Python API endpoint (`http://localhost:8000/search`)
  - Removed unused `USE_DIRECT_SEARCH` logic and Elasticsearch direct access code
  - Simplified configuration to use Python API exclusively

- **Test Scripts**
  - `test_svg_search.py`: Updated to use Python API endpoint
  - `test_image_search.py`: Updated to use Python API endpoint

- **Documentation** (`docs/MCP_SERVER.md`, `README.md`, `mcp_server_config_example.json`)
  - Updated all references to use Python API search endpoint
  - Removed references to Next.js API for search functionality
  - Updated environment variable examples

## [2025-11-11] - Token Rendering and Indexing Improvements

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
    - `POST /render-icon` - Render icon or token with componentType parameter
    - `POST /render-svg` - Return SVG/HTML content for icon or token
    - `POST /render-tokens` - Batch render tokens
  - Runs on port 3002 by default (configurable via `TOKEN_RENDERER_PORT`)
  - Playwright-based rendering with webpack-built frontend
  - Supports rendering both EuiIcon and EuiToken components

- **Elasticsearch Index Mapping Updates**
  - Added `filename` field (keyword) - Original SVG filename
  - Added `release_tag` field (keyword) - EUI version tag (e.g., "v109.0.0")
  - Added `icon_type` field (keyword) - "icon" or "token"
  - Added `token_type` field (keyword) - Token type for token icons (optional)
  - Added `svg_content` field (text, not indexed) - Full SVG content for reference
  - Replaced single `image_embedding` and `svg_embedding` with separate fields:
    - `icon_image_embedding` (dense_vector, 512 dims)
    - `token_image_embedding` (dense_vector, 512 dims)
    - `icon_svg_embedding` (dense_vector, 512 dims)
    - `token_svg_embedding` (dense_vector, 512 dims)
  - Added `token_svg_content` field (text, not indexed) - Token SVG/HTML content

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
  - `docs/REINDEXING_STRATEGY.md` - Plan for automated indexing strategy
  - `docs/TOKEN_INDEXING_PLAN.md` - Plan for indexing tokenized icon versions
  - `docs/FRONTEND_SEARCH.md` - Frontend search implementation plan

### Changed
- **Index Mapping** (`utils/es_index_setup.py`)
  - Changed `icon_type` values from "regular" to "icon"
  - Updated embedding fields to separate icon and token embeddings
  - Added version tracking and icon type fields

- **Indexing Script** (`scripts/index_eui_icons.py`)
  - Updated to generate all four embedding types (icon image, token image, icon SVG, token SVG) for each icon
  - Stores all embeddings in a single document instead of separate documents
  - Uses token renderer service for all image generation (removed SVG-to-PNG fallback)
  - Added option to save rendered images to disk with `--save-images` flag
  - Updated document structure to include all embedding fields

- **Search API Response** (`frontend/pages/api/search.ts`)
  - Returns `icon_name` from document source instead of document ID
  - Added `release_tag` and `icon_type` fields to response
  - Document IDs include version tag (e.g., "search_v109.0.0"), but `icon_name` field returns clean name (e.g., "search")

- **Test Scripts** (`test_svg_search.py`)
  - Updated `--icon-name` flag to use EUI repository mapping
  - Extracts `typeToPathMap` from EUI repository to convert icon names to filenames
  - Searches EUI repository recursively for SVG files

- Updated frontend to use icon name mapping instead of direct filename usage
- Improved search result display with icon names and scores

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

- **EUI Styling**
  - Added EuiProvider wrapper in `_app.tsx` to ensure EUI CSS classes (including `.euiScreenReaderOnly`) are properly applied

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

