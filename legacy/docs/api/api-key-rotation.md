# API Key Rotation Guide

This document describes the process for rotating API keys used to authenticate with the EUI Icon Embeddings Python API.

## Overview

API keys are stored in Google Secret Manager and can be managed using the `scripts/manage-api-keys.sh` script. Keys are stored as a JSON array in the secret.

## Prerequisites

- Google Cloud SDK (`gcloud`) installed and configured
- Access to the GCP project where secrets are stored
- `roles/secretmanager.secretAccessor` permission (to read keys)
- `roles/secretmanager.secretAdmin` permission (to create/update secrets)

## Key Rotation Process

### Step 1: Generate New API Key

```bash
# Set your project ID
export GOOGLE_CLOUD_PROJECT=your-project-id

# Generate and add a new API key
./scripts/manage/manage-api-keys.sh generate
```

The script will:
1. Generate a secure random API key (32+ characters)
2. Add it to Secret Manager
3. Display the new key (save it securely - it won't be shown again!)

**Important**: Save the new API key immediately - it will not be displayed again.

### Step 2: Update Services with New Key

#### Option A: Update Frontend Service (Recommended for Zero Downtime)

1. **Add new key to Secret Manager** (already done in Step 1)

2. **Update Frontend Cloud Run service** with new key:
   ```bash
   # Get the new key from Step 1, then:
   gcloud run services update eui-frontend \
     --update-secrets FRONTEND_API_KEY=frontend-api-key:latest \
     --region us-central1
   ```
   
   Or if using environment variable:
   ```bash
   gcloud run services update eui-frontend \
     --set-env-vars FRONTEND_API_KEY=new-api-key-here \
     --region us-central1
   ```

3. **Verify frontend can authenticate**:
   ```bash
   curl https://icons.example.com/api/search \
     -X POST \
     -H "Content-Type: application/json" \
     -d '{"type":"text","query":"test"}'
   ```

#### Option B: Update Secret Manager Secret (For Multiple Services)

If multiple services use the same secret:

1. **Add new key** (already done in Step 1)

2. **Services will automatically pick up the new key** on next secret version access

3. **Verify services are working** with the new key

### Step 3: Remove Old API Key (After Verification)

**Wait 24-48 hours** after deploying the new key to ensure all services are updated and working.

Then remove the old key:

```bash
# List current keys (to identify the old one)
./scripts/manage/manage-api-keys.sh list

# Remove the old key
./scripts/manage/manage-api-keys.sh remove old-api-key-here
```

### Step 4: Verify Old Key is Invalid

Test that the old key no longer works:

```bash
# This should return 401 Unauthorized
curl https://api.icons.example.com/search \
  -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: old-api-key-here" \
  -d '{"type":"text","query":"test"}'
```

## Emergency Rotation

If a key is compromised, follow these steps immediately:

1. **Generate new key**:
   ```bash
   ./scripts/manage/manage-api-keys.sh generate
   ```

2. **Update all services immediately** (don't wait for verification)

3. **Remove compromised key**:
   ```bash
   ./scripts/manage/manage-api-keys.sh remove compromised-key-here
   ```

4. **Monitor logs** for any unauthorized access attempts

## Key Management Commands

### List All Keys (Masked)
```bash
./scripts/manage/manage-api-keys.sh list
```

### Generate and Add New Key
```bash
./scripts/manage/manage-api-keys.sh generate
```

### Add Existing Key
```bash
./scripts/manage/manage-api-keys.sh add your-api-key-here
```

### Remove Key
```bash
./scripts/manage/manage-api-keys.sh remove old-api-key-here
```

## Best Practices

1. **Regular Rotation**: Rotate keys every 90 days or as per your security policy
2. **Key Length**: Use keys of at least 32 characters (default in script)
3. **Secure Storage**: Never commit API keys to version control
4. **Separate Keys**: Use different keys for different services/environments
5. **Monitor Usage**: Regularly check logs for unusual API key usage
6. **Gradual Rollout**: Add new key before removing old one to avoid downtime
7. **Documentation**: Keep track of which services use which keys

## Secret Manager Configuration

### Secret Format

Keys are stored as a JSON array:
```json
["key1", "key2", "key3"]
```

### Secret Name

Default: `api-keys`

Can be overridden via `API_KEYS_SECRET_NAME` environment variable.

### Access Control

Ensure service accounts have the `roles/secretmanager.secretAccessor` role:

```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:eui-python-api-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## Troubleshooting

### Key Not Working After Rotation

1. **Check Secret Manager**: Verify key exists in Secret Manager
   ```bash
   ./scripts/manage/manage-api-keys.sh list
   ```

2. **Check Service Configuration**: Verify service is reading from correct secret
   ```bash
   gcloud run services describe eui-python-api --region us-central1 \
     --format='value(spec.template.spec.containers[0].env)'
   ```

3. **Check Service Account Permissions**: Verify service account can access secrets
   ```bash
   gcloud projects get-iam-policy PROJECT_ID \
     --flatten="bindings[].members" \
     --filter="bindings.members:serviceAccount:*"
   ```

4. **Check Logs**: Look for authentication errors
   ```bash
   gcloud logging read "resource.type=cloud_run_revision AND textPayload=~'API key'" \
     --limit 50
   ```

### Service Can't Access Secret Manager

1. **Verify service account** has correct permissions
2. **Check project ID** is set correctly
3. **Verify secret exists** and is accessible
4. **Check service is using correct secret name**

## Environment Variables

### For API Key Management Script

- `GOOGLE_CLOUD_PROJECT` - GCP project ID (required)
- `API_KEYS_SECRET_NAME` - Secret name (default: `api-keys`)
- `API_KEY_LENGTH` - Key length in characters (default: `32`)

### For Python API Service

- `API_KEYS_SECRET_NAME` - Secret name containing API keys (default: empty, uses env var)
- `API_KEY_HEADER` - HTTP header name for API key (default: `X-API-Key`)
- `API_KEYS` - Comma-separated list of keys (for local development, overrides Secret Manager)

### For Frontend Service

- `FRONTEND_API_KEY` - API key for frontend to authenticate with Python API

## Related Documentation

- `docs/ENVIRONMENT_VARIABLES.md` - Complete environment variable reference
- `docs/DOCKERIZE.md` - Phase 4: API Key Authentication details
- `scripts/manage-api-keys.sh` - API key management script

