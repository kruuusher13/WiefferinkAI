# GitHub Actions Workflows Summary

Complete overview of all automated workflows for GarageAI.

---

## 🎯 Overview

5 comprehensive workflows automate testing, deployment, and security for GarageAI:

```
Push/PR to main/develop
        ↓
   ┌────┴────┐
   ↓         ↓
test ←→ code-quality → health-check → security
   ↓
deploy → slack
   ↓
production
```

---

## Workflow Timeline

### On Every Push to Main

```
0s        test.yml starts
├─ Run pytest, coverage check
├─ Check code formatting
└─ 5 min: ✅ PASS

0s        code-quality.yml starts (parallel)
├─ Detailed linting & analysis
└─ 3 min: ✅ PASS

0s        security.yml starts (parallel)
├─ Scan for vulnerabilities
└─ 5 min: ✅ PASS

5s        health-check.yml starts
├─ Full health check (test + docs + optimize)
└─ 3 min: ✅ PASS

5s        deploy.yml starts (after tests pass)
├─ Build Docker image
├─ Push to GHCR
├─ Deploy to staging
├─ Health check staging
└─ 10 min: ✅ DEPLOYED

0s        Slack notification: ✅ All done!
```

### On Pull Request

```
0s        test.yml starts
├─ Run all tests
├─ Check coverage
└─ 5 min: ✅ PASS/FAIL

0s        code-quality.yml starts
├─ Lint & analyze
├─ Comment on PR with report
└─ 3 min: ✅ PASS

0s        security.yml starts
├─ Scan for issues
└─ 5 min: ✅ PASS

Result: PR shows ✅ all checks pass (can merge)
        or ❌ failures (must fix)
```

### On Release

```
1. Create release on GitHub
2. deploy.yml triggers
   ├─ Build image
   ├─ Test
   ├─ Deploy to staging
   ├─ Deploy to production
   │  ├─ Blue-green deployment
   │  ├─ Health check
   │  └─ Auto-rollback if fails
   └─ Slack notification
3. Production live! 🚀
```

### On Schedule

```
Daily 2 AM: health-check.yml
  ├─ Test
  ├─ Docs verification
  ├─ Code optimization
  └─ Slack notification

Daily 1 AM: security.yml
  ├─ Dependency audit
  ├─ Code scanning
  ├─ Container scan
  ├─ Secrets check
  └─ License audit
```

---

## Workflow Details

### 1️⃣ test.yml - Test Suite

**When**: Push/PR, every commit

**What it does**:
```
Python 3.12 setup
    ↓
Install dependencies
    ↓
Start SQL Server container
    ↓
Initialize test database
    ↓
Run pytest (all tests)
    ├─ Unit tests
    ├─ Integration tests
    ├─ Tool tests
    └─ API tests
    ↓
Check coverage (min 80%)
    ↓
Upload coverage report
    ↓
Check formatting (black)
    ↓
Lint (pylint, flake8)
    ↓
Type check (mypy)
```

**Time**: ~5 minutes
**Status**: 🔴 **REQUIRED** - PR cannot merge without passing
**Artifacts**: Coverage reports, HTML coverage

**Example Output**:
```
✅ Test session started
✅ 47 tests passed
✅ Coverage: 82%
✅ Black: OK
✅ Pylint: 9.5/10
✅ Mypy: OK
```

---

### 2️⃣ code-quality.yml - PR Quality Check

**When**: Pull Request only

**What it does**:
```
Check code formatting (black)
    ↓
Lint with pylint
    ↓
Lint with flake8
    ↓
Type check (mypy)
    ↓
Security scan (bandit)
    ↓
Code complexity analysis
    ↓
Dead code detection
    ↓
Dependency audit
    ↓
Comment on PR with report
```

**Time**: ~3 minutes
**Status**: 🟡 **BLOCKS MERGE** if formatting fails
**Comments**: Posts detailed quality report on PR

**Example Output**:
```
## 📊 Code Quality Report

| Check | Status |
|-------|--------|
| 🎨 Formatting | ✅ PASS |
| 📝 Linting | ✅ OK |
| 🔍 Types | ✅ OK |
| 🔒 Security | ✅ OK |

💡 Fix with: black . && pylint app/
```

---

### 3️⃣ health-check.yml - Daily Health Check

**When**: Daily 2 AM UTC, Manual trigger

**What it does**:
```
Setup environment
    ↓
Start SQL Server
    ↓
4 parallel tasks:
├─ 🧪 Test phase: Run all tests, check coverage
├─ 📚 Docs phase: Verify all docs exist/current
├─ ✨ Optimize: Check code quality, linting
└─ 📤 Git phase: Repository status check
    ↓
Generate summary report
    ↓
Upload artifacts
    ↓
Slack notification (if configured)
```

**Time**: ~3 minutes
**Status**: 🟢 **INFORMATIONAL** - doesn't block anything
**Reports**: `_bmad/_output/health-*.md`
**Notifications**: Slack success/failure

**Example Output**:
```
✅ Testing: 47 passed, 0 failed (82% coverage)
✅ Documentation: 5 files verified, 0 broken links
✅ Optimization: Code clean, no issues
✅ Git Status: Working directory clean
```

---

### 4️⃣ deploy.yml - Production Deployment

**When**: Push to main (staging only), Release (production)

**What it does**:

**Build Phase**:
```
Checkout code
    ↓
Setup gcloud
    ↓
Build Docker image
    ├─ From Dockerfile
    ├─ Multi-stage build
    └─ Push to GHCR
```

**Test Phase**:
```
Run full test suite
    ↓
Run deployment-specific tests
    ↓
Performance baseline
    ↓
Verify image health
```

**Staging Deployment** (automatic on main push):
```
Deploy to Cloud Run (staging)
    ↓
Wait for health
    ↓
Health check: GET /api/health
    ├─ Retry 5 times
    └─ Fail if unhealthy
    ↓
Smoke tests
    ↓
Slack notification
```

**Production Deployment** (on release only):
```
Blue-green deployment
├─ Deploy to "green" instance
├─ Health check green
├─ Smoke tests on green
├─ Monitor for 1 minute
├─ Route traffic to green
└─ Monitor for errors
    ↓
Auto-rollback if fails
    ├─ Revert traffic to blue
    └─ Slack notification
```

**Time**:
- Build: ~3 min
- Test: ~2 min
- Staging: ~2 min
- Production: ~5 min

**Status**: 🟢 **AUTOMATIC** (staging), 🟡 **REQUIRES APPROVAL** (prod)
**Notifications**: Slack deployment status

**Example Output**:
```
📦 Building image...
✅ Image built and pushed
🧪 Running tests...
✅ All tests passed
📤 Deploying to staging...
✅ Deployment healthy
🚀 Staging updated!
```

---

### 5️⃣ security.yml - Security Scanning

**When**: Push/PR, Daily 1 AM UTC

**What it does**:

**Dependency Audit**:
```
pip-audit: Check for known vulnerabilities
    ↓
safety: Secondary check
    ↓
Report any CVEs
```

**Code Scanning**:
```
Bandit: Python security issues
    ↓
Convert to SARIF
    ↓
Upload to GitHub Code Scanning
```

**Container Scanning**:
```
Build image
    ↓
Trivy: Scan image for vulnerabilities
    ↓
Report any issues
```

**Secrets Detection**:
```
TruffleHog: Scan for secrets
    ↓
Check for API keys, credentials, tokens
    ↓
Block if found
```

**License Compliance**:
```
pip-licenses: List all dependency licenses
    ↓
Flag GPL/AGPL (if commercial use)
    ↓
Report
```

**SAST Analysis**:
```
Semgrep: Code pattern analysis
    ↓
Detect common vulnerabilities
    ↓
Report
```

**Time**: ~5 minutes
**Status**: 🟢 **INFORMATIONAL** - doesn't block
**Reports**: GitHub Security tab, SARIF format

**Example Output**:
```
✅ Dependencies: 0 critical vulnerabilities
✅ Code: No security issues found
✅ Container: 1 medium issue (non-critical)
✅ Secrets: None detected
✅ Licenses: MIT, Apache-2.0 OK
✅ SAST: No issues found
```

---

## Event-Driven Workflow Map

```
EVENT                           WORKFLOWS TRIGGERED
─────────────────────────────────────────────────────────────
Push to feature branch
  └─ (nothing triggered)

Pull Request to main/develop
  ├─ test.yml (required)
  ├─ code-quality.yml (comment)
  └─ security.yml (report)

Commit/PR approval + merge
  └─ PR automatically closes

Push to main branch
  ├─ test.yml (required)
  ├─ code-quality.yml
  ├─ security.yml
  ├─ health-check.yml
  └─ deploy.yml → staging (automatic)

Release published
  └─ deploy.yml → production (with approval)

Manual workflow dispatch
  ├─ health-check.yml (manual button)
  └─ deploy.yml (manual button)

Schedule (daily)
  ├─ 1 AM: security.yml
  └─ 2 AM: health-check.yml
```

---

## Status Indicators

### Workflow Status Badge (in README)

```markdown
![Tests](https://github.com/hornet/GarageAI/workflows/Tests/badge.svg)
![Deploy](https://github.com/hornet/GarageAI/workflows/Deploy/badge.svg)
![Security](https://github.com/hornet/GarageAI/workflows/Security%20Scanning/badge.svg)
```

### PR Status Checks

```
✅ test / test (Pass)
✅ code-quality / quality (Pass)
✅ security / dependencies (Pass)
✅ security / code-scanning (Pass)
  → All checks passed - ready to merge
```

---

## Branch Protection Rules

All enforced on `main` branch:

```
✅ Require pull request before merging
   └─ Require 1 approval from code owners

✅ Require status checks to pass
   ├─ test / test
   ├─ code-quality / quality
   ├─ security / dependencies
   └─ security / code-scanning

✅ Require branches to be up to date
   └─ Can't merge if main moved forward

✅ Require code owners review
   └─ CODEOWNERS file must approve

✅ Dismiss stale reviews
   └─ New commits invalidate old reviews
```

---

## Integration Points

### GitHub
- Status checks on PR
- Security tab scanning results
- Deployments tab history
- Actions tab logs

### Google Cloud
- Docker image stored in GHCR
- Deployed to Cloud Run
- Staging & Production instances

### Slack (optional)
- Health check results
- Deployment success/failure
- Security findings
- Rollback notifications

### Email (GitHub default)
- Workflow failures
- Security alerts
- Deployment notifications

---

## Cost Estimation

### GitHub Actions Minutes (free tier: 2,000/month)

```
test.yml:           5 min × 10 runs/day × 30 days = 1,500 min
code-quality.yml:   3 min × 3 PRs/day × 30 days   = 270 min
health-check.yml:   3 min × 1 run/day × 30 days   = 90 min
security.yml:       5 min × 1 run/day × 30 days   = 150 min
deploy.yml:         10 min × 3 deploys/month      = 30 min
────────────────────────────────────────────────────────────
Total:                                              2,040 min
```

**Result**: ✅ Slightly over free tier (~40 min/month extra) = **~$0.24/month**

---

## Troubleshooting Decision Tree

```
Workflow failed?
├─ Status red ❌
│  ├─ test.yml failed?
│  │  ├─ Check Python version
│  │  ├─ Run tests locally
│  │  └─ Check database
│  │
│  ├─ code-quality.yml failed?
│  │  ├─ Run: black . && pylint app/
│  │  ├─ Fix formatting issues
│  │  └─ Commit & push
│  │
│  ├─ deploy.yml failed?
│  │  ├─ Check secrets configured
│  │  ├─ Verify GCP credentials
│  │  └─ Check Cloud Run quota
│  │
│  └─ security.yml failed?
│     ├─ Check dependencies: pip-audit
│     ├─ Update vulnerable packages
│     └─ Review findings
│
├─ Workflow stuck ⏳
│  ├─ Check Actions tab
│  ├─ Click job to see logs
│  └─ Manual re-run if needed
│
└─ Secrets not found?
   ├─ Verify in Settings
   ├─ Check spelling (case-sensitive)
   └─ Re-add if needed
```

---

## Quick Commands

### View all workflows
```bash
gh workflow list
```

### View workflow runs
```bash
gh workflow view test.yml -r 5
```

### Trigger manually
```bash
gh workflow run health-check.yml
gh workflow run deploy.yml -f environment=staging
```

### View logs
```bash
gh run view [RUN_ID] --log
```

### List secrets
```bash
gh secret list
```

---

## Monitoring Dashboard

**GitHub UI**:
- Actions → All workflows
- Security → Code scanning
- Deployments → History
- Issues → Check for errors

**Slack** (if configured):
- #deployments channel
- Health check daily results
- Deploy notifications

**Google Cloud**:
- Cloud Run → Instances
- Logs → Execution logs
- Monitoring → Error rates

---

## Next Steps

1. **Complete Setup**: Follow `GITHUB_ACTIONS_SETUP.md`
2. **Test Workflows**: Push to develop branch
3. **Verify PR Checks**: Create test pull request
4. **Deploy Staging**: Merge to main
5. **Deploy Production**: Create release
6. **Monitor**: Check GitHub Security tab

---

## Reference

- **Setup Guide**: `GITHUB_ACTIONS_SETUP.md`
- **Workflows Directory**: `.github/workflows/`
- **GitHub Docs**: https://docs.github.com/en/actions
- **GCP Cloud Run**: https://cloud.google.com/run/docs

---

**Status**: ✅ All workflows production-ready

**Last Updated**: February 2024
