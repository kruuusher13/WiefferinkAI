# Bug Fix Workflow

A streamlined workflow for fixing bugs in GarageAI.

## Overview

Fast, focused bug resolution with proper verification.

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│REPRODUCE│ → │ LOCATE  │ → │   FIX   │ → │ VERIFY  │
└─────────┘    └─────────┘    └─────────┘    └─────────┘
```

---

## Phase 1: Reproduce

**Goal**: Confirm the bug and understand when it occurs.

### Steps

1. **Get Bug Details**
   - What's the expected behavior?
   - What's the actual behavior?
   - Steps to reproduce?

2. **Reproduce Locally**
   - Follow the reproduction steps
   - Note any error messages
   - Check logs for additional context

3. **Document Environment**
   - Which path? (Twilio vs Web)
   - Browser/device if frontend
   - Any specific data conditions?

### Checklist
- [ ] Bug reproduced locally
- [ ] Error message captured
- [ ] Reproduction steps documented

---

## Phase 2: Locate

**Goal**: Find the root cause in the code.

### Steps

1. **Identify Component**
   - Where in the architecture does this occur?
   - `app/` (agent logic), `bridge/` (API/telephony), or `web_test/` (frontend)?

2. **Trace the Code Path**
   - Follow the data/request flow
   - Add temporary logging if needed
   - Check recent changes (git log)

3. **Root Cause Analysis**
   - Why is this happening?
   - Is it a logic error, data issue, or integration problem?
   - Are there related bugs?

### Common Bug Locations

| Symptom | Likely Location |
|---------|-----------------|
| Audio issues | `bridge/audio.py` |
| Tool not working | `app/tools.py` |
| WebSocket errors | `bridge/telephony.py` |
| API errors | `bridge/api.py` |
| Wrong AI response | `app/graph.py` (prompt) |
| Database errors | `app/tools.py` (queries) |
| Frontend issues | `web_test/static/client.js` |

---

## Phase 3: Fix

**Goal**: Implement the minimal fix.

### Steps

1. **Plan the Fix**
   - What's the smallest change that fixes the bug?
   - Are there side effects to consider?
   - Should we fix the symptom or the root cause?

2. **Implement**
   - Make the fix
   - Follow existing code patterns
   - Add comments explaining the fix if non-obvious

3. **Write Regression Test**
   - Create a test that would have caught this bug
   - Test should fail before fix, pass after

### Fix Guidelines
- Prefer targeted fixes over refactoring
- Don't fix unrelated issues in the same change
- If the fix is complex, discuss before implementing

---

## Phase 4: Verify

**Goal**: Confirm the fix works and doesn't break anything.

### Steps

1. **Run Test Suite**
   ```bash
   pytest tests/
   ```

2. **Manual Verification**
   - Follow original reproduction steps
   - Confirm bug is fixed
   - Test related functionality

3. **Edge Cases**
   - What if input is empty?
   - What if database is slow?
   - What if network fails?

### Verification Checklist
- [ ] All tests pass
- [ ] Bug no longer reproduces
- [ ] No new issues introduced
- [ ] Regression test added

---

## Quick Start

```
You: There's a bug - [description]

BMAD: Let's fix this. First, can you help me reproduce it?
      1. What's the expected behavior?
      2. What's actually happening?
      3. How do I reproduce it?
```

## Workflow Commands

- `next` - Move to next phase
- `status` - Show current progress
- `skip fix` - Skip to fix if cause is obvious
- `exit` - Exit workflow
