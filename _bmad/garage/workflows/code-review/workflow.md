# Code Review Workflow

Comprehensive code review for GarageAI changes.

## Overview

Multi-faceted review ensuring code quality, correctness, and maintainability.

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│STRUCTURE│ → │ LOGIC   │ → │SECURITY │ → │LATENCY  │
└─────────┘    └─────────┘    └─────────┘    └─────────┘
```

---

## Review Facets

### 1. Structure & Style

**Questions to ask:**
- Does the code follow existing patterns?
- Are files in the right locations?
- Is naming consistent with the codebase?
- Are there type hints?

**Checklist:**
- [ ] Follows project structure conventions
- [ ] Naming is clear and consistent
- [ ] Type hints present on functions
- [ ] Docstrings on public functions
- [ ] No commented-out code
- [ ] Import organization

### 2. Logic & Correctness

**Questions to ask:**
- Does the code do what it's supposed to do?
- Are edge cases handled?
- What happens with invalid input?
- Are there off-by-one errors?

**Checklist:**
- [ ] Logic matches requirements
- [ ] Edge cases handled (empty, null, etc.)
- [ ] Error handling present
- [ ] No hardcoded magic values
- [ ] Correct use of async/await

### 3. Security

**Questions to ask:**
- Is user input validated?
- Are SQL queries parameterized?
- Are secrets hardcoded?
- Is sensitive data logged?

**Checklist:**
- [ ] SQL injection prevented (parameterized queries)
- [ ] No hardcoded secrets/credentials
- [ ] Input validation present
- [ ] No sensitive data in logs
- [ ] Authentication checked where needed

### 4. Latency & Performance

**Questions to ask:**
- Does this add latency to the voice path?
- Are database queries optimized?
- Are there unnecessary network calls?
- Could this cause memory issues?

**Checklist:**
- [ ] Database queries are efficient (indexes used)
- [ ] No N+1 query patterns
- [ ] Connections properly closed
- [ ] No blocking calls in async functions
- [ ] Reasonable memory usage

### 5. Testing

**Questions to ask:**
- Are there tests for the new code?
- Do tests cover error cases?
- Are tests meaningful or just for coverage?
- Do all tests pass?

**Checklist:**
- [ ] Unit tests for new functions
- [ ] Error cases tested
- [ ] Tests are readable and maintainable
- [ ] All tests pass
- [ ] No flaky tests introduced

### 6. GarageAI-Specific

**Questions to ask:**
- Does this work with Twilio AND web client?
- Are Dutch user-facing strings correct?
- Is the latency budget preserved?
- Does it work with the LangGraph agent flow?

**Checklist:**
- [ ] Works with both Twilio (8kHz) and Web (16kHz) paths
- [ ] Dutch strings are correct for customer-facing text
- [ ] Latency impact acceptable (<200ms for our code)
- [ ] Tool functions return AI-friendly strings
- [ ] WebSocket messages properly formatted

---

## Review Process

### Step 1: Understand the Change

```
What was changed?
- List files modified
- Understand the purpose
- Read any related issue/story
```

### Step 2: Review Each Facet

Go through each of the 6 facets above.

### Step 3: Summarize Findings

```markdown
## Code Review Summary

### Changes Reviewed
- [List of files]

### Findings

#### Must Fix (Blocking)
- [ ] Issue 1 - reason
- [ ] Issue 2 - reason

#### Should Fix (Non-blocking)
- [ ] Issue 1 - reason

#### Nice to Have
- [ ] Suggestion 1

### Verdict
[ ] Approved
[ ] Approved with comments
[ ] Changes requested
```

---

## Quick Start

```
You: Review my changes to [files/branch]

BMAD: I'll review this across 6 facets:
      1. Structure & Style
      2. Logic & Correctness
      3. Security
      4. Latency & Performance
      5. Testing
      6. GarageAI-Specific

      Let me start by looking at the changes...
```

## Workflow Commands

- `focus [facet]` - Focus on specific facet
- `summarize` - Show summary of findings
- `approve` - Mark as approved
- `exit` - Exit review
