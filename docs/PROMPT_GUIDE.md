# AI Master Prompt & Behavior Guide

This guide explains how to modify the AI's personality, rules, and "hardcoded" behaviors.

## 📍 Where is the System Prompt?

The "Master Prompt" (System Prompt) is located in:
**`graph.py`** -> variable `SYSTEM_PROMPT`.

This text block defines everything about the AI: who it is, what tools it has, how it should speak, and what rules it must follow.

## ✏️ How to Edit the Prompt

 To change the AI's behavior, simply edit the string in `SYSTEM_PROMPT`.

### Example: Changing the Personality
Current:
```python
PERSONA:
- Helpful, knowledgeable, safety-conscious, and friendly.
```

Change to:
```python
PERSONA:
- Use a formal, technical tone.
- Address the user as "Sir" or "CDM".
```

## 🚨 Adding "Hardcoded" Cases

"Hardcoded" cases in LLMs are best implemented as **specific instructions** or **situational rules** within the prompt.

### Example: Handling "Weird Smell" (Emergency Logic)

If you want the AI to react in a specific way to certain keywords (like "burning smell"), add a **CRITICAL SAFETY RULES** section to the prompt:

```markdown
CRITICAL SAFETY RULES:
- If the user mentions a "burning smell", "smoke", "brakes failing", or "warning light flashing red", STOP immediately.
- Tell them this sounds like an EMERGENCY.
- Advise them to stop the car safely and call roadside assistance or 112 if necessary.
- Do NOT try to upsell or book an appointment until safety is addressed.
```

**Why do it this way?**
Implementing this in Python code (e.g., `if "smell" in user_input`) is brittle and hard to maintain handling synonyms ("it stinks", "odor", "smoke"). The LLM is smart enough to understand the *intent* and follow the rule across various phrasings.

### Validating Inputs (Phone Numbers)

To ensure the AI handles specific formats (like "0 6 1 2..." with spaces), explicitly tell it in the prompt:

```markdown
3. IDENTIFY CUSTOMER (Contextual):
   - When you ask for a phone number, ALWAYS accept numbers even if they are spoken with spaces (e.g., "0 6 1 2...").
   - Do not ask the user to repeat it just because of spaces; the tool handles it.
```

## 🧠 Advanced: Conditional Logic in Python

For extremely strict logic that *must* happen (e.g., "If user says 'banana', shut down server"), you would modify the **Graph Logic** in `graph.py` or the specific Tool in `tools.py`, not just the prompt.

**Example: Force Identify Tool**
In `tools.py`, the `identify_customer` function now aggressively strips non-digits to handle the "spoken spaces" issue:

```python
clean_phone = re.sub(r'[^0-9+]', '', phone_number)
```

This ensures that even if the LLM passes "0 6 1 2", the tool sees "0612" and finds the customer.
