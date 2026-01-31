---
description: 'Start the Code Review workflow'
---

# Code Review Workflow

You are starting the **Code Review Workflow** for GarageAI.

## Overview

Comprehensive multi-faceted code review:

```
STRUCTURE → LOGIC → SECURITY → LATENCY
```

## Activation

1. Load the configuration from `_bmad/core/config.yaml`
2. Load the workflow from `_bmad/garage/workflows/code-review/workflow.md`
3. Follow the workflow instructions exactly

## Review Facets

1. **Structure & Style** - Code organization and conventions
2. **Logic & Correctness** - Does it work correctly?
3. **Security** - Input validation, SQL injection, secrets
4. **Latency & Performance** - Impact on voice response time
5. **Testing** - Test coverage and quality
6. **GarageAI-Specific** - Twilio/Gemini/WinCar concerns

## Start

Read and follow the instructions in `_bmad/garage/workflows/code-review/workflow.md`.
