# EUI Icon Embeddings System

A multi-modal search system for EUI icons supporting text descriptions, image matching, and SVG code search using dense vector embeddings and Elasticsearch.

## Features

- **Text Search**: Semantic search using dense embeddings (all-MiniLM-L6-v2) and sparse embeddings (ELSER)
- **Image Search**: Visual similarity search using CLIP embeddings
- **SVG Search**: Search by SVG code using normalized SVG-to-image embeddings
- **Batch Indexing**: Efficient bulk processing of hundreds of icons

## Setup

### 1. Install Python Dependencies

**Important**: You must use a virtual environment. The project already has a `venv/` directory.

```bash
# Activate the existing virtual environment
source venv/bin/activate

# Then install dependencies
pip install -r requirements.txt
```

**If you don't have a virtual environment yet:**
```bash
# Create a new virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**Note**: Always activate the virtual environment before running Python commands:
```bash
source venv/bin/activate
```

### 2. Install Node.js Dependencies

```bash
cd frontend
npm install
```

### 3. Set Environment Variables

Create a `.env` file in the project root:

```env
ELASTICSEARCH_ENDPOINT=https://your-cluster.es.amazonaws.com
ELASTICSEARCH_API_KEY=your-api-key
```

### 4. Setup Elasticsearch Index

Run the index setup script:

```bash
python utils/es_index_setup.py
```

This creates the `icons` index with proper mappings for:
- `text_embedding` (dense_vector, 384 dims)
- `text_embedding_sparse` (sparse_vector for ELSER)
- `image_embedding` (dense_vector, 512 dims)
- `svg_embedding` (dense_vector, 512 dims)

### 5. Deploy ELSER Model (Optional)

For sparse embeddings, deploy the ELSER model in Elasticsearch:

```bash
PUT _ml/trained_models/.elser_model_2/_deploy
```

### 6. Start the Embedding Service

```bash
uvicorn embed:app --reload --port 8000
```

### 7. Start the Frontend

```bash
cd frontend
npm run dev
```

## Usage

### Search API

**POST** `/api/search`

Search for icons by text, image, or SVG:

```json
{
  "type": "text",
  "query": "user icon with circle"
}
```

```json
{
  "type": "image",
  "query": "base64-encoded-image-data"
}
```

```json
{
  "type": "svg",
  "query": "<svg>...</svg>"
}
```

### Batch Indexing

**POST** `/api/batchIndexText`

Index text descriptions for multiple icons:

```json
{
  "items": [
    { "iconName": "user", "description": "user icon" },
    { "iconName": "home", "description": "home icon" }
  ]
}
```

**POST** `/api/batchIndexImages`

Generate and index image embeddings for multiple icons:

```json
{
  "iconNames": ["user", "home", "settings"]
}
```

**POST** `/api/batchIndexSVG`

Extract, normalize, and index SVG embeddings for multiple icons:

```json
{
  "iconNames": ["user", "home", "settings"]
}
```

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
- Search functionality

## Architecture

- **FastAPI Service** (`embed.py`): Handles embedding generation for text, images, and SVG
- **Next.js Frontend**: Provides API endpoints for search and batch indexing
- **Elasticsearch**: Stores embeddings and performs vector search
- **CLIP Model**: Generates 384-dim embeddings for images and SVG
- **ELSER**: Provides sparse embeddings for enhanced text search

## Documentation

- **[PROJECT_PLAN.md](docs/PROJECT_PLAN.md)** - High-level project plan and architecture
- **[IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md)** - Detailed implementation plan and task breakdown

## File Structure

```
eui-embeddings/
├── embed.py                    # FastAPI embedding service
├── image_processor.py          # Image normalization utilities
├── svg_processor.py            # SVG normalization utilities
├── docs/
│   ├── PROJECT_PLAN.md         # High-level project plan
│   └── IMPLEMENTATION_PLAN.md  # Detailed implementation plan
├── utils/
│   ├── es_index_setup.py       # Elasticsearch index setup
│   └── icon_renderer.js        # Icon rendering utilities (Node.js)
├── frontend/
│   ├── pages/api/
│   │   ├── search.ts           # Unified search API
│   │   ├── batchIndexText.ts  # Batch text indexing
│   │   ├── batchIndexImages.ts # Batch image indexing
│   │   ├── batchIndexSVG.ts    # Batch SVG indexing
│   │   └── saveIcon.ts         # Single icon indexing
│   └── utils/
│       └── icon_renderer.ts    # Icon rendering utilities (TypeScript)
└── requirements.txt            # Python dependencies
```

