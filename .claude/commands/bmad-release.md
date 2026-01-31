---
description: 'Start the Release workflow for deployment'
---

# Release Workflow

You are starting the **Release Workflow** for GarageAI.

## Overview

Safe, systematic release process:

```
PREPARE → TEST → DEPLOY → VERIFY
```

## Activation

1. Load the configuration from `_bmad/core/config.yaml`
2. Load the workflow from `_bmad/garage/workflows/release/workflow.md`
3. Follow the workflow instructions exactly

## Workflow Phases

1. **Prepare** - Version, changelog, dependency check
2. **Test** - Automated and manual testing
3. **Deploy** - Execute deployment
4. **Verify** - Confirm production is working

## Deployment Targets

- Google Cloud Run
- Docker
- Manual deployment

## Start

Read and follow the instructions in `_bmad/garage/workflows/release/workflow.md`.
