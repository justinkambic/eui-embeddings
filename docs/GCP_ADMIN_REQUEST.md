# GCP Admin Request Template

If you don't have permission to create projects or enable APIs, use this template to request access from your GCP organization administrator.

## Email Template

**Subject**: Request for GCP Project Setup - EUI Icon Embeddings

**Body**:

Hi [Admin Name],

I need to deploy the EUI Icon Embeddings application to Google Cloud Platform. Could you please help with the following:

### 1. Project Access

**Option A**: Create a new project for me
- Project name: `eui-icon-embeddings`
- Project ID: `eui-icon-embeddings-[org-suffix]` (or your naming convention)

**Option B**: Grant me access to an existing project
- Project ID: `[PROJECT_ID]`

### 2. Required IAM Roles

Please grant me the following IAM roles on the project:

- `roles/run.admin` - Deploy and manage Cloud Run services
- `roles/cloudbuild.builds.editor` - Trigger Cloud Build jobs
- `roles/secretmanager.admin` - Create and manage secrets in Secret Manager
- `roles/iam.serviceAccountAdmin` - Create and manage service accounts
- `roles/storage.admin` - Push Docker images to Container Registry (or `roles/storage.objectAdmin`)

**Alternative**: Grant `roles/editor` role for full project access (if your org policy allows).

### 3. Required APIs

Please enable these APIs on the project:

- Cloud Build API (`cloudbuild.googleapis.com`)
- Cloud Run API (`run.googleapis.com`)
- Secret Manager API (`secretmanager.googleapis.com`)
- IAM API (`iam.googleapis.com`)
- Container Registry API (`containerregistry.googleapis.com`)

### 4. Billing

Please ensure billing is enabled on the project (required for Cloud Run).

### 5. Service Account Permissions

After I create service accounts, I'll need them to have:
- `roles/secretmanager.secretAccessor` - Access secrets in Secret Manager

I can handle granting these permissions myself if I have `roles/iam.serviceAccountAdmin`.

---

**My email**: [YOUR_EMAIL@example.com]

**Timeline**: [e.g., "ASAP" or "By [DATE]"]

Thank you!

---

## Alternative: Minimal Permissions Request

If your organization has strict IAM policies, you can request these specific permissions instead:

### Minimum Required Permissions

1. **Cloud Run**:
   - `run.services.create`
   - `run.services.update`
   - `run.services.get`
   - `run.services.list`

2. **Cloud Build**:
   - `cloudbuild.builds.create`
   - `cloudbuild.builds.get`

3. **Secret Manager**:
   - `secretmanager.secrets.create`
   - `secretmanager.secrets.get`
   - `secretmanager.secrets.update`
   - `secretmanager.versions.add`

4. **IAM**:
   - `iam.serviceAccounts.create`
   - `iam.serviceAccounts.get`
   - `iam.serviceAccounts.list`
   - `iam.serviceAccounts.setIamPolicy`

5. **Container Registry**:
   - `storage.objects.create`
   - `storage.objects.get`
   - `storage.objects.list`

## What You Can Do After Access is Granted

Once you have the necessary permissions:

1. **Verify access**:
   ```bash
   gcloud projects get-iam-policy YOUR_PROJECT_ID \
     --flatten="bindings[].members" \
     --filter="bindings.members:user:YOUR_EMAIL@example.com"
   ```

2. **Follow the setup guide**: Continue with `docs/GCP_PROJECT_SETUP.md` starting from Step 2

3. **Run verification**:
   ```bash
   ./scripts/verify-phase6.sh
   ```

## Troubleshooting Permission Issues

If you encounter permission errors:

1. **Check your current permissions**:
   ```bash
   gcloud projects get-iam-policy YOUR_PROJECT_ID \
     --flatten="bindings[].members" \
     --filter="bindings.members:user:YOUR_EMAIL@example.com" \
     --format="table(bindings.role)"
   ```

2. **Test specific permissions**:
   ```bash
   # Test Cloud Run access
   gcloud run services list --region=us-central1
   
   # Test Secret Manager access
   gcloud secrets list
   
   # Test IAM access
   gcloud iam service-accounts list
   ```

3. **Common permission errors**:
   - `PERMISSION_DENIED: The caller does not have permission` → Need IAM role
   - `API not enabled` → Need API enabled or `roles/servicemanagement.admin`
   - `Billing not enabled` → Need billing account linked

## Security Considerations

If your organization has security concerns:

1. **Service accounts**: We create dedicated service accounts with minimal permissions
2. **Secrets**: All sensitive data stored in Secret Manager (encrypted)
3. **Network**: Services can use internal-only networking
4. **IAM**: Principle of least privilege applied
5. **Cost**: Cloud Run scales to zero, pay-per-use pricing

You can review the security implementation in:
- `cloud-run-python.yaml` - Service account and secret configuration
- `scripts/setup-service-accounts.sh` - IAM role assignments
- `scripts/setup-secrets.sh` - Secret management

