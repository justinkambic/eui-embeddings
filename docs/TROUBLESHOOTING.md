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
python tests/integration/test_elasticsearch_setup.py
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
python tests/integration/test_elasticsearch_setup.py

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
5. **Run the validation test**: `python tests/integration/test_elasticsearch_setup.py`

Common error patterns:
- `ImportError` → Missing Python package
- `Module not found` → Missing Node.js package
- `Connection refused` → Service not running or wrong port
- `Authentication failed` → Wrong API key or endpoint
- `Dimension mismatch` → Embedding size doesn't match index mapping

---

## Cloud Run Deployment Issues

### Container Failed to Start / PORT Timeout

**Error:**
```
The user-provided container failed to start and listen on the port defined provided by the PORT=8000 environment variable within the allocated timeout.
```

**Causes:**
1. Model loading takes too long (sentence-transformers models are large)
2. Container startup timeout too short
3. Insufficient CPU during startup

**Solutions:**

1. **Increase timeout and enable CPU boost** (already done in script):
   ```bash
   --timeout 300 --startup-cpu-boost
   ```

2. **Check logs** for startup errors:
   ```bash
   gcloud run services logs read eui-python-api \
     --region=us-central1 \
     --project=$PROJECT_ID \
     --limit=50
   ```

3. **Verify Procfile is correct**:
   ```
   web: uvicorn embed:app --host 0.0.0.0 --port $PORT
   ```

4. **Check if models are loading**:
   - Look for "Loading model..." messages in logs
   - First startup can take 2-5 minutes to download/load models

### Build Fails - Missing Entrypoint

**Error:**
```
for Python, provide a main.py or app.py file or set an entrypoint with "GOOGLE_ENTRYPOINT" env var or by creating a "Procfile" file
```

**Solution:**
- Ensure `Procfile` exists in project root
- Content: `web: uvicorn embed:app --host 0.0.0.0 --port $PORT`

### PORT Environment Variable Reserved

**Error:**
```
The following reserved env names were provided: PORT. These values are automatically set by the system.
```

**Solution:**
- Don't set `PORT` in environment variables
- Cloud Run sets it automatically
- Use `$PORT` in Procfile to read it

### Models Taking Too Long to Load

**Symptoms:**
- Container starts but times out before ready
- Logs show model loading messages

**Solutions:**

1. **Pre-warm models** (optional):
   - Models load on first request
   - Consider keeping 1 min-instance to avoid cold starts

2. **Use smaller models** (if possible):
   - Current: `all-MiniLM-L6-v2` (text) and `clip-ViT-B-32` (image)
   - These are already relatively small

3. **Increase resources**:
   ```bash
   --memory 4Gi --cpu 4
   ```

### Health Check Failing

**Symptoms:**
- Service deploys but health checks fail
- Service shows as unhealthy

**Solutions:**

1. **Verify health endpoint**:
   ```bash
   curl https://your-service-url.run.app/health
   ```

2. **Check health endpoint code**:
   - Should return 200 OK
   - Should respond quickly (< 5 seconds)

3. **Increase health check timeout**:
   ```bash
   --startup-probe-timeout 300
   ```

### Out of Memory

**Symptoms:**
- Container crashes during startup
- Logs show "Killed" or "OOM"

**Solutions:**

1. **Increase memory**:
   ```bash
   --memory 4Gi  # Increase from 2Gi
   ```

2. **Reduce model size** (if possible):
   - Current models need ~1-2GB RAM

### API Key Authentication Not Working

**Symptoms:**
- Requests return 401 Unauthorized
- Even with correct API key

**Solutions:**

1. **Verify API keys are set**:
   ```bash
   gcloud run services describe eui-python-api \
     --region=us-central1 \
     --project=$PROJECT_ID \
     --format="value(spec.template.spec.containers[0].env)" | grep API_KEYS
   ```

2. **Check API key format**:
   - Should be comma-separated: `key1,key2,key3`
   - No spaces around commas

3. **Verify header name**:
   - Default: `X-API-Key`
   - Check request includes this header

### CORS Errors in Cloud Run

**Symptoms:**
- Browser shows CORS error
- Frontend can't call Python API

**Solutions:**

1. **Set CORS_ORIGINS**:
   ```bash
   export CORS_ORIGINS="https://your-frontend-url.run.app"
   gcloud run services update eui-python-api \
     --region=us-central1 \
     --project=$PROJECT_ID \
     --update-env-vars CORS_ORIGINS=$CORS_ORIGINS
   ```

2. **Check CORS configuration**:
   - Should include frontend URL
   - No trailing slashes

### Permission Denied Errors

**Solution**: Ensure you have Cloud Run deployment permissions:
```bash
# Check your permissions
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:user:YOUR_EMAIL"
```

You need at least `roles/run.developer` or `roles/run.admin`.

### API Not Enabled Errors

**Solution**: The script will try to enable Cloud Run API automatically. If it fails:
```bash
gcloud services enable run.googleapis.com --project=$PROJECT_ID
```

### Build Failures

**Solution**: Check build logs:
```bash
gcloud builds list --project=$PROJECT_ID --limit=5
gcloud builds log BUILD_ID --project=$PROJECT_ID
```

### Service Not Accessible

**Solution**: Check service status:
```bash
gcloud run services describe eui-python-api \
  --region us-central1 \
  --project $PROJECT_ID
```

Verify `--allow-unauthenticated` is set (script does this automatically).

### Environment Variables Not Working

**Solution**: Verify environment variables are set correctly:
```bash
gcloud run services describe eui-python-api \
  --region us-central1 \
  --project $PROJECT_ID \
  --format="value(spec.template.spec.containers[0].env)"
```

### Browser Shows "Search failed" Error

**Possible causes:**
1. `FRONTEND_API_KEY` not set in Cloud Run environment
2. API key doesn't match one in Python API's `API_KEYS`
3. Python API not accessible from Next.js

**Check:**
```bash
# Verify environment variable is set
gcloud run services describe eui-frontend \
  --region=us-central1 \
  --project=$PROJECT_ID \
  --format="value(spec.template.spec.containers[0].env)" | grep FRONTEND_API_KEY

# Check Next.js logs
gcloud run services logs read eui-frontend \
  --region=us-central1 \
  --project=$PROJECT_ID
```

### Mixed Content Warnings

**Symptom**: Browser warns about mixed HTTP/HTTPS content

**Solution**: Ensure all URLs use HTTPS:
- Set `EMBEDDING_SERVICE_URL` to HTTPS URL
- Set `NEXT_PUBLIC_EMBEDDING_SERVICE_URL` to HTTPS URL
- Set `PYTHON_API_BASE_URL` to HTTPS URL

### Debugging Cloud Run Services

**View Service Logs:**
```bash
gcloud run services logs read eui-python-api \
  --region=us-central1 \
  --project=$PROJECT_ID \
  --limit=100
```

**Check Service Status:**
```bash
gcloud run services describe eui-python-api \
  --region=us-central1 \
  --project=$PROJECT_ID
```

**View Environment Variables:**
```bash
gcloud run services describe eui-python-api \
  --region=us-central1 \
  --project=$PROJECT_ID \
  --format="value(spec.template.spec.containers[0].env)"
```

**Test Health Endpoint:**
```bash
curl https://your-service-url.run.app/health
```

**View Build Logs:**
```bash
gcloud builds list --project=$PROJECT_ID --limit=5
gcloud builds log BUILD_ID --project=$PROJECT_ID
```

**Getting Help:**
1. **Check Cloud Console**:
   - Cloud Run → Services → Your Service → Logs
   - Cloud Build → Build History → Your Build → Logs

2. **Common log locations**:
   - Startup errors: Cloud Run service logs
   - Build errors: Cloud Build logs
   - Runtime errors: Cloud Run service logs

3. **Useful links**:
   - [Cloud Run Troubleshooting](https://cloud.google.com/run/docs/troubleshooting)
   - [Buildpacks Documentation](https://cloud.google.com/docs/buildpacks)

