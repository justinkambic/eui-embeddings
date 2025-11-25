# Known Issues and Fixes

## Issue 1: ELSER Inference Field Name

**Problem**: ELSER inference API may fail with "field not found" error.

**Root Cause**: The field name in the inference request may be incorrect. ELSER models typically expect `"text"` not `"text_field"`.

**Fix**: Update `embed.py` line 51:

```python
# Current (may be incorrect):
inference_response = es_client.ml.infer_trained_model(
    model_id=".elser_model_2",
    body={
        "docs": [{"text_field": request.content}]
    }
)

# Fixed:
inference_response = es_client.ml.infer_trained_model(
    model_id=".elser_model_2",
    body={
        "docs": [{"text": request.content}]  # Changed from "text_field" to "text"
    }
)
```

**Alternative**: If your ELSER model uses a different field name, check your model configuration:
```bash
GET _ml/trained_models/.elser_model_2
```

---

## Issue 2: FormData in Next.js API Routes

**Problem**: `FormData` may not work correctly in Next.js API routes when sending files.

**Root Cause**: Node.js `FormData` from `form-data` package works differently than browser `FormData`.

**Fix**: Update `frontend/pages/api/search.ts` for image uploads:

```typescript
// Option A: Use multipart/form-data manually
import FormData from "form-data";

// When sending image:
const formData = new FormData();
formData.append("file", imageBuffer, {
  filename: "image.png",
  contentType: "image/png",
});

const embedRes = await fetch("http://localhost:8000/embed-image", {
  method: "POST",
  headers: formData.getHeaders(), // Important: get headers from FormData
  body: formData,
});

// Option B: Send base64 directly (simpler)
// In search.ts, change image handling:
const embedRes = await fetch("http://localhost:8000/embed-image", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ image: query }), // Send base64 as JSON
});

// Then update embed.py to accept JSON:
@app.post("/embed-image", response_model=ImageEmbedResponse)
async def embed_image(request: dict):
    import base64
    image_data = base64.b64decode(request["image"])
    image = Image.open(io.BytesIO(image_data))
    # ... rest of the code
```

**Recommended**: Use Option B (base64 JSON) as it's simpler and more reliable.

---

## Issue 3: Elasticsearch Hybrid Search Query

**Problem**: Hybrid search (dense + sparse) may not work correctly or return errors.

**Root Cause**: The query structure may need adjustment for your Elasticsearch version.

**Fix**: Update `frontend/pages/api/search.ts`:

```typescript
// For Elasticsearch 8.x, ensure proper query structure:
if (type === "text" && sparseEmbeddings) {
  // Option A: Use separate queries (recommended)
  searchBody.query = {
    bool: {
      should: [
        {
          text_expansion: {
            text_embedding_sparse: {
              model_text: query,
              model_id: ".elser_model_2",
            },
          },
        },
      ],
    },
  };
  searchBody.knn = {
    field: embeddingField,
    query_vector: embeddings,
    k: 10,
    num_candidates: 100,
  };
  
  // Option B: If Option A doesn't work, try combining with boost
  searchBody.query = {
    bool: {
      should: [
        {
          text_expansion: {
            text_embedding_sparse: {
              model_text: query,
              model_id: ".elser_model_2",
            },
          },
          boost: 0.5, // Adjust boost as needed
        },
      ],
    },
  };
}
```

**Note**: If ELSER is not available, the code will fall back to pure knn search (this is expected).

---

## Issue 4: cairosvg System Dependencies

**Problem**: `cairosvg` fails to import or convert SVG.

**Root Cause**: `cairosvg` requires system libraries (Cairo, Pango, etc.).

**Fix**: Install system dependencies:

**macOS**:
```bash
brew install cairo pango gdk-pixbuf libffi
pip install cairosvg
```

**Linux (Ubuntu/Debian)**:
```bash
sudo apt-get install libcairo2-dev libpango1.0-dev libgdk-pixbuf2.0-dev libffi-dev
pip install cairosvg
```

**Alternative**: If system dependencies are problematic, use an alternative approach:

```python
# In embed.py, replace cairosvg with svglib:
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
import io

# Convert SVG to PNG:
drawing = svg2rlg(io.StringIO(request.svg_content))
png_data = renderPM.drawToString(drawing, fmt='PNG')
image = Image.open(io.BytesIO(png_data))
```

**Or**: Handle SVG conversion in Node.js and send image to `/embed-image` endpoint.

---

## Issue 5: Model Download on First Run

**Problem**: First run is very slow or fails with network errors.

**Root Cause**: Sentence Transformers downloads models on first use.

**Fix**: Pre-download models:

```python
# Run this once before starting the service:
from sentence_transformers import SentenceTransformer

print("Downloading text model...")
text_model = SentenceTransformer("all-MiniLM-L6-v2")
print("Downloading image model...")
image_model = SentenceTransformer("clip-ViT-B-32")
print("Models downloaded!")
```

Or set cache directory:
```python
import os
os.environ['SENTENCE_TRANSFORMERS_HOME'] = '/path/to/cache'
```

---

## Issue 6: Elasticsearch Index Refresh

**Problem**: Indexed documents don't appear in search results immediately.

**Root Cause**: Elasticsearch may not have refreshed the index.

**Fix**: Refresh index after indexing:

```typescript
// In batchIndexText.ts, batchIndexImages.ts, batchIndexSVG.ts:
// After indexing, add:
await client.indices.refresh({ index: INDEX_NAME });
```

Or set refresh policy:
```typescript
await client.index({
  index: INDEX_NAME,
  id: iconName,
  document: document,
  refresh: 'wait_for', // Wait for refresh before returning
});
```

---

## Quick Diagnostic Commands

### Test Embedding Service
```bash
# Test text embedding:
curl -X POST http://localhost:8000/embed \
  -H "Content-Type: application/json" \
  -d '{"content": "test query"}'

# Test image embedding (if you have an image file):
curl -X POST http://localhost:8000/embed-image \
  -F "file=@test.png"
```

### Test Elasticsearch
```bash
# Run validation test:
python tests/integration/test_elasticsearch_setup.py

# Check index exists:
curl -X GET "your-es-endpoint/icons" \
  -H "Authorization: ApiKey your-key"
```

### Check Dependencies
```bash
# Python:
pip list | grep -E "fastapi|sentence|elasticsearch|cairo|Pillow"

# Node.js:
cd frontend && npm list | grep -E "elasticsearch|form-data"
```

---

## Most Likely Issues (Priority Order)

1. **ELSER field name** - Change `"text_field"` to `"text"` in `embed.py`
2. **FormData headers** - Add `formData.getHeaders()` when using FormData
3. **Index refresh** - Add refresh after indexing operations
4. **cairosvg dependencies** - Install system libraries
5. **Model download** - Pre-download models or wait for first run

---

## Getting Specific Error Messages

To help debug, please provide:

1. **Full error message** including stack trace
2. **Which endpoint** was called (e.g., `/api/search`, `/api/batchIndexText`)
3. **Request payload** (sanitized)
4. **Service logs** from both FastAPI and Next.js
5. **Elasticsearch version** (if known)

Run this to capture error details:
```bash
# FastAPI service:
uvicorn embed:app --reload --port 8000 --log-level debug

# Next.js:
cd frontend && npm run dev 2>&1 | tee nextjs.log
```

