# Release Workflow

Workflow for preparing and deploying GarageAI releases.

## Overview

Safe, systematic release process for production deployments.

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ PREPARE │ → │  TEST   │ → │ DEPLOY  │ → │ VERIFY  │
└─────────┘    └─────────┘    └─────────┘    └─────────┘
```

---

## Phase 1: Prepare

**Goal**: Get the codebase ready for release.

### Steps

1. **Version Check**
   - What version are we releasing?
   - Update version in relevant files
   - Create release branch if needed

2. **Changelog**
   - List all changes since last release
   - Categorize: Features, Fixes, Breaking Changes
   - Note any migration steps

3. **Dependency Check**
   - Are all dependencies up to date?
   - Any security vulnerabilities?
   - Lock file updated?

### Checklist
- [ ] Version updated
- [ ] Changelog prepared
- [ ] Dependencies reviewed
- [ ] No uncommitted changes

---

## Phase 2: Test

**Goal**: Verify everything works before deploying.

### Steps

1. **Automated Tests**
   ```bash
   pytest tests/ -v
   ```

2. **Manual Testing**
   - Test web dashboard
   - Test voice conversation (if possible)
   - Verify database operations

3. **Integration Testing**
   - Test Twilio webhook connectivity
   - Test Gemini API integration
   - Test WinCar database queries

### Test Scenarios

| Scenario | Steps | Expected Result |
|----------|-------|-----------------|
| Web chat | Open dashboard, send message | AI responds |
| Customer lookup | Ask "who am I?" | Customer identified |
| Werkorder check | Ask about license plate | Status returned |
| Parts query | Ask about brake pads | Stock info shown |
| Appointment | Schedule an appointment | Confirmation received |

### Checklist
- [ ] All automated tests pass
- [ ] Web dashboard works
- [ ] Core voice flows work
- [ ] Database operations successful

---

## Phase 3: Deploy

**Goal**: Deploy to production safely.

### Pre-Deploy

1. **Backup** (if applicable)
   - Database backup
   - Note current working version

2. **Notify**
   - Inform stakeholders of deployment window
   - Prepare rollback plan

### Deploy Steps

**Google Cloud Run:**
```bash
# From deployment/ directory
./deploy_cloudrun.sh
```

**Docker:**
```bash
docker build -t garageai:latest .
docker push [registry]/garageai:latest
```

**Manual:**
```bash
# Pull latest code
git pull origin main

# Install dependencies
pip install -r requirements.txt

# Restart service
systemctl restart garageai
```

### Checklist
- [ ] Backup created
- [ ] Deployment command executed
- [ ] No errors in deployment logs
- [ ] Service started successfully

---

## Phase 4: Verify

**Goal**: Confirm production is working correctly.

### Steps

1. **Health Check**
   - Hit the health endpoint: `GET /`
   - Check application logs

2. **Smoke Test**
   - Open production dashboard
   - Send a test message
   - Verify AI responds

3. **Monitor**
   - Watch logs for errors
   - Check latency metrics
   - Monitor for 15-30 minutes

### Verification Checklist
- [ ] Health endpoint returns 200
- [ ] Dashboard loads correctly
- [ ] AI responds to messages
- [ ] No errors in logs
- [ ] Latency within acceptable range

---

## Rollback Plan

If something goes wrong:

1. **Identify the Issue**
   - Check logs for errors
   - Determine severity

2. **Decide: Fix Forward or Rollback**
   - Minor issue → Fix forward
   - Major issue → Rollback

3. **Rollback Steps**
   ```bash
   # Cloud Run: Revert to previous revision
   gcloud run services update-traffic garageai \
     --to-revisions=[previous-revision]=100

   # Docker: Deploy previous tag
   docker pull [registry]/garageai:[previous-tag]
   docker-compose up -d

   # Manual: Checkout previous version
   git checkout [previous-tag]
   pip install -r requirements.txt
   systemctl restart garageai
   ```

4. **Post-Mortem**
   - Document what went wrong
   - Plan fix for next release

---

## Release Notes Template

```markdown
# GarageAI v[X.Y.Z] Release Notes

**Release Date**: YYYY-MM-DD

## New Features
- Feature 1: Description
- Feature 2: Description

## Bug Fixes
- Fixed: Description of bug fixed

## Improvements
- Improvement 1: Description

## Breaking Changes
- None / List any breaking changes

## Migration Steps
- None / List any required migration steps

## Known Issues
- None / List any known issues
```

---

## Quick Start

```
You: Let's prepare a release

BMAD: I'll guide you through the release process.

      First, let's prepare:
      1. What version are we releasing?
      2. Let me check for uncommitted changes...
      3. Let me run the test suite...
```

## Workflow Commands

- `next` - Move to next phase
- `status` - Show release progress
- `rollback` - Initiate rollback
- `abort` - Abort release process
