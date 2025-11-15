# Basic Deployment Cleanup Guide

Quick reference for deleting Cloud Run services deployed via basic deployment.

## Quick Commands

### List Services (No Deletion)

```bash
# Show service information
./scripts/delete-basic.sh list

# Or manually
gcloud run services list --project=$PROJECT_ID --region=us-central1
```

### Delete Services

```bash
# Delete both services
./scripts/delete-basic.sh both

# Delete Python API only
./scripts/delete-basic.sh python

# Delete Frontend only
./scripts/delete-basic.sh frontend
```

## Manual Deletion Commands

If you prefer to delete manually:

```bash
# Set project and region
export PROJECT_ID="elastic-observability"
export REGION="us-central1"

# Delete Python API
gcloud run services delete eui-python-api \
  --region=$REGION \
  --project=$PROJECT_ID

# Delete Frontend
gcloud run services delete eui-frontend \
  --region=$REGION \
  --project=$PROJECT_ID
```

## Get Service Information

### Service Names
- Python API: `eui-python-api`
- Frontend: `eui-frontend`

### Get Service URLs

```bash
# Python API URL
gcloud run services describe eui-python-api \
  --region=us-central1 \
  --project=$PROJECT_ID \
  --format="value(status.url)"

# Frontend URL
gcloud run services describe eui-frontend \
  --region=us-central1 \
  --project=$PROJECT_ID \
  --format="value(status.url)"
```

### Get All Service Details

```bash
# List all Cloud Run services
gcloud run services list \
  --project=$PROJECT_ID \
  --region=us-central1 \
  --format="table(metadata.name,status.url,status.conditions[0].status,metadata.creationTimestamp)"
```

## Service IDs Reference

When deleting, you need:
- **Service Name**: `eui-python-api` or `eui-frontend`
- **Region**: `us-central1` (or your configured region)
- **Project ID**: Your GCP project ID (e.g., `elastic-observability`)

## Cleanup Script Features

The `delete-basic.sh` script provides:
- ✅ Confirmation prompts (prevents accidental deletion)
- ✅ Service existence checking
- ✅ Colored output for clarity
- ✅ Lists services before deletion
- ✅ Handles missing services gracefully

## Complete Cleanup

To remove everything related to the deployment:

```bash
# 1. Delete Cloud Run services
./scripts/delete-basic.sh both

# 2. (Optional) Delete container images from Container Registry
gcloud container images list --project=$PROJECT_ID
gcloud container images delete gcr.io/$PROJECT_ID/eui-python-api:latest --quiet
gcloud container images delete gcr.io/$PROJECT_ID/eui-frontend:latest --quiet

# 3. (Optional) Delete all revisions (if you want to clean up old revisions)
# Cloud Run automatically keeps old revisions - they don't cost anything
# but you can delete them if needed:
gcloud run revisions list --service=eui-python-api --region=us-central1 --project=$PROJECT_ID
gcloud run revisions delete REVISION_NAME --region=us-central1 --project=$PROJECT_ID
```

## Verification

After deletion, verify services are gone:

```bash
# Should return empty or "Listed 0 items"
gcloud run services list \
  --project=$PROJECT_ID \
  --region=us-central1 \
  --filter="metadata.name:eui-python-api OR metadata.name:eui-frontend"
```

## Troubleshooting

### "Service not found" error

This is normal if the service was already deleted or never existed.

### "Permission denied" error

You need `roles/run.admin` or `roles/run.developer` to delete services.

### Delete without confirmation

The script requires confirmation. To delete without prompts, use manual commands with `--quiet`:

```bash
gcloud run services delete eui-python-api \
  --region=us-central1 \
  --project=$PROJECT_ID \
  --quiet
```

## Cost Impact

Deleting Cloud Run services:
- ✅ Stops all charges immediately
- ✅ No data retention costs
- ✅ Container images remain in Container Registry (small storage cost)
- ✅ Old revisions remain but don't cost anything (they're metadata only)

To fully clean up costs, also delete container images if you don't need them.

