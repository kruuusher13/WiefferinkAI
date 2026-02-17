# GitHub Actions Workflows

Automated CI/CD workflows for GarageAI.

## Workflows Overview

### 🧪 [test.yml](test.yml)
**Triggers**: Push to main/develop, Pull Requests

Runs comprehensive test suite:
- Unit tests with pytest
- Code coverage (min 80%)
- Database connectivity
- Tool functionality
- Code formatting check (black)
- Linting (pylint, flake8)
- Type checking (mypy)

**Duration**: ~5 minutes
**Artifacts**: Coverage reports, HTML coverage

---

### 🏥 [health-check.yml](health-check.yml)
**Triggers**: Daily at 2 AM UTC, Manual trigger

Full project health check (mirrors `/project-health start`):
- 🧪 Test phase: Run all tests, check coverage
- 📚 Docs phase: Verify documentation is current
- ✨ Optimize phase: Check code quality, linting
- 📤 Git phase: Repository status check

**Duration**: ~3 minutes
**Reports**: `_bmad/_output/health-*.md`
**Notifications**: Slack (success/failure)

---

### 💎 [code-quality.yml](code-quality.yml)
**Triggers**: Pull Requests to main/develop

Detailed code quality analysis for PRs:
- Black formatting check (strict)
- Pylint linting
- Flake8 additional linting
- Mypy type checking
- Bandit security scan
- Code complexity (radon)
- Dead code detection (vulture)
- Dependency audit

**Duration**: ~3 minutes
**Comments on PR**: Quality report with detailed findings
**Fails if**: Black formatting issues found

---

### 🚀 [deploy.yml](deploy.yml)
**Triggers**: Push to main, Release published, Manual trigger

Deployment pipeline with blue-green strategy:
1. **Build**: Create Docker image, push to registry
2. **Test**: Full test suite + deployment tests
3. **Staging**: Deploy to staging (always on main push)
4. **Production**: Deploy to production (on release only)
   - Blue-green deployment
   - Health checks
   - Smoke tests
   - Automatic rollback on failure

**Duration**: ~10-15 minutes (for full deploy)
**Environments**: Staging, Production
**Notifications**: Slack (deployment success/failure/rollback)

---

### 🔒 [security.yml](security.yml)
**Triggers**: Push to main/develop, PRs, Daily 1 AM UTC

Comprehensive security scanning:
- **pip-audit**: Python dependency vulnerabilities
- **Safety**: Additional dependency checks
- **Bandit**: Python code security issues
- **Trivy**: Docker image vulnerabilities
- **TruffleHog**: Secrets detection
- **pip-licenses**: License compliance
- **Semgrep**: SAST analysis

**Duration**: ~5 minutes
**Reports**: GitHub Security tab, SARIF format
**Auto-uploaded**: CodeQL/SARIF results

---

## Quick Reference

| Workflow | When | Time | Status |
|----------|------|------|--------|
| test.yml | Push/PR | 5m | Must pass |
| health-check.yml | Daily 2 AM | 3m | Informational |
| code-quality.yml | PR | 3m | Must pass format |
| deploy.yml | Main push / Release | 10-15m | Staging auto, prod on release |
| security.yml | Push/PR/Daily 1 AM | 5m | Informational |

---

## Setup Instructions

### 1. GitHub Secrets Required

Add these secrets to your GitHub repository settings:

```
GOOGLE_API_KEY          # Gemini API key
GCP_SA_KEY              # Google Cloud service account JSON
GCP_PROJECT_ID          # GCP project ID
GCP_REGION              # Cloud Run region (e.g., us-central1)
STAGING_DB_SERVER       # Staging database server
PROD_DB_SERVER          # Production database server
SLACK_WEBHOOK_URL       # Slack notifications (optional)
GITHUB_TOKEN            # Auto-created, already available
```

### 2. GitHub Environments

Create two environments in Settings → Environments:

**Staging**
- Auto-deploy on main push
- No approval required

**Production**
- Deploy on release only
- Optional: require approval

### 3. Branch Protection Rules

For `main` branch, add:
- ✅ Require status checks to pass (test.yml)
- ✅ Require code quality to pass (code-quality.yml)
- ✅ Require security to pass (security.yml)
- ✅ Dismiss stale reviews when new commits pushed

### 4. Dockerfile

Ensure `Dockerfile` exists in repo root:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "bridge.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Workflow Behavior

### On Every Push to main

1. 🧪 **test.yml** runs → Must pass
2. 💎 **code-quality.yml** runs → Informational
3. 🚀 **deploy.yml** triggers → Builds and deploys to staging
4. 🔒 **security.yml** runs → Informational

### On Pull Request

1. 🧪 **test.yml** runs → Must pass
2. 💎 **code-quality.yml** runs → Posts detailed report
3. 🔒 **security.yml** runs → Posts security findings

### On Release

1. 🚀 **deploy.yml** triggers → Full build + production deployment
2. Blue-green deployment with automatic rollback

### Daily

- **2 AM UTC**: 🏥 **health-check.yml** → Health report
- **1 AM UTC**: 🔒 **security.yml** → Security scan

---

## Monitoring & Alerts

### GitHub Status Checks
- All workflow results visible on PR/commit
- Required checks must pass before merge

### Slack Notifications
- Health check: Daily results (if webhook configured)
- Deploy: Success/failure/rollback
- Security: Critical findings

### Artifacts
- Test coverage reports
- Health check results
- Security scan reports

All available in GitHub Actions → Run details → Artifacts

---

## Troubleshooting

### Tests Fail Locally But Pass in CI

Check Python version:
```bash
python --version  # Should be 3.12.x

# Install exact deps as CI
pip install -r requirements.txt
```

### Docker Build Fails in CI

Check Docker daemon:
```bash
docker ps  # Should work locally
```

### Deployment Fails

Check GCP credentials:
```bash
gcloud auth list
gcloud config get-value project
```

### Secrets Not Found

Verify in GitHub Settings:
- Settings → Secrets and variables → Actions
- All required secrets present
- No trailing whitespace

### Slack Notifications Not Working

1. Get Slack webhook: https://api.slack.com/messaging/webhooks
2. Add as `SLACK_WEBHOOK_URL` secret
3. Workflows will auto-notify

---

## Advanced: Custom Triggers

### Manually Trigger Workflow

Go to: Actions → Select workflow → "Run workflow" button

### Test PR Before Merge

Push to PR branch - workflows run automatically

### Dry-run Deployment

```bash
# Via GitHub UI
Actions → Deploy → Run workflow → staging
```

---

## Cost Considerations

### Free Tier Limits
- 2,000 minutes/month for private repos
- Current setup uses ~200-300 min/month
- Well under free tier

### To Reduce Cost
- Remove daily schedules
- Only test on main branch (not all branches)
- Skip deployment to staging

---

## Production Checklist

Before deploying to production:

- [ ] All tests passing
- [ ] Code quality checks passing
- [ ] No critical security findings
- [ ] Documentation updated
- [ ] CHANGELOG updated
- [ ] Version bumped (semantic versioning)
- [ ] Create GitHub release
- [ ] Monitor deployment in Cloud Run

---

## Files Reference

```
.github/workflows/
├── test.yml              # Test suite runner
├── health-check.yml      # Daily health checks
├── code-quality.yml      # PR code quality
├── deploy.yml            # Production deployment
├── security.yml          # Security scanning
└── README.md            # This file
```

---

## See Also

- [Project Structure](../../CLAUDE.md)
- [Deployment Guide](../../DEPLOYMENT.md)
- [Project Health Workflow](_bmad/garage/workflows/project-health/)
- [GitHub Actions Docs](https://docs.github.com/en/actions)

---

**Last Updated**: February 2024
**Status**: Production Ready ✅
