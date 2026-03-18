---
name: SKILL_NAME
description: >
  TRIGGER_DESCRIPTION. Use when USER_CONTEXT. Covers CAPABILITIES.
---

# SKILL_NAME

## Inputs
- `required_input`: DESCRIPTION
- `optional_input` (optional): DESCRIPTION

<!-- Optional: uncomment if the skill requires user-specific settings.
## Configuration
On first invocation, if `config.json` is missing, prompt the user for:
- `setting_name`: DESCRIPTION
Store in `config.json` (gitignored). No secrets — use environment variables.
-->

## Procedure

Step 1: Gather context.
  - Read RELEVANT_CONFIG_FILES
  - Record constraints for subsequent steps

Step 2: PRIMARY_ACTION.
  - IMPERATIVE_INSTRUCTION
  - If CONDITION → BRANCH_A. Otherwise → BRANCH_B.
  - Note: EDGE_CASE_CONTEXT — explains why this matters for correct results.

Step 3: Verify output.
  - Check each item in the Output Contract
  - If any check fails → fix and re-verify

## Output Format

```json
{
  "result": "EXAMPLE_VALUE",
  "confidence": "high|medium|low",
  "details": []
}
```

<!-- Optional: uncomment if the skill registers session hooks.
## Session Hooks
hooks:
  - event: PreToolUse
    matcher: "ToolName"
    script: scripts/guard.sh
Hooks activate on skill invocation and persist for the session.
Platform-specific (Claude Code). For cross-platform, note as optional.
-->

## References
| File | Load When | Contains |
|------|-----------|----------|
| `references/CHECKLIST.md` | Step 2 if CONDITION | Detailed checklist for X |
