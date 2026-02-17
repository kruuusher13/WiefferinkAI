# GitHub Actions Setup Guide for GarageAI

Complete instructions for setting up and configuring GitHub Actions workflows.

## Prerequisites

- GitHub repository (public or private)
- Admin access to repository settings
- Google Cloud Platform account (for deployment)
- Slack workspace (optional, for notifications)

---

## Step 1: Add GitHub Secrets

GitHub Actions requires secrets for API keys and credentials.

### How to Add Secrets

1. Go to repository → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add each secret below with its value

### Required Secrets

```
GOOGLE_API_KEY
  Description: Google Gemini API key
  Where to get: https://cloud.google.com/docs/authentication
  How to find: Check your .env file or Google Cloud console

GCP_SA_KEY
  Description: Google Cloud service account JSON key
  Where to get: https://console.cloud.google.com/iam-admin/serviceaccounts
  Steps:
    1. Create new service account
    2. Grant roles: Cloud Run Admin, Service Account User
    3. Create JSON key
    4. Copy entire JSON content
    5. Paste as secret

GCP_PROJECT_ID
  Description: Your Google Cloud Project ID
  Where to get: https://console.cloud.google.com/home/dashboard
  Example: garage-ai-prod-12345

GCP_REGION
  Description: Cloud Run region
  Example: us-central1 (or your preferred region)

STAGING_DB_SERVER
  Description: Staging database connection string
  Example: staging-sql.database.windows.net
  Note: Include server name only, not connection string

PROD_DB_SERVER
  Description: Production database connection string
  Example: prod-sql.database.windows.net
  Note: Include server name only, not connection string
```

### Optional Secrets

```
SLACK_WEBHOOK_URL
  Description: Slack webhook for notifications
  Where to get: https://api.slack.com/messaging/webhooks
  Steps:
    1. Go to Slack API site
    2. Create new app or select existing
    3. Enable "Incoming Webhooks"
    4. Add New Webhook to Workspace
    5. Copy webhook URL
    6. Add as SLACK_WEBHOOK_URL secret
```

### Quick Setup Command (if using CLI)

```bash
# Using GitHub CLI (must be authenticated)
gh secret set GOOGLE_API_KEY --body "your-key-here"
gh secret set GCP_SA_KEY < path/to/serviceaccount.json
gh secret set GCP_PROJECT_ID --body "your-project-id"
gh secret set GCP_REGION --body "us-central1"
gh secret set STAGING_DB_SERVER --body "staging-sql.database.windows.net"
gh secret set PROD_DB_SERVER --body "prod-sql.database.windows.net"
```

---

## Step 2: Create GitHub Environments

Environments let you control deployment approvals and secrets.

### Create Staging Environment

1. **Settings** → **Environments** → **New environment**
2. Name: `staging`
3. Click **Configure environment**
4. **Deployment branches**: Select "Allow deployments from specific branches"
   - Select: `main`, `develop`
5. **Required reviewers**: Leave empty (auto-deploy)
6. Click **Save protection rules**

### Create Production Environment

1. **Settings** → **Environments** → **New environment**
2. Name: `production`
3. Click **Configure environment**
4. **Deployment branches**: Select "Allow deployments from specific branches"
   - Select: `main` only
5. **Required reviewers**: ✅ Check this box
   - Add reviewers (e.g., yourself or team leads)
6. Click **Save protection rules**

**Note**: This means production deploys require approval!

---

## Step 3: Configure Branch Protection

Protect your main branch with required status checks.

### Steps

1. **Settings** → **Branches**
2. Click **Add rule** next to "Branch protection rules"
3. **Branch name pattern**: `main`

### Protection Rules

Check these boxes:

✅ **Require a pull request before merging**
- Required approvals: 1
- ✅ Dismiss stale pull request approvals when new commits are pushed

✅ **Require status checks to pass before merging**
- Search and select:
  - `test` (from test.yml)
  - `Code Quality` (from code-quality.yml)
  - `Dependency Audit` (from security.yml)

✅ **Require branches to be up to date before merging**

✅ **Include administrators** (enforce for admins too)

Click **Create**

---

## Step 4: Enable GitHub Code Scanning

Let GitHub scan for vulnerabilities automatically.

### Steps

1. **Security** → **Code scanning**
2. Click **Set up code scanning**
3. Select **GitHub Actions**
4. Choose **CodeQL analysis** or use our existing workflows
5. Click **Enable CodeQL**

This enables:
- Automatic vulnerability detection
- Code quality analysis
- Secrets detection

---

## Step 5: Configure Slack Notifications (Optional)

Get instant Slack alerts for workflow success/failure.

### Create Slack App

1. Go to https://api.slack.com/apps
2. Click **Create New App** → **From scratch**
3. Name: `GarageAI Bot`
4. Select your Slack workspace
5. Click **Create App**

### Enable Incoming Webhooks

1. On app page, go to **Incoming Webhooks**
2. Toggle **Activate Incoming Webhooks**: ON
3. Click **Add New Webhook to Workspace**
4. Select channel: `#deployments` (or create one)
5. Click **Allow**
6. Copy the **Webhook URL**

### Add to GitHub

1. GitHub → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `SLACK_WEBHOOK_URL`
4. Value: Paste the webhook URL from above
5. Click **Add secret**

---

## Step 6: Set Up Docker Registry Authentication

For GitHub Container Registry (GHCR).

### Steps

1. Create personal access token:
   - GitHub → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**
   - Click **Generate new token**
   - Name: `GarageAI CI`
   - Select scopes:
     - ✅ `write:packages`
     - ✅ `read:packages`
     - ✅ `delete:packages`
   - Click **Generate token**
   - Copy token (save somewhere safe!)

2. The workflows use `GITHUB_TOKEN` (auto-created), but you can add your personal token as `GHCR_TOKEN` if needed.

---

## Step 7: Verify Setup

### Check Secrets

```bash
# List all secrets (without values)
gh secret list
```

### Test Workflow Trigger

1. Make a small change
2. Push to develop branch
3. Go to **Actions** tab
4. Watch workflows run:
   - ✅ test.yml should run
   - ✅ code-quality.yml should run
   - ✅ security.yml should run

### First Deployment

1. Merge PR to main
2. Go to **Actions** → **Deploy**
3. Watch deploy.yml run:
   - Build Docker image
   - Run tests
   - Deploy to staging
   - Health checks pass

---

## Troubleshooting

### Workflows Not Running

**Problem**: Pushed code but workflows not triggered

**Solutions**:
1. Check Actions are enabled: **Settings** → **Actions** → **General** → "Allow all actions and reusable workflows"
2. Check branch has .github/workflows files
3. Wait 30 seconds (sometimes takes time)

### Secrets Not Found Error

**Problem**: `Error: Secret not found`

**Solutions**:
1. Verify secret exists in Settings
2. Check exact secret name spelling
3. Secrets are case-sensitive
4. Can't use `${{ secrets. }}` in `if:` conditionals, only in `run:` or `env:`

### Permission Denied

**Problem**: `Permission denied: ... (publickey)`

**Solutions**:
1. Check GCP_SA_KEY is valid JSON
2. Service account needs Cloud Run Admin role
3. Try creating new service account key

### Test Failures in CI But Pass Locally

**Problem**: Tests pass locally but fail in GitHub Actions

**Solutions**:
1. Check Python version: `python --version` (should be 3.12)
2. Check dependencies match: `pip install -r requirements.txt`
3. Check database connection string for test environment
4. Run with same environment vars: `GOOGLE_API_KEY=... pytest tests/`

### Docker Build Fails

**Problem**: Docker build fails in CI but works locally

**Solutions**:
1. Check `Dockerfile` exists in repo root
2. Check all files referenced in Dockerfile are committed
3. Try local build: `docker build -t test .`
4. Check Docker syntax: `docker buildx bake --print`

### Deployment to Staging Hangs

**Problem**: Deploy workflow gets stuck on "Deploy to Cloud Run"

**Solutions**:
1. Check GCP_SA_KEY is valid
2. Check GCP_PROJECT_ID is correct
3. Check Cloud Run API is enabled in GCP
4. Try manual gcloud command locally:
   ```bash
   gcloud auth activate-service-account --key-file=/path/to/key.json
   gcloud config set project YOUR_PROJECT_ID
   gcloud run list
   ```

---

## Monitoring & Alerts

### View Workflow Runs

1. Go to **Actions** tab
2. Click workflow name
3. Click run to see details
4. Click job to see logs

### View Security Findings

1. Go to **Security** tab
2. Click **Code scanning**
3. View detected vulnerabilities
4. Mark as "Won't fix" or "Dismissed" if false positive

### View Deployments

1. Go to **Deployments** tab
2. View deployment history
3. Click deployment for details

### Slack Notifications

- Health check results: Daily 2 AM UTC
- Deployment success/failure: When deploying
- Security issues: When found

---

## Common Workflows

### Deploy Staging Manually

1. **Actions** → **Deploy** → **Run workflow**
2. Environment: `staging`
3. Click **Run workflow**

### Deploy Production Manually

1. Create GitHub Release:
   - Go to **Releases** → **Draft a new release**
   - Tag: `v1.0.0` (semantic versioning)
   - Click **Publish release**
2. Deploy workflow triggers automatically
3. Requires approval in production environment

### Rerun Failed Workflow

1. Go to **Actions** → failed run
2. Click **Re-run jobs** → **Re-run failed jobs**

### View Logs

1. **Actions** → workflow run → job
2. Click each step to expand logs
3. Search logs with browser find (Ctrl+F)

---

## Security Best Practices

### Secrets Safety

✅ **DO**:
- Use GitHub Secrets for all credentials
- Rotate secrets regularly
- Use least-privilege service accounts
- Review Actions runs in Security tab

❌ **DON'T**:
- Commit .env files with secrets
- Pass secrets as command arguments
- Log secrets in workflow output
- Use same secret for multiple environments

### Code Safety

✅ **DO**:
- Require status checks before merge
- Require code review
- Use branch protection
- Scan for secrets and vulnerabilities

❌ **DON'T**:
- Merge directly to main
- Force push to main
- Disable branch protection
- Skip security scans

---

## Advanced Configuration

### Add Custom Status Check

Edit `.github/workflows/test.yml`:

```yaml
- name: Custom Check
  run: |
    # Your custom validation
    pytest tests/
```

### Conditional Steps

```yaml
- name: Deploy to Production
  if: github.ref == 'refs/heads/main'
  run: ...
```

### Matrix Builds (Test Multiple Python Versions)

```yaml
strategy:
  matrix:
    python-version: [3.9, '3.10', '3.11', '3.12']

steps:
  - uses: actions/setup-python@v4
    with:
      python-version: ${{ matrix.python-version }}
```

---

## Getting Help

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub Actions Troubleshooting](https://docs.github.com/en/actions/troubleshooting)
- [Workflow Syntax Reference](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)

---

## Next Steps

1. ✅ Add all required secrets
2. ✅ Create staging and production environments
3. ✅ Set up branch protection for main
4. ✅ Enable Code Scanning
5. ✅ Configure Slack (optional)
6. ✅ Test with a PR to develop
7. ✅ Merge to main and verify staging deploy
8. ✅ Create release and verify production deploy

---

**Status**: ✅ Ready for production use

After completing setup, all workflows should be fully operational!
