# Claude Code Prompt: Audit & Refactor Existing Skills for Compliance

## Objective

Audit all Claude Code custom skills in this project (and optionally in `~/.claude/`) against the Skill Authoring Standard. Produce a compliance report, then refactor non-compliant skills to meet the token budgets and structural requirements.

---

## Step 1: Locate All Skills

Scan for SKILL.md files in these locations (check each, skip if not present):

1. `.claude/skills/` — project-level skills
2. `~/.claude/skills/` — user-level skills (only if I confirm you should audit these)
3. Any other skill directories referenced in `.claude/CLAUDE.md` or `CLAUDE.md`

For each SKILL.md found, record:
- Full file path
- Whether it's a coordinator (has a `skills/` subdirectory with child SKILL.md files) or standalone
- Word count
- Estimated token count (words × 1.33)

Also scan for reference files (`references/*.md`) associated with each skill.

**Present the inventory to me before proceeding to the audit.**

---

## Step 2: Compliance Audit

For each file in the inventory, check against these criteria:

### Token Budget Checks

| File Type | Max Words | Max Tokens |
|-----------|-----------|------------|
| Coordinator SKILL.md | 600 | 800 |
| Specialist / Standalone SKILL.md | 1,500 | 2,000 |
| Reference file | 1,100 | 1,500 |

Flag any file exceeding its budget with the overage amount.

### Structural Checks

For **coordinator** SKILL.md files, verify it contains ONLY:
- [ ] Purpose statement (one sentence)
- [ ] Classification / routing logic
- [ ] Skill registry table
- [ ] Load-then-execute directive
- [ ] Handoff protocol

Flag if it contains: detailed procedures, checklists, output format specs, examples, or explanatory prose that belongs in a specialist skill.

For **specialist / standalone** SKILL.md files:
- [ ] Procedure steps use imperative sentences
- [ ] Decision points are inline conditionals (not nested sub-sections)
- [ ] No explanatory "why" prose in the procedure section
- [ ] Output format shown as one compact example (not schema + example)
- [ ] Checklists with >10 items are in reference files, not inline
- [ ] References section lists files by path with loading conditions
- [ ] No cross-references to other specialist skills

For **reference** files:
- [ ] Pure content (no preamble, meta-instructions, or conclusions)
- [ ] Items are one line each
- [ ] Organized under category headers

### Suite-Level Checks

For skill suites (coordinator + specialists):
- [ ] Worst-case load (coordinator + largest specialist + largest reference) ≤5,000 tokens
- [ ] Eval cases are outside skill directories
- [ ] No specialist skill loads another specialist's content
- [ ] Handoff protocol defines structured data format (not raw file passing)

---

## Step 3: Produce the Audit Report

Output a report in this format:

```markdown
# Skill Compliance Audit Report

## Summary
- Skills audited: [count]
- Compliant: [count]
- Non-compliant: [count]
- Total estimated token footprint (worst-case): [tokens]

## Inventory

| # | Skill | Type | File | Words | Tokens (est) | Budget | Status |
|---|-------|------|------|-------|--------------|--------|--------|
| 1 | frontend-qa | coordinator | .claude/skills/frontend-qa/SKILL.md | 423 | 563 | 800 | ✅ |
| 2 | ui-bug-investigator | specialist | .claude/skills/.../SKILL.md | 1,847 | 2,457 | 2,000 | ❌ +457 |
| ... | | | | | | | |

## Non-Compliant Files

### [file path]
**Budget**: [over by X tokens]
**Structural issues**:
- [specific issue, e.g., "40-item diagnostic checklist inline — should be in reference file"]
- [specific issue]
**Recommended refactoring**:
- [specific action, e.g., "Extract lines 45-90 to references/rendering-checklist.md"]
- [specific action]
**Estimated savings**: [tokens]

### [next file...]
```

**Present the audit report to me and wait for approval before refactoring.**

---

## Step 4: Refactor (After Approval)

For each non-compliant file, apply refactoring patterns in this order:

1. **Extract checklists** — Move inline lists >10 items to `references/[name].md`. Replace with a load instruction in the procedure.

2. **Kill prose** — Convert explanatory paragraphs to imperative steps. Preserve critical context as one-line "Note:" annotations. Remove all "why" explanations, background sections, and hedging language.

3. **Deduplicate output specs** — If both a schema description and an example exist, keep only the example with inline annotations.

4. **Script mechanical work** — If the procedure describes deterministic file operations in natural language, offer to write a script. The procedure step becomes a script invocation.

5. **Decompose if needed** — If steps 1-4 don't get the file under budget, propose splitting the skill into two specialists with a coordinator. Present the proposed split to me before executing.

### Refactoring Rules

- **Never change the skill's behavior.** The refactored skill must produce the same outputs given the same inputs. You're changing how instructions are organized, not what they instruct.
- **Preserve all content.** Nothing gets deleted — it gets moved to reference files, converted to scripts, or restructured. If a checklist item exists, it must still exist after refactoring.
- **One file at a time.** Refactor a file, show me the before/after word count, confirm compliance, then move to the next file.

---

## Step 5: Post-Refactoring Validation

After all refactoring is complete:

1. Re-run the compliance checks on every modified file
2. Verify worst-case suite loads are under 5,000 tokens
3. Produce a final summary:

```markdown
# Post-Refactoring Summary

## Before vs After

| Skill | Before (tokens) | After (tokens) | Savings |
|-------|-----------------|----------------|---------|
| ... | ... | ... | ... |

## Total Worst-Case Context Load
- Before: [X] tokens
- After: [Y] tokens
- Reduction: [Z]%

## Files Modified
- [list of every file changed with a one-line description of what changed]

## Files Created
- [list of new reference files or scripts created during refactoring]
```

---

## Important Notes

- **Do not refactor without presenting the audit report first.** I need to review the findings and may want to exclude certain skills or adjust priorities.
- **Do not change skill behavior.** This is a structural refactoring, not a functional one.
- **If a skill can't be brought under budget through patterns 1-4**, present the decomposition proposal and wait for my input. Splitting a skill changes its interface and may affect how other skills or workflows reference it.
- **If you encounter skills that are already compliant**, leave them alone. Don't refactor things that don't need refactoring.
