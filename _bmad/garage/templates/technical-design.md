# Technical Design: [Feature Name]

**Date**: YYYY-MM-DD
**Author**: [Name]
**Status**: Draft | In Review | Approved
**Related Brief**: [Link to feature brief]

---

## Overview

### Summary
[One paragraph describing the technical approach]

### Goals
- Goal 1
- Goal 2

### Non-Goals
- Non-goal 1 (why)

---

## Architecture

### Component Diagram

```
[ASCII diagram showing component interactions]

Example:
┌─────────┐     ┌─────────┐     ┌─────────┐
│ Client  │ ──▶ │   API   │ ──▶ │   DB    │
└─────────┘     └─────────┘     └─────────┘
```

### Data Flow

```
1. User action
2. → Component A processes
3. → Component B stores
4. → Response returned
```

---

## Detailed Design

### Component Changes

#### `app/tools.py`
```python
# New tool to be added
@tool("new_tool_name")
def new_tool_name(param: str) -> str:
    """Description"""
    # Implementation notes
    pass
```

#### `bridge/api.py`
```python
# New endpoint
@app.get("/api/new_endpoint")
async def new_endpoint():
    # Implementation notes
    pass
```

#### `bridge/telephony.py`
```python
# New message handler
if msg_type == "new_type":
    # Implementation notes
    pass
```

### Database Changes

```sql
-- New table (if any)
CREATE TABLE NewTable (
    ID INT PRIMARY KEY,
    Column1 VARCHAR(100),
    ...
);

-- New queries
SELECT ... FROM ... WHERE ...
```

### API Changes

| Endpoint | Method | Request | Response |
|----------|--------|---------|----------|
| `/api/new` | GET | `{param: string}` | `{result: string}` |

### WebSocket Messages

| Type | Direction | Payload |
|------|-----------|---------|
| `new_request` | Client → Server | `{data: ...}` |
| `new_response` | Server → Client | `{result: ...}` |

---

## Latency Analysis

### Current Latency Budget
- Total: 800ms
- Network: ~200ms
- Gemini: ~400ms
- Our code: ~200ms

### Impact of This Change
- Additional latency: [X]ms
- Reason: [explanation]
- Mitigation: [if needed]

---

## Error Handling

| Error Scenario | Handling | User Message |
|----------------|----------|--------------|
| Database unavailable | Retry 3x, then fail | "Sorry, ik kan nu niet bij de gegevens." |
| Invalid input | Return error | "Ik begrijp dat niet. Kunt u het herhalen?" |
| Timeout | Cancel operation | "Dat duurt te lang. Probeer het later." |

---

## Security Considerations

- [ ] Input validation implemented
- [ ] SQL injection prevented
- [ ] No sensitive data logged
- [ ] Authentication required (if applicable)

---

## Testing Strategy

### Unit Tests
- Test 1: [description]
- Test 2: [description]

### Integration Tests
- Test 1: [description]

### Manual Tests
- [ ] Test via web dashboard
- [ ] Test via Twilio call (if applicable)

---

## Rollout Plan

1. **Phase 1**: Deploy to staging
2. **Phase 2**: Test with subset of calls
3. **Phase 3**: Full rollout

### Rollback Plan
[How to revert if issues occur]

---

## Open Questions

1. [Question 1]
2. [Question 2]

---

## Decision Log

| Decision | Rationale | Date |
|----------|-----------|------|
| [Decision 1] | [Why] | YYYY-MM-DD |
| [Decision 2] | [Why] | YYYY-MM-DD |
