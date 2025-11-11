# Changelog

All notable changes to the EUI Icon Embeddings project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Project Status

This project provides a production-ready, multi-modal search system for Elastic UI (EUI) icons, supporting semantic text search, visual image matching, and SVG code similarity search. The system features automated indexing, version tracking, and comprehensive API support for seamless integration.

## [Unreleased]

### Added
- **Automated EUI Icon Indexing System** (`scripts/index_eui_icons.py`)
  - **Production-ready automation**: Fully automated repository cloning, version detection, and icon indexing
  - **Intelligent version management**: Automatically detects latest EUI major releases and tracks processed versions
  - **Smart incremental indexing**: Only processes new versions or missing icons, skipping fully indexed versions
  - **Comprehensive icon mapping**: Automatically extracts and uses `typeToPathMap` from EUI repository for accurate icon name resolution
  - **Recursive SVG discovery**: Searches entire repository structure to find all SVG files, not limited to specific paths
  - **Dual indexing support**: Indexes both regular icons and tokenized versions in a single pass
  - **Robust error handling**: Continues processing even when individual icons fail, with comprehensive error reporting
  - **Version-aware document structure**: Uses `{icon_name}_{release_tag}` format for unique document IDs while preserving clean icon names

- **Token Renderer Microservice** (`token_renderer/`)
  - **Standalone service architecture**: Decoupled Node.js microservice for token rendering, enabling independent scaling
  - **RESTful API design**: Clean REST endpoints for single and batch token rendering
  - **Production-ready**: Health checks, error handling, and comprehensive documentation
  - **Flexible deployment**: Configurable port and environment variables for easy integration

- **Enhanced Elasticsearch Index Mapping**
  - **Version tracking fields**: Added `release_tag`, `icon_type`, `token_type`, and `filename` for comprehensive metadata
  - **Future-proof design**: Supports multiple EUI versions in a single index with proper filtering capabilities
  - **Complete document structure**: Includes `svg_content` for reference while keeping embeddings searchable

- **Comprehensive Documentation**
  - **Strategic planning documents**: Detailed plans for reindexing, token indexing, and image normalization
  - **Implementation guides**: Step-by-step documentation for all major features
  - **Troubleshooting resources**: Known issues, fixes, and setup guides

### Changed
- **Index Mapping Architecture** (`utils/es_index_setup.py`)
  - **Semantic field naming**: Changed `icon_type` from "regular" to "icon" for clarity
  - **Corrected dimensions**: Updated `svg_embedding` to 512 dimensions to match CLIP model output
  - **Enhanced metadata**: Added version tracking and icon type fields for better search filtering

- **Frontend Search Experience** (`frontend/pages/index.tsx`)
  - **Intuitive image search**: Paste images directly (Ctrl/Cmd+V) or upload files
  - **Real-time SVG search**: Paste SVG code with automatic debounced search
  - **Visual feedback**: Image preview, loading states, and similarity scores
  - **Improved UX**: Better result display with icon names and scores

- **Search API Response Format** (`frontend/pages/api/search.ts`)
  - **Clean icon names**: Returns actual icon names (e.g., "search") instead of document IDs (e.g., "search_v109.0.0")
  - **Enhanced metadata**: Includes `release_tag` and `icon_type` for advanced filtering
  - **Backward compatible**: Maintains existing response structure while adding new fields

- **Test Scripts** (`test_svg_search.py`)
  - **EUI repository integration**: Uses same mapping logic as indexing script for consistency
  - **Automatic icon resolution**: Converts icon names to filenames using `typeToPathMap`
  - **Repository-aware**: Searches EUI repository directly instead of relying on `.svgpaths` file

### Fixed
- **Critical Search API Bug**
  - **Fixed icon name resolution**: Search API now returns correct icon names from document source instead of document IDs
  - **Proper version handling**: Users receive clean icon names while version information is available for filtering

- **SVG Rendering Pipeline**
  - **Fixed all-black SVG issue**: Added preprocessing to ensure proper fill attributes and white backgrounds
  - **Dimension consistency**: Corrected embedding dimensions to match CLIP model output (512 dimensions)

- **Image Search Accuracy**
  - **Field mapping fix**: Corrected search to use `svg_embedding` field for image searches
  - **Normalization improvements**: Automatic background detection and inversion for better search accuracy
  - **Cross-mode compatibility**: Works with both light and dark mode screenshots

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

## [2025-11-10] - Image Normalization & Advanced Planning

### Added
- **Intelligent Image Normalization** (`image_processor.py`)
  - **Automatic background detection**: Detects light/dark backgrounds and adjusts accordingly
  - **Smart inversion logic**: Automatically inverts dark backgrounds to ensure consistency
  - **Advanced preprocessing**: Grayscale conversion, contrast normalization, and size standardization
  - **Cross-mode compatibility**: Ensures search images match indexed SVG embeddings regardless of source mode

- **Comprehensive Testing Tools**
  - `test_image_normalization.py` - Visual comparison tool for normalized images
  - `test_svg_normalization.py` - SVG preprocessing validation tool
  - Both tools provide detailed analysis and side-by-side comparisons

- **Strategic Planning Documentation**
  - `docs/IMAGE_NORMALIZATION_PLAN.md` - Comprehensive image normalization strategy
  - `docs/TOKEN_INDEXING_PLAN.md` - Detailed token indexing implementation plan

### Changed
- **Enhanced Embedding Service** (`embed.py`)
  - Integrated `normalize_search_image()` into `/embed-image` endpoint
  - Significantly improved search accuracy for real-world screenshots

### Fixed
- **Real-world screenshot compatibility**: Fixed issue where screenshots from different backgrounds didn't match indexed embeddings
- **Cross-mode search accuracy**: Improved search results for both light and dark mode screenshots

## [2025-11-10] - Initial Project Setup & Foundation

### Added
- **Production-Grade Core Infrastructure**
  - **FastAPI Embedding Service** (`embed.py`): High-performance embedding generation
    - Text embeddings using `all-MiniLM-L6-v2` (384 dimensions)
    - ELSER sparse embeddings via Elasticsearch inference API
    - Image embeddings using CLIP (`clip-ViT-B-32`, 512 dimensions)
    - SVG embeddings via SVG-to-image conversion using CLIP
  - **Next.js Frontend**: Modern React-based UI with comprehensive API routes
  - **Elasticsearch Integration**: Full vector search support with KNN and hybrid search

- **Robust Elasticsearch Setup** (`utils/es_index_setup.py`)
  - **Comprehensive index mapping**: Support for dense vectors (384 and 512 dimensions) and sparse vectors (ELSER)
  - **Optimized search configuration**: KNN search settings for efficient vector similarity search
  - **Model validation**: Automatic ELSER model deployment checking

- **Efficient Batch Processing** (`batch_embed_svgs.py`)
  - **Scalable processing**: Handles hundreds of icons efficiently
  - **Flexible input**: Reads SVG paths from `.svgpaths` file
  - **Smart skipping**: Automatically skips already-indexed files
  - **Testing support**: `--limit` flag for incremental testing

- **Comprehensive API Endpoints** (`frontend/pages/api/`)
  - **Unified search API**: Single endpoint for text, image, and SVG search
  - **Batch indexing APIs**: Efficient bulk processing for all embedding types
  - **Management APIs**: Icon listing and individual icon indexing

- **Icon Rendering System**
  - **React-based rendering**: Server-side icon rendering for frontend
  - **Node.js utilities**: Standalone icon rendering for batch processing
  - **SVG normalization**: Consistent size and format standardization

- **Extensive Testing & Diagnostics Suite**
  - **Elasticsearch validation**: Comprehensive setup and functionality testing
  - **Search testing**: Dedicated scripts for SVG and image search
  - **Diagnostic tools**: Embedding analysis, duplicate detection, similarity checking
  - **Index management**: Document counting and health checking

- **Image & SVG Processing**
  - **Image normalization**: Standardization utilities for consistent embeddings
  - **SVG processing**: ViewBox extraction and normalization
  - **Format conversion**: Seamless conversion between formats

- **Comprehensive Documentation**
  - **Project planning**: High-level architecture and implementation plans
  - **Setup guides**: Detailed instructions for all components
  - **Troubleshooting**: Common issues, fixes, and best practices
  - **Known issues**: Documented problems and solutions

- **Production Configuration**
  - **Environment management**: Comprehensive `.gitignore` and environment variable support
  - **Dependency management**: Clear Python and Node.js dependency specifications
  - **Path management**: Flexible SVG path configuration

### Features
- **Multi-Modal Search Capabilities**
  - **Text search**: Semantic search with hybrid dense/sparse embeddings
  - **Image search**: Visual similarity search using CLIP embeddings
  - **SVG search**: Structural similarity search via normalized SVG embeddings

- **Advanced Search Features**
  - **Hybrid search**: Combines dense vector search (KNN) with sparse vector search (ELSER) for optimal relevance
  - **Cross-modal compatibility**: Image and SVG searches use compatible embeddings

- **Enterprise-Grade Batch Processing**
  - **Efficient bulk operations**: Process hundreds of icons with progress tracking
  - **Resume capability**: Automatically skips already-processed files
  - **Error resilience**: Continues processing even when individual items fail

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

