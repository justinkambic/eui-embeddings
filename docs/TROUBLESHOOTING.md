# Troubleshooting Guide

## Common Issues and Solutions

### 1. ELSER Inference API Error

**Symptom**: Error when generating sparse embeddings, e.g., "field name mismatch" or "model not found"

**Issue**: The ELSER inference API expects a specific field name in the document.

**Solution**: Update `embed.py` to use the correct field name:

```python
# Current (may be incorrect):
inference_response = es_client.ml.infer_trained_model(
    model_id=".elser_model_2",
    body={
        "docs": [{"text_field": request.content}]
    }
)

# Should be (check your ELSER model configuration):
inference_response = es_client.ml.infer_trained_model(
    model_id=".elser_model_2",
    body={
        "docs": [{"text": request.content}]  # or check your model's expected field
    }
)
```

**Alternative**: If ELSER is not deployed, the code will continue without sparse embeddings (this is expected).

---

### 2. FormData Import Error in Next.js

**Symptom**: `FormData is not defined` or import errors in `search.ts`

**Issue**: Next.js API routes may not have FormData available in the same way as browser code.

**Solution**: Use a different approach for image uploads:

```typescript
// Instead of FormData, send base64 directly or use multipart/form-data differently
import FormData from "form-data";

// Or use a different approach:
const formData = new FormData();
// Make sure form-data package is installed: npm install form-data @types/form-data
```

**Check**: Ensure `form-data` is installed:
```bash
cd frontend
npm install form-data @types/form-data
```

---

### 3. Elasticsearch Query Structure Error

**Symptom**: Error when executing search, e.g., "query malformed" or "knn not supported"

**Issue**: The Elasticsearch query structure may need adjustment based on your ES version.

**Solution**: Update `frontend/pages/api/search.ts`:

```typescript
// For Elasticsearch 8.x, the query structure should be:
const searchBody: any = {
  size: 10,
  knn: {
    field: embeddingField,
    query_vector: embeddings,
    k: 10,
    num_candidates: 100,
  },
};

// For hybrid search with ELSER:
if (type === "text" && sparseEmbeddings) {
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
  // knn is added separately
  searchBody.knn = {
    field: embeddingField,
    query_vector: embeddings,
    k: 10,
    num_candidates: 100,
  };
}
```

---

### 4. cairosvg Import Error

**Symptom**: `ImportError: cannot import name 'svg2png' from 'cairosvg'`

**Issue**: cairosvg may require system dependencies (Cairo, Pango, etc.) or the import syntax may differ.

**Solution**: 

**Option A**: Install system dependencies (macOS):
```bash
brew install cairo pango gdk-pixbuf libffi
pip install cairosvg
```

**Option B**: Use alternative SVG-to-image conversion:
```python
# In embed.py, replace cairosvg with alternative:
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM

# Or use PIL with svg2png alternative
```

**Option C**: Handle SVG conversion in Node.js and send image to Python:
- Convert SVG to PNG in TypeScript/Node.js
- Send PNG image to `/embed-image` endpoint instead

---

### 5. CLIP Model Loading Error

**Symptom**: Error loading `clip-ViT-B-32` model or slow startup

**Issue**: Model needs to be downloaded on first run, or there's a version mismatch.

**Solution**:
- First run will download the model (this is normal and may take time)
- Ensure internet connection for first download
- Check available disk space (models can be large)
- If issues persist, try explicit model path:
```python
from sentence_transformers import SentenceTransformer
image_model = SentenceTransformer("sentence-transformers/clip-ViT-B-32")
```

---

### 6. Image Embedding Dimension Mismatch

**Symptom**: Error when indexing images: "dimension mismatch" or "expected 384 dims"

**Issue**: CLIP model may output different dimensions than expected.

**Solution**: Verify embedding dimensions:
```python
# Add debug logging in embed.py:
embeddings = image_model.encode(image, convert_to_numpy=True).tolist()
print(f"Image embedding dimensions: {len(embeddings)}")  # Should be 384
```

If not 384, update Elasticsearch mapping:
```python
# In utils/es_index_setup.py, update dims to match actual output
"image_embedding": {
    "type": "dense_vector",
    "dims": <actual_dimension>,  # Update this
    "index": True,
    "similarity": "cosine"
}
```

---

### 7. Elasticsearch Connection Error

**Symptom**: Cannot connect to Elasticsearch or authentication fails

**Solution**:
1. Verify environment variables are set:
```bash
echo $ELASTICSEARCH_ENDPOINT
echo $ELASTICSEARCH_API_KEY
```

2. Test connection:
```bash
python test_elasticsearch_setup.py
```

3. Check Elasticsearch client initialization in `frontend/client/es.ts`:
```typescript
export const client = new Client({
  node: process.env.ELASTICSEARCH_ENDPOINT,
  auth: {
    apiKey: process.env.ELASTICSEARCH_API_KEY,
  },
});
```

---

### 8. Icon Rendering Error

**Symptom**: Error when rendering EuiIcon components: "EuiIcon is not available"

**Issue**: EuiIcon may not be properly imported or available in server-side context.

**Solution**: Check `frontend/utils/icon_renderer.ts`:
```typescript
import { EuiIcon } from '@elastic/eui';

// Ensure @elastic/eui is installed:
// cd frontend && npm install @elastic/eui
```

If server-side rendering issues persist, consider:
- Using a different rendering approach
- Pre-rendering icons and storing them
- Using a headless browser (Puppeteer) for rendering

---

### 9. Batch Indexing Timeout

**Symptom**: Batch indexing endpoints timeout or fail on large batches

**Solution**:
- Reduce batch size in the endpoint
- Add longer timeout settings
- Process in smaller chunks
- Add retry logic

Update batch sizes in:
- `batchIndexText.ts`: `const batchSize = 10;` (reduce if needed)
- `batchIndexImages.ts`: `const batchSize = 5;` (reduce if needed)
- `batchIndexSVG.ts`: `const batchSize = 10;` (reduce if needed)

---

### 10. Search Returns No Results

**Symptom**: Search API returns empty results even when data is indexed

**Possible Causes**:
1. **Index not refreshed**: Elasticsearch may not have refreshed the index
   ```typescript
   // After indexing, refresh the index:
   await client.indices.refresh({ index: INDEX_NAME });
   ```

2. **Wrong embedding field**: Ensure you're searching the correct field
   - Text search → `text_embedding`
   - Image search → `image_embedding`
   - SVG search → `svg_embedding`

3. **Dimension mismatch**: Embeddings must match index mapping dimensions

4. **No data indexed**: Verify data exists:
   ```bash
   # Check Elasticsearch directly:
   curl -X GET "your-es-endpoint/icons/_search?pretty"
   ```

---

## Debugging Steps

### 1. Check Service Status

```bash
# Check if embedding service is running:
curl http://localhost:8000/docs

# Test text embedding:
curl -X POST http://localhost:8000/embed \
  -H "Content-Type: application/json" \
  -d '{"content": "test"}'
```

### 2. Check Elasticsearch

```bash
# Run validation test:
python test_elasticsearch_setup.py

# Check index exists:
curl -X GET "your-es-endpoint/icons" -H "Authorization: ApiKey your-key"
```

### 3. Check Logs

- **FastAPI logs**: Check terminal where `uvicorn embed:app` is running
- **Next.js logs**: Check terminal where `npm run dev` is running
- **Browser console**: Check for client-side errors

### 4. Verify Dependencies

```bash
# Python:
pip list | grep -E "fastapi|sentence-transformers|elasticsearch|cairosvg|Pillow"

# Node.js:
cd frontend && npm list | grep -E "elasticsearch|next|react"
```

---

## Getting Help

If you encounter an error:

1. **Capture the full error message** including stack trace
2. **Note which endpoint/operation** was being executed
3. **Check the logs** from both FastAPI and Next.js services
4. **Verify environment variables** are set correctly
5. **Run the validation test**: `python test_elasticsearch_setup.py`

Common error patterns:
- `ImportError` → Missing Python package
- `Module not found` → Missing Node.js package
- `Connection refused` → Service not running or wrong port
- `Authentication failed` → Wrong API key or endpoint
- `Dimension mismatch` → Embedding size doesn't match index mapping

