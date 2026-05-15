# Implementation Plan - EUI Icon Embeddings

## Overview

This document details the step-by-step implementation plan for the EUI Icon Embeddings system. The plan was executed to create a multi-modal search system supporting text, image, and SVG-based icon search.

## Implementation Tasks

### Task 1: Elasticsearch Index Setup ✅

**Objective**: Create Elasticsearch index with proper mappings for all embedding types

**Implementation**:
- Created `utils/es_index_setup.py` script
- Defined index mapping with:
  - `icon_name` (keyword)
  - `descriptions` (text array)
  - `text_embedding` (dense_vector, 384 dims, cosine similarity)
  - `text_embedding_sparse` (sparse_vector for ELSER)
  - `image_embedding` (dense_vector, 384 dims, cosine similarity)
  - `svg_embedding` (dense_vector, 384 dims, cosine similarity)
- Configured knn settings for efficient vector search
- Added ELSER model deployment check

**Files Created**:
- `utils/es_index_setup.py`

**Usage**:
```bash
python utils/es_index_setup.py
```

---

### Task 2: Text Embeddings Enhancement ✅

**Objective**: Add ELSER sparse embeddings alongside existing dense embeddings

**Implementation**:
- Enhanced `embed.py` to generate both dense and sparse embeddings
- Added Elasticsearch client initialization for ELSER inference
- Updated `/embed` endpoint to return both embedding types
- Modified `frontend/pages/api/saveIcon.ts` to store both embedding types
- Updated document structure to include `text_embedding` and `text_embedding_sparse` fields

**Files Modified**:
- `embed.py` - Added ELSER inference support
- `frontend/pages/api/saveIcon.ts` - Updated to handle sparse embeddings

**Key Changes**:
- Dense embeddings: Continue using `all-MiniLM-L6-v2`
- Sparse embeddings: Use Elasticsearch ELSER inference API
- Both embeddings stored in same document for hybrid search

---

### Task 3: Icon Rendering Utility ✅

**Objective**: Create utility to render EuiIcon components to standardized images

**Implementation**:
- Created `frontend/utils/icon_renderer.ts` (TypeScript version)
- Created `utils/icon_renderer.js` (Node.js version)
- Functions:
  - `renderIconToSVG()` - Render EuiIcon to SVG string
  - `normalizeSVG()` - Normalize SVG size and format
  - `saveSVG()` - Save SVG to file
  - `renderIconToImage()` - Render icon to image file

**Files Created**:
- `frontend/utils/icon_renderer.ts`
- `utils/icon_renderer.js`

**Key Features**:
- Server-side React rendering using `renderToStaticMarkup`
- SVG normalization (standardize viewBox, size)
- Support for different icon sizes

---

### Task 4: Image Embedding Pipeline ✅

**Objective**: Implement image embedding pipeline using CLIP model

**Implementation**:
- Added CLIP model (`clip-ViT-B-32`) to `embed.py`
- Created `image_processor.py` for image normalization
- Added `/embed-image` endpoint to FastAPI service
- Image normalization:
  - Convert to RGB
  - Resize to 224x224 (CLIP input size)
  - Maintain aspect ratio with center crop

**Files Created**:
- `image_processor.py`

**Files Modified**:
- `embed.py` - Added image embedding endpoint

**Key Features**:
- Standardized image size (224x224) for CLIP model
- Automatic format conversion (RGB)
- 384-dimension embeddings

---

### Task 5: SVG Normalization Utility ✅

**Objective**: Create SVG normalization utility to standardize size and format

**Implementation**:
- Created `svg_processor.py` with normalization functions
- Functions:
  - `normalize_svg()` - Standardize SVG size, viewBox, format
  - `svg_to_image()` - Convert SVG to PIL Image
  - `extract_svg_layers()` - Extract individual SVG elements

**Files Created**:
- `svg_processor.py`

**Key Features**:
- ViewBox extraction and normalization
- Size standardization (224x224)
- SVG to image conversion using cairosvg
- Layer extraction for future use

---

### Task 6: SVG Embedding Pipeline ✅

**Objective**: Implement SVG embedding pipeline (normalize → convert to image → embed)

**Implementation**:
- Added `/embed-svg` endpoint to `embed.py`
- SVG processing flow:
  1. Normalize SVG (size, format)
  2. Convert SVG to PNG using cairosvg
  3. Load PNG as PIL Image
  4. Generate embeddings using CLIP model
- Same embedding model as images (CLIP)

**Files Modified**:
- `embed.py` - Added SVG embedding endpoint

**Key Features**:
- SVG normalization before conversion
- Consistent 224x224 output size
- Reuses image embedding pipeline

---

### Task 7: Unified Search API ✅

**Objective**: Create unified search endpoint accepting text, image, or SVG

**Implementation**:
- Created `frontend/pages/api/search.ts`
- Supports three search types:
  - `text` - Hybrid search (dense + sparse)
  - `image` - Dense vector search on image embeddings
  - `svg` - Dense vector search on SVG embeddings
- Query routing based on type
- Embedding generation via FastAPI service
- Elasticsearch search execution

**Files Created**:
- `frontend/pages/api/search.ts`

**Key Features**:
- Single endpoint for all search types
- Automatic embedding generation
- Hybrid search for text (dense + sparse)
- Returns ranked results with scores

**API Usage**:
```json
POST /api/search
{
  "type": "text|image|svg",
  "query": "search query, base64 image, or SVG code"
}
```

---

### Task 8: Batch Text Indexing ✅

**Objective**: Create endpoint for bulk text description indexing

**Implementation**:
- Created `frontend/pages/api/batchIndexText.ts`
- Accepts array of `{iconName, description}` pairs
- Batch processing with configurable batch size (10)
- Error handling and progress tracking
- Upsert behavior (updates existing, creates new)

**Files Created**:
- `frontend/pages/api/batchIndexText.ts`

**Key Features**:
- Processes multiple icons efficiently
- Rate limiting between batches
- Detailed error reporting
- Merges descriptions for existing icons

**API Usage**:
```json
POST /api/batchIndexText
{
  "items": [
    { "iconName": "user", "description": "user icon" },
    { "iconName": "home", "description": "home icon" }
  ]
}
```

---

### Task 9: Batch Image Indexing ✅

**Objective**: Create endpoint for bulk image generation and embedding

**Implementation**:
- Created `frontend/pages/api/batchIndexImages.ts`
- Accepts array of icon names
- Renders icons to SVG, then converts to image
- Generates embeddings via `/embed-svg` endpoint
- Stores `image_embedding` in Elasticsearch
- Smaller batch size (5) for image processing

**Files Created**:
- `frontend/pages/api/batchIndexImages.ts`

**Key Features**:
- Automatic icon rendering
- SVG to image conversion
- Batch processing with delays
- Error handling per icon

**API Usage**:
```json
POST /api/batchIndexImages
{
  "iconNames": ["user", "home", "settings"]
}
```

---

### Task 10: Batch SVG Indexing ✅

**Objective**: Create endpoint for bulk SVG extraction, normalization, and embedding

**Implementation**:
- Created `frontend/pages/api/batchIndexSVG.ts`
- Accepts array of icon names
- Renders icons to SVG
- Normalizes SVG (size, format)
- Generates embeddings via `/embed-svg` endpoint
- Stores `svg_embedding` in Elasticsearch

**Files Created**:
- `frontend/pages/api/batchIndexSVG.ts`

**Key Features**:
- SVG extraction from EuiIcon components
- Normalization before embedding
- Batch processing with error handling
- Stores normalized SVG embeddings

**API Usage**:
```json
POST /api/batchIndexSVG
{
  "iconNames": ["user", "home", "settings"]
}
```

---

## Additional Files Created

### Requirements File
- `requirements.txt` - All Python dependencies with versions

### Documentation
- `README.md` - Setup and usage instructions
- `docs/PROJECT_PLAN.md` - High-level project plan
- `docs/IMPLEMENTATION_PLAN.md` - This file

### Testing
- `test_elasticsearch_setup.py` - Comprehensive ES validation test suite

## Implementation Notes

### Model Loading
- Text model (`all-MiniLM-L6-v2`) loaded at startup
- Image model (`clip-ViT-B-32`) loaded at startup
- ELSER model accessed via Elasticsearch inference API (not loaded locally)

### Error Handling
- All endpoints include try-catch blocks
- Detailed error messages returned to client
- Batch endpoints continue processing on individual failures

### Performance Considerations
- Batch processing with configurable batch sizes
- Rate limiting between batches
- Parallel processing within batches using `Promise.all()`
- Efficient vector search using Elasticsearch knn

### Search Strategy
- **Text**: Hybrid search combining dense (knn) and sparse (text_expansion)
- **Image/SVG**: Pure knn search on dense vectors
- Results ranked by similarity score

## Testing

Run the Elasticsearch validation test:
```bash
python test_elasticsearch_setup.py
```

This validates:
- Connection and authentication
- Index existence and mapping
- Dense vector field support
- ELSER sparse embedding support
- Search functionality (knn, text_expansion, hybrid)

## Next Steps

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   cd frontend && npm install
   ```

2. **Set Environment Variables**
   ```env
   ELASTICSEARCH_ENDPOINT=https://your-cluster.es.amazonaws.com
   ELASTICSEARCH_API_KEY=your-api-key
   ```

3. **Setup Elasticsearch Index**
   ```bash
   python utils/es_index_setup.py
   ```

4. **Deploy ELSER Model** (Optional)
   ```bash
   PUT _ml/trained_models/.elser_model_2/_deploy
   ```

5. **Start Services**
   ```bash
   # Terminal 1: Embedding service
   uvicorn embed:app --reload --port 8000
   
   # Terminal 2: Frontend
   cd frontend && npm run dev
   ```

6. **Index Icons**
   - Use batch endpoints to index hundreds of icons
   - Start with text descriptions
   - Then index images and SVG

7. **Test Search**
   - Test text search with various queries
   - Test image search with uploaded images
   - Test SVG search with SVG code

## Status

All implementation tasks have been completed. The system is ready for:
- Indexing hundreds of EUI icons
- Multi-modal search (text, image, SVG)
- Batch processing operations
- Production deployment

