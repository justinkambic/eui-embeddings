# EUI Icon Embeddings Project Plan

## Project Overview

This project implements a comprehensive multi-modal search system for EUI (Elastic UI) icons. The system supports three search modalities:

1. **Semantic search for human descriptions** - Text-based search using dense and sparse embeddings
2. **Dense vectors for images** - Visual similarity search using image embeddings
3. **Dense vectors for SVG code** - Search by SVG structure and content

## Goals

### Goal 1: Text-Based Semantic Search
- Generate human-readable descriptions for each EUI icon
- Create dense embeddings using `all-MiniLM-L6-v2` (384 dimensions)
- Create sparse embeddings using Elasticsearch ELSER model
- Index both embedding types to Elasticsearch
- Support semantic search queries

### Goal 2: Image-Based Search
- Generate standardized images (PNG) for each EUI icon
- Normalize images (resize, center, format standardization)
- Create embeddings using CLIP model (`clip-ViT-B-32`, 384 dimensions)
- Index image embeddings to Elasticsearch
- Accept user-uploaded images and find matching icons

### Goal 3: SVG-Based Search
- Normalize SVG code (standardize size, extract layers)
- Render SVG layers to images
- Create embeddings using CLIP model (same as images)
- Index SVG embeddings to Elasticsearch
- Accept SVG code from users and find matching icons

## Technical Architecture

### Embedding Models
- **Text (Dense)**: `all-MiniLM-L6-v2` - 384 dimensions
- **Text (Sparse)**: Elasticsearch ELSER (`.elser_model_2`)
- **Image/SVG**: `sentence-transformers/clip-ViT-B-32` - 512 dimensions

### Elasticsearch Index Structure
```
Index: "icons"
Fields:
  - icon_name (keyword)
  - descriptions (text array)
  - text_embedding (dense_vector, 384 dims, cosine similarity)
  - text_embedding_sparse (sparse_vector for ELSER)
  - image_embedding (dense_vector, 512 dims, cosine similarity)
  - svg_embedding (dense_vector, 512 dims, cosine similarity)
```

### API Endpoints

#### Embedding Service (FastAPI - Port 8000)
- `POST /embed` - Generate text embeddings (dense + sparse)
- `POST /embed-image` - Generate image embeddings
- `POST /embed-svg` - Generate SVG embeddings

#### Frontend API (Next.js)
- `POST /api/search` - Unified search (text/image/SVG)
- `POST /api/batchIndexText` - Bulk text indexing
- `POST /api/batchIndexImages` - Bulk image indexing
- `POST /api/batchIndexSVG` - Bulk SVG indexing
- `POST /api/saveIcon` - Single icon text indexing (existing)

## Implementation Tasks

### Phase 1: Infrastructure Setup
1. ✅ Create Elasticsearch index with proper mappings
2. ✅ Set up embedding service with multiple models
3. ✅ Configure ELSER model deployment

### Phase 2: Text Embeddings
1. ✅ Enhance text embedding pipeline with ELSER support
2. ✅ Update saveIcon API to store both dense and sparse embeddings
3. ✅ Create batch text indexing endpoint

### Phase 3: Image Processing
1. ✅ Create icon rendering utility (EuiIcon → SVG → Image)
2. ✅ Implement image normalization pipeline
3. ✅ Add CLIP model for image embeddings
4. ✅ Create batch image indexing endpoint

### Phase 4: SVG Processing
1. ✅ Create SVG normalization utility
2. ✅ Implement SVG-to-image conversion
3. ✅ Add SVG embedding pipeline
4. ✅ Create batch SVG indexing endpoint

### Phase 5: Search API
1. ✅ Create unified search endpoint
2. ✅ Implement hybrid search (dense + sparse for text)
3. ✅ Support image and SVG search queries

## File Structure

```
eui-embeddings/
├── embed.py                          # FastAPI embedding service
├── image_processor.py                # Image normalization utilities
├── svg_processor.py                 # SVG normalization utilities
├── requirements.txt                  # Python dependencies
├── test_elasticsearch_setup.py      # ES validation tests
├── utils/
│   ├── es_index_setup.py            # Elasticsearch index setup script
│   └── icon_renderer.js             # Icon rendering (Node.js)
├── frontend/
│   ├── pages/api/
│   │   ├── search.ts                # Unified search API
│   │   ├── batchIndexText.ts        # Batch text indexing
│   │   ├── batchIndexImages.ts      # Batch image indexing
│   │   ├── batchIndexSVG.ts         # Batch SVG indexing
│   │   └── saveIcon.ts              # Single icon indexing
│   ├── utils/
│   │   └── icon_renderer.ts         # Icon rendering (TypeScript)
│   └── client/
│       └── es.ts                    # Elasticsearch client
└── docs/
    └── PROJECT_PLAN.md              # This file
```

## Dependencies

### Python
- fastapi >= 0.104.0
- uvicorn >= 0.24.0
- sentence-transformers >= 2.2.0
- torch >= 2.0.0
- transformers >= 4.30.0
- Pillow >= 10.0.0
- cairosvg >= 2.7.0
- numpy >= 1.24.0
- elasticsearch >= 8.0.0
- pydantic >= 2.0.0
- python-multipart >= 0.0.6

### Node.js
- @elastic/elasticsearch >= 9.1.1
- @elastic/eui >= 106.4.0
- next >= 15.5.2
- react >= 18.0.0
- react-dom >= 18.0.0
- node-fetch >= 3.3.2
- form-data >= 4.0.0

## Search Strategies

### Text Search (Hybrid)
- Combines dense vector search (knn) with sparse vector search (text_expansion)
- Dense embeddings capture semantic meaning
- Sparse embeddings (ELSER) capture keyword relevance
- Results are combined for optimal relevance

### Image Search
- User uploads image → normalized to 224x224 RGB
- CLIP model generates 384-dim embedding
- knn search against `image_embedding` field
- Returns top-k most similar icons

### SVG Search
- User provides SVG code → normalized (size, format)
- SVG converted to image (224x224) via cairosvg
- CLIP model generates 384-dim embedding
- knn search against `svg_embedding` field
- Returns top-k most similar icons

## Batch Processing

All batch endpoints support:
- Processing hundreds of icons efficiently
- Progress tracking and error reporting
- Rate limiting to avoid overwhelming services
- Upsert behavior (updates existing, creates new)

## Future Enhancements

- [ ] Add caching layer for frequently searched queries
- [ ] Implement result ranking improvements
- [ ] Add support for icon metadata (categories, tags)
- [ ] Create admin UI for managing indexed icons
- [ ] Add analytics and search performance metrics
- [ ] Support for icon variants and sizes
- [ ] Multi-language description support

