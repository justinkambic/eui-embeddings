# Cost Analysis for Basic Deployment

## Resource Allocations

### Python API
- **Memory**: 2 GB
- **CPU**: 2 vCPU
- **Max Instances**: 10
- **Min Instances**: 0 (scales to zero)
- **Timeout**: 60 seconds

### Frontend
- **Memory**: 1 GB
- **CPU**: 1 vCPU
- **Max Instances**: 5
- **Min Instances**: 0 (scales to zero)
- **Timeout**: 60 seconds

## Cloud Run Pricing Model

**Key Point**: Cloud Run charges only when handling requests. With `min-instances: 0`, services scale to zero when idle.

### Pricing Components

1. **CPU Allocation** (only charged when handling requests)
   - $0.00002400 per vCPU-second
   - Python API: 2 vCPU × $0.00002400 = $0.00004800/second when active
   - Frontend: 1 vCPU × $0.00002400 = $0.00002400/second when active

2. **Memory Allocation** (only charged when handling requests)
   - $0.00000250 per GB-second
   - Python API: 2 GB × $0.00000250 = $0.00000500/second when active
   - Frontend: 1 GB × $0.00000250 = $0.00000250/second when active

3. **Request Pricing**
   - $0.40 per million requests
   - First 2 million requests/month are FREE

4. **Free Tier** (per month)
   - 2 million requests
   - 360,000 GB-seconds of memory
   - 180,000 vCPU-seconds of compute

## Cost Scenarios

### Scenario 1: Light Usage (Testing/Development)

**Assumptions:**
- 1,000 requests/month
- Average request duration: 2 seconds
- Services scale to zero when idle

**Costs:**
- Requests: FREE (under 2M free tier)
- Compute: FREE (under free tier limits)
- **Total: $0/month**

### Scenario 2: Moderate Usage

**Assumptions:**
- 100,000 requests/month
- Average request duration: 2 seconds
- Python API: 50,000 requests (2s each) = 100,000 vCPU-seconds, 100,000 GB-seconds
- Frontend: 50,000 requests (1s each) = 50,000 vCPU-seconds, 50,000 GB-seconds

**Costs:**
- Requests: FREE (under 2M free tier)
- Python API compute: 100,000 vCPU-s × $0.00002400 = $2.40
- Python API memory: 100,000 GB-s × $0.00000250 = $0.25
- Frontend compute: 50,000 vCPU-s × $0.00002400 = $1.20
- Frontend memory: 50,000 GB-s × $0.00000250 = $0.13
- **Total: ~$4/month**

### Scenario 3: Heavy Usage

**Assumptions:**
- 1,000,000 requests/month
- Average request duration: 2 seconds
- Python API: 500,000 requests (2s each) = 1,000,000 vCPU-seconds, 1,000,000 GB-seconds
- Frontend: 500,000 requests (1s each) = 500,000 vCPU-seconds, 500,000 GB-seconds

**Costs:**
- Requests: FREE (under 2M free tier)
- Python API compute: 1,000,000 vCPU-s × $0.00002400 = $24.00
- Python API memory: 1,000,000 GB-s × $0.00000250 = $2.50
- Frontend compute: 500,000 vCPU-s × $0.00002400 = $12.00
- Frontend memory: 500,000 GB-s × $0.00000250 = $1.25
- **Total: ~$40/month**

### Scenario 4: Idle (No Traffic)

**Assumptions:**
- 0 requests
- Services scale to zero

**Costs:**
- **Total: $0/month** (no charges when idle)

## Cost Safety Features

### ✅ Scale to Zero (Enabled by Default)

```yaml
min-instances: 0  # Services scale to zero when idle
```

**Impact:**
- No charges when no requests
- Services start automatically when requests arrive
- Cold start delay: ~5-10 seconds (acceptable for most use cases)

### ✅ Request Limits

```yaml
max-instances: 10  # Python API
max-instances: 5   # Frontend
```

**Impact:**
- Prevents runaway scaling
- Caps maximum concurrent instances
- Protects against cost spikes

### ✅ Timeout Limits

```yaml
timeout: 60 seconds
```

**Impact:**
- Prevents long-running requests from accumulating costs
- Requests timeout after 60 seconds

## Cost Optimization Tips

### 1. Keep Scale-to-Zero Enabled

**Don't change this:**
```bash
# Default is already optimal
--min-instances 0
```

**Only increase if:**
- You need instant response (no cold start)
- You have consistent traffic
- You're willing to pay for always-on instances

### 2. Monitor Usage

```bash
# Check Cloud Run metrics
gcloud run services describe eui-python-api \
  --region=us-central1 \
  --project=$PROJECT_ID \
  --format="value(status.conditions)"

# View billing
gcloud billing accounts list
```

### 3. Set Budget Alerts

In GCP Console:
1. Go to Billing → Budgets & alerts
2. Create budget alert
3. Set threshold (e.g., $10/month)
4. Get email notifications

### 4. Reduce Resource Allocation (If Needed)

**If costs are higher than expected:**

```bash
# Reduce Python API resources
gcloud run services update eui-python-api \
  --region=us-central1 \
  --project=$PROJECT_ID \
  --memory=1Gi \
  --cpu=1

# Reduce Frontend resources
gcloud run services update eui-frontend \
  --region=us-central1 \
  --project=$PROJECT_ID \
  --memory=512Mi \
  --cpu=0.5
```

**Trade-off:** May increase request duration, but reduces costs.

## Cost Comparison

| Resource | Current Allocation | Lower Cost Option | Cost Difference |
|----------|-------------------|-------------------|------------------|
| Python API Memory | 2 GB | 1 GB | ~50% reduction |
| Python API CPU | 2 vCPU | 1 vCPU | ~50% reduction |
| Frontend Memory | 1 GB | 512 MB | ~50% reduction |
| Frontend CPU | 1 vCPU | 0.5 vCPU | ~50% reduction |

**Note:** Lower allocations may increase request duration. Test before reducing.

## Estimated Monthly Costs

| Usage Level | Requests/Month | Estimated Cost |
|-------------|----------------|----------------|
| **Idle** | 0 | $0 |
| **Light** | 1,000 | $0 (free tier) |
| **Moderate** | 100,000 | ~$4 |
| **Heavy** | 1,000,000 | ~$40 |
| **Very Heavy** | 10,000,000 | ~$400 |

**Assumptions:**
- Average request duration: 2 seconds
- Scale-to-zero enabled
- Using free tier where applicable

## What Won't Cost Money

✅ **Idle time** - Services scale to zero, no charges  
✅ **Storage** - Container images stored in Container Registry (minimal cost, ~$0.026/GB/month)  
✅ **First 2M requests/month** - Free tier  
✅ **Health checks** - Internal, don't count as requests  
✅ **Logs** - Cloud Logging has free tier (50 GB/month)  

## What Will Cost Money

⚠️ **Active requests** - Charged per vCPU-second and GB-second  
⚠️ **Requests over 2M/month** - $0.40 per million  
⚠️ **Always-on instances** - If you set min-instances > 0  

## Cost Protection

### Budget Alerts (Recommended)

Set up in GCP Console:
1. Billing → Budgets & alerts
2. Create budget: $10/month
3. Alert at 50%, 90%, 100%

### Delete Services When Not Needed

```bash
# Stop all charges immediately
./scripts/delete-basic.sh both
```

### Monitor Usage

```bash
# Check current month's usage
gcloud billing projects describe $PROJECT_ID \
  --format="value(billingAccountName)"

# View Cloud Run metrics
gcloud run services list \
  --region=us-central1 \
  --project=$PROJECT_ID \
  --format="table(metadata.name,status.url,status.conditions[0].status)"
```

## Summary

**Your Current Configuration:**
- ✅ **Scale-to-zero enabled** - No charges when idle
- ✅ **Reasonable resource limits** - 2GB/2CPU for API, 1GB/1CPU for frontend
- ✅ **Request limits** - Max 10 instances (API), 5 instances (frontend)
- ✅ **Timeout limits** - 60 seconds max per request

**Expected Costs:**
- **Idle**: $0/month
- **Light usage**: $0/month (free tier)
- **Moderate usage**: ~$4/month
- **Heavy usage**: ~$40/month

**Cost Safety:**
- Services scale to zero automatically
- Free tier covers first 2M requests/month
- Resource limits prevent runaway costs
- Easy to delete services if needed

**Bottom Line:** With scale-to-zero enabled, you'll only pay for actual usage. For testing/development, expect $0-5/month. Even with moderate production traffic, costs should stay under $50/month.

