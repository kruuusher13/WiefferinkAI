# Feature Development Workflow

A structured workflow for developing new features in GarageAI.

## Overview

This workflow guides you through the complete feature development process, from requirements to deployment.

## Phases

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ DISCOVER│ → │ DESIGN  │ → │  BUILD  │ → │ REVIEW  │
└─────────┘    └─────────┘    └─────────┘    └─────────┘
```

---

## Phase 1: Discovery

**Agent**: Jan (Product Manager)

### Steps

1. **Define the Problem**
   - What problem does this feature solve?
   - Who is affected? (Customer, staff, owner)
   - What's the impact of NOT solving it?

2. **Gather Requirements**
   - User stories with acceptance criteria
   - Edge cases and error scenarios
   - Non-functional requirements (latency, etc.)

3. **Scope the Work**
   - What's in scope?
   - What's explicitly out of scope?
   - Dependencies on other systems?

### Output
Create: `_bmad/_output/features/[feature-name]/brief.md`

---

## Phase 2: Design

**Agent**: Willem (Architect)

### Steps

1. **Technical Analysis**
   - Which components are affected?
   - What's the data flow?
   - Are there new database tables/queries?

2. **Architecture Decision**
   - Document key decisions (ADRs)
   - Consider latency impact
   - Plan for error handling

3. **API/Interface Design**
   - New endpoints needed?
   - WebSocket message types?
   - Tool function signatures?

### Output
Create: `_bmad/_output/features/[feature-name]/design.md`

---

## Phase 3: Build

**Agent**: Sophie (Developer)

### Steps

1. **Setup**
   - Create feature branch
   - Review existing patterns in codebase

2. **Implementation**
   - Follow the design document
   - Write code following existing patterns
   - Add type hints and docstrings

3. **Testing**
   - Write unit tests first (TDD)
   - Ensure all tests pass
   - Manual testing for voice/UI features

### Output
- Code changes in feature branch
- Test files in `tests/`

---

## Phase 4: Review

**Agent**: Sophie (Developer) or peer

### Steps

1. **Code Review Checklist**
   - [ ] Follows existing patterns
   - [ ] Type hints present
   - [ ] Tests cover happy path and errors
   - [ ] No hardcoded secrets
   - [ ] Error handling in place

2. **Integration Testing**
   - Test with real Twilio call (if telephony)
   - Test web dashboard (if frontend)
   - Verify database operations

3. **Documentation**
   - Update README if needed
   - Add to API_REFERENCE.md if new endpoints
   - Document in code (docstrings)

### Output
- Approved PR ready to merge
- Updated documentation

---

## Quick Start

To begin this workflow:

```
You: I want to add [feature]

BMAD: Let's start with Discovery. I'll switch to Jan (PM).

Jan: Great! Let's understand this feature...
     1. What problem does this solve?
     2. Who will use it?
     ...
```

## Workflow Commands

- `next` - Move to next phase
- `back` - Return to previous phase
- `status` - Show current progress
- `skip` - Skip to specific phase (with justification)
- `exit` - Exit workflow (progress saved)
