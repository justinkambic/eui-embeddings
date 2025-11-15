# Basic Deployment Troubleshooting

## Common Issues and Solutions

### Issue: Container Failed to Start / PORT Timeout

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

### Issue: Build Fails - Missing Entrypoint

**Error:**
```
for Python, provide a main.py or app.py file or set an entrypoint with "GOOGLE_ENTRYPOINT" env var or by creating a "Procfile" file
```

**Solution:**
- Ensure `Procfile` exists in project root
- Content: `web: uvicorn embed:app --host 0.0.0.0 --port $PORT`

### Issue: PORT Environment Variable Reserved

**Error:**
```
The following reserved env names were provided: PORT. These values are automatically set by the system.
```

**Solution:**
- Don't set `PORT` in environment variables
- Cloud Run sets it automatically
- Use `$PORT` in Procfile to read it

### Issue: Models Taking Too Long to Load

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

### Issue: Health Check Failing

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

### Issue: Out of Memory

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

### Issue: API Key Authentication Not Working

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

### Issue: CORS Errors

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

## Debugging Commands

### View Service Logs
```bash
gcloud run services logs read eui-python-api \
  --region=us-central1 \
  --project=$PROJECT_ID \
  --limit=100
```

### Check Service Status
```bash
gcloud run services describe eui-python-api \
  --region=us-central1 \
  --project=$PROJECT_ID
```

### View Environment Variables
```bash
gcloud run services describe eui-python-api \
  --region=us-central1 \
  --project=$PROJECT_ID \
  --format="value(spec.template.spec.containers[0].env)"
```

### Test Health Endpoint
```bash
curl https://your-service-url.run.app/health
```

### View Build Logs
```bash
gcloud builds list --project=$PROJECT_ID --limit=5
gcloud builds log BUILD_ID --project=$PROJECT_ID
```

## Getting Help

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

