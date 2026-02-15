# Skill Authoring Standard

## What This Is

A governance standard for authoring Claude Code skills that prevents context window bloat, instruction interference, and token waste. Apply this standard to every skill you create or maintain — whether project-specific, personal, or shared across teams.

This document serves two purposes:
1. **For you**: A reference for how to structure skills efficiently
2. **For Claude Code**: A constraint layer that can be loaded before or alongside skill creation to enforce compliance

---

## Placement Options

Choose where to install this standard based on your scope:

| Scope | Location | Effect |
|-------|----------|--------|
| **All projects (personal default)** | `~/.claude/CLAUDE.md` | Every Claude Code session sees it |
| **Single repo** | `<repo>/.claude/CLAUDE.md` or `<repo>/CLAUDE.md` | All sessions in this repo see it |
| **Skill creation only** | Load as a prompt when creating/editing skills | On-demand enforcement |

For maximum coverage, add the **Directive Block** (Section 1 below) to your user-level `~/.claude/CLAUDE.md` and keep the full document accessible for reference when authoring.

---

## Section 1: Directive Block

Add this to your CLAUDE.md. It's intentionally compact — this block is always in context, so it must be small.

```markdown
## Skill Authoring Constraints

All skills in this project must follow the progressive loading architecture:

**Token budgets (hard limits):**
- Coordinator/entry-point SKILL.md: ≤800 tokens (~600 words)
- Specialist SKILL.md: ≤2,000 tokens (~1,500 words)
- Reference files: ≤1,500 tokens (~1,100 words)
- Maximum simultaneous instruction load: ≤5,000 tokens

**Structure rules:**
- Coordinators contain ONLY: classification logic, skill registry, load-then-execute directive, handoff protocol
- Specialist skills load on-demand, one at a time — never pre-load multiple specialists
- Checklists and lookup tables with >10 items go in reference files, loaded conditionally
- Procedure steps use imperative sentences — no explanatory prose
- One compact output example per skill — no verbose schemas alongside examples
- Eval cases and templates live outside skill directories and are never loaded during execution

**When creating or editing skills, read the full Skill Authoring Standard at:
[path to this document] before proceeding.**
```

---

## Section 2: Progressive Loading Architecture

### The Problem

Each skill loaded into context has three costs:
1. **Direct token cost** — instruction text consuming the context window
2. **Interference cost** — multiple detailed procedures causing step blending and indecision
3. **Cache cost** — variable instruction prefixes reducing KV-cache hit rates

These compound multiplicatively. Two 3,000-token skills loaded simultaneously don't cost 6,000 tokens of effective capacity — they cost 6,000 tokens plus the reasoning overhead of disambiguating between them.

### The Solution: Three-Layer Progressive Loading

```
Layer 1: Coordinator          Always in context        ≤800 tokens
          ↓ routes to
Layer 2: Specialist Skill     Loaded on demand          ≤2,000 tokens
          ↓ references
Layer 3: Reference Files      Loaded within a step     ≤1,500 tokens

Worst-case simultaneous load: ≤4,300 tokens (hard ceiling: 5,000)
```

**Layer 1 — Coordinator**: The entry point. Contains classification logic that determines which specialist skill to invoke. Knows about all available skills but contains none of their procedures. For standalone skills (no suite), the skill itself is both coordinator and specialist — budget it at ≤2,000 tokens.

**Layer 2 — Specialist Skill**: The full procedure for a single task type. Loaded only when the coordinator routes to it. Contains numbered steps, decision points, output format, and pointers to reference files. Exactly one specialist is in context at a time.

**Layer 3 — Reference Files**: Detailed checklists, lookup tables, patterns libraries, or domain-specific data. Loaded only when a specific procedure step needs them. A specialist skill might reference three different checklists but only load the one relevant to the current situation.

### When You Don't Need a Coordinator

Not every skill needs a suite. Standalone skills that serve a single purpose can skip the coordinator layer entirely. In this case, the skill's SKILL.md *is* the specialist — budget it at ≤2,000 tokens and use reference files for anything that would push it over.

The coordinator pattern is warranted when:
- You have 3+ related skills that share a problem domain
- The user's input needs classification before you know which procedure to run
- Skills chain together (output of one feeds into another)

---

## Section 3: Token Budgets

### How to Measure

Approximate: 1 token ≈ 0.75 words. Count words and multiply by 1.33 for a token estimate. For precise measurement, use a tokenizer or have Claude Code count during the compliance check.

### Budget Tiers

| File Type | Token Limit | Word Limit (approx) | Rationale |
|-----------|-------------|----------------------|-----------|
| Coordinator SKILL.md | 800 | 600 | Always loaded — must be minimal |
| Specialist SKILL.md | 2,000 | 1,500 | Core procedure with decision points |
| Reference file | 1,500 | 1,100 | Single-purpose lookup, loaded conditionally |
| Standalone SKILL.md (no suite) | 2,000 | 1,500 | Same as specialist — it's doing the same job |

### Scaling for Complexity

Some skills genuinely need more room. If a specialist SKILL.md can't fit under 2,000 tokens after applying all the writing rules, the fix is **never** to raise the budget. Instead:

1. Extract the largest section into a reference file
2. Split the skill into two specialist skills with a coordinator
3. Move deterministic/mechanical steps into a script that the skill invokes

If you find yourself repeatedly hitting the ceiling, it usually means the skill is trying to do too many things. Decompose it.

---

## Section 4: Writing Rules

These rules apply to every SKILL.md and reference file. They exist to maximize information density per token.

### For Specialist SKILL.md Files

**Structure template:**

```markdown
---
name: [skill-name]
description: [Trigger description — when to use, what it does. Be specific and slightly pushy about triggers.]
---

# [Skill Name]

## Inputs
[What the skill expects. 3-5 lines. Required vs optional clearly marked.]

## Procedure
[Numbered steps. Each step = one action + one output.]
[Decision points as inline conditionals.]
[Reference file loads as explicit steps: "Read references/X.md and work through each item."]

## Output Format
[One compact example. Annotate variations inline.]

## Handoff
[What to pass forward if chaining to another skill. 2-3 lines.]
[What to pass: structured data. What NOT to pass: raw files, intermediate reasoning.]

## References
[Table: file path, when to load, what it contains. Only listed, never embedded.]
```

**Writing principles:**

- **Imperative sentences for procedures.** Write "Read the file. Extract the imports. Classify each as server or client." not "You should read the file to understand its imports and then classify them..."
- **Inline conditionals for decision points.** Write "If X → do A. If Y → do B. Otherwise → do C." Don't create nested sub-sections for each branch.
- **No explanatory prose.** Every sentence must either instruct an action or define an output. "This step is important because..." is always cuttable. If the rationale genuinely matters for correct execution, frame it as context: "Note: barrel exports mask the real file path — always resolve to the source file."
- **One example per output format.** Show a compact, realistic example. Don't also describe the schema in prose. If the example is clear, the schema is redundant.
- **Specific references, not inline content.** "Read `references/checklist.md`" costs 5 tokens. Embedding a 40-item checklist costs 400+ tokens — and wastes them when that checklist isn't relevant.

### For Reference Files

- **Pure content.** No preamble ("This checklist covers..."), no meta-instructions ("Use this when..."), no conclusions ("After completing this checklist..."). Those belong in the specialist SKILL.md's procedure step that loads the reference.
- **One item per line.** Each checklist item, pattern, or lookup entry is a single line containing: what to check + what a problem looks like.
- **Organized by category.** Group related items under short headers. This lets the agent scan for relevance without reading every item.
- **Table of contents for files >100 lines.** A 3-line TOC at the top saves the agent from reading 200 lines to find the relevant section.

### For Coordinator SKILL.md Files

The coordinator is the most constrained file. It contains exactly five elements:

1. **Purpose statement** — one sentence
2. **Classification logic** — a concise decision tree or conditional block
3. **Skill registry** — a table with: skill name, file path, one-line purpose, model recommendation (if applicable)
4. **Load-then-execute directive** — explicit instruction to read only the relevant specialist skill
5. **Handoff protocol** — what structured data passes between skills when chaining

Nothing else. No examples, no procedures, no detailed descriptions of what each skill does internally.

---

## Section 5: Suite Organization

### Directory Structure Pattern

```
skill-suite-name/
├── SKILL.md                          # Coordinator (Layer 1)
├── skills/
│   ├── specialist-a/
│   │   ├── SKILL.md                  # Specialist (Layer 2)
│   │   └── references/               # Reference files (Layer 3)
│   │       ├── checklist-x.md
│   │       └── patterns-y.md
│   ├── specialist-b/
│   │   ├── SKILL.md
│   │   └── references/
│   │       └── lookup-table.md
│   └── specialist-c/
│       └── SKILL.md
├── scripts/                          # Executable automation (not loaded into context)
│   ├── compliance-check.sh
│   └── token-count.sh
├── templates/                        # Output templates (loaded only when producing output)
│   └── report-template.md
└── eval-cases/                       # Never loaded during execution
    ├── evals.json
    └── cases/
```

### Standalone Skill Structure

```
skill-name/
├── SKILL.md                          # Combined coordinator + specialist
├── references/                       # Reference files (loaded conditionally)
│   └── detailed-checklist.md
└── eval-cases/                       # Never loaded during execution
    └── evals.json
```

### Key Rules

- **Eval cases and templates never live inside a skill directory** that might be auto-loaded. Keep them in dedicated subdirectories that are only accessed during eval runs or output generation.
- **Scripts are executed, not read.** A 200-line Python script costs zero context tokens if invoked via bash. Move any deterministic logic (file scanning, formatting, validation) into scripts.
- **No cross-specialist loading.** Specialist A must never read Specialist B's SKILL.md. If they need to share information, it passes through the coordinator's handoff protocol as structured data.

---

## Section 6: Model Routing Annotations

Skills can include model recommendations to support intelligent routing. Add a `model_tier` field to the SKILL.md frontmatter or include it in the coordinator's skill registry.

```markdown
---
name: file-scanner
description: Scan and catalog project files by type and purpose
model_tier: mechanical
---
```

| Tier | When to Use | Typical Models |
|------|-------------|----------------|
| `mechanical` | Deterministic tracing, file operations, format conversion, pattern matching | Haiku, Sonnet |
| `analytical` | Diagnosis, classification, multi-factor decision making | Sonnet |
| `reasoning` | Complex debugging, architectural decisions, nuanced tradeoffs | Opus |

This is advisory — the routing system (or the human) makes the final decision. But embedding the recommendation in the skill means the coordinator can surface it when routing.

---

## Section 7: Compliance Enforcement

### Automated Compliance Check Script

Create this script at the root of your skills directory. It validates every SKILL.md and reference file against the standard.

```bash
#!/bin/bash
# compliance-check.sh — Validate skill files against authoring standard
# Usage: bash compliance-check.sh <skill-directory>

SKILL_DIR="${1:-.}"
ERRORS=0
WARNINGS=0

echo "=== Skill Authoring Compliance Check ==="
echo "Scanning: $SKILL_DIR"
echo ""

# Token budget check (using word count as proxy)
check_budget() {
    local file="$1"
    local max_words="$2"
    local label="$3"
    local word_count=$(wc -w < "$file")
    local token_estimate=$(( word_count * 133 / 100 ))

    if [ "$word_count" -gt "$max_words" ]; then
        echo "  FAIL: $file — $word_count words (~$token_estimate tokens) exceeds $label limit of $max_words words"
        ERRORS=$((ERRORS + 1))
    else
        echo "  PASS: $file — $word_count words (~$token_estimate tokens) [limit: $max_words words]"
    fi
}

# Check coordinator SKILL.md (if skills/ subdirectory exists, root SKILL.md is a coordinator)
ROOT_SKILL="$SKILL_DIR/SKILL.md"
if [ -f "$ROOT_SKILL" ]; then
    if [ -d "$SKILL_DIR/skills" ]; then
        echo "[Coordinator] $ROOT_SKILL"
        check_budget "$ROOT_SKILL" 600 "coordinator"
    else
        echo "[Standalone Skill] $ROOT_SKILL"
        check_budget "$ROOT_SKILL" 1500 "standalone specialist"
    fi
fi

# Check specialist SKILL.md files
if [ -d "$SKILL_DIR/skills" ]; then
    for skill_md in "$SKILL_DIR"/skills/*/SKILL.md; do
        [ -f "$skill_md" ] || continue
        echo "[Specialist] $skill_md"
        check_budget "$skill_md" 1500 "specialist"
    done
fi

# Check reference files
find "$SKILL_DIR" -path "*/references/*.md" -type f | while read ref_file; do
    echo "[Reference] $ref_file"
    check_budget "$ref_file" 1100 "reference"
done

# Structural checks
echo ""
echo "=== Structural Checks ==="

# Check that eval cases are not inside skill directories
eval_in_skill=$(find "$SKILL_DIR/skills" -name "evals.json" 2>/dev/null | head -5)
if [ -n "$eval_in_skill" ]; then
    echo "  FAIL: Eval files found inside skill directories (should be in eval-cases/):"
    echo "$eval_in_skill" | sed 's/^/    /'
    ERRORS=$((ERRORS + 1))
else
    echo "  PASS: No eval files inside skill directories"
fi

# Check for cross-specialist references
if [ -d "$SKILL_DIR/skills" ]; then
    for skill_md in "$SKILL_DIR"/skills/*/SKILL.md; do
        [ -f "$skill_md" ] || continue
        skill_name=$(basename $(dirname "$skill_md"))
        # Look for references to other specialist SKILL.md files
        other_refs=$(grep -n "skills/.*SKILL.md" "$skill_md" | grep -v "$skill_name" || true)
        if [ -n "$other_refs" ]; then
            echo "  WARN: $skill_md references other specialist skills (should use handoff protocol):"
            echo "$other_refs" | sed 's/^/    /'
            WARNINGS=$((WARNINGS + 1))
        fi
    done
    echo "  PASS: No cross-specialist references detected" 2>/dev/null
fi

echo ""
echo "=== Summary ==="
echo "Errors: $ERRORS"
echo "Warnings: $WARNINGS"
[ "$ERRORS" -eq 0 ] && echo "Status: COMPLIANT" || echo "Status: NON-COMPLIANT — fix errors before shipping"
exit $ERRORS
```

### Claude Code Compliance Prompt

When creating or editing skills, prepend this instruction to ensure Claude Code self-enforces:

```
Before writing any SKILL.md or reference file, confirm you've read the Skill Authoring
Standard at [path]. After writing each file, perform the compliance self-check:

1. Count the words. Is it within budget?
   - Coordinator: ≤600 words
   - Specialist: ≤1,500 words
   - Reference: ≤1,100 words
2. Are procedure steps imperative sentences (not explanatory prose)?
3. Are checklists >10 items extracted to reference files?
4. Is there exactly one compact output example (no redundant schema)?
5. Does the file reference other files by path rather than embedding their content?

If any check fails, refactor before proceeding. Report the word count of each file produced.
```

### Integration with skill-creator

If you use the skill-creator workflow, add this to your skill-creator configuration or include it when invoking the create mode:

```
When creating or improving skills, all output must comply with the Skill Authoring
Standard. Key constraints:
- Coordinator SKILL.md ≤800 tokens / ~600 words
- Specialist SKILL.md ≤2,000 tokens / ~1,500 words  
- Reference files ≤1,500 tokens / ~1,100 words
- Maximum simultaneous context load ≤5,000 tokens
- Progressive loading: coordinator → one specialist → conditional reference files
- Procedures use imperative sentences, no explanatory prose
- Checklists >10 items extracted to reference files

Produce a token budget report after scaffolding each skill.
```

---

## Section 8: Common Refactoring Patterns

When an existing skill exceeds its budget, apply these patterns in order:

### Pattern 1: Extract Checklists
**Symptom**: The SKILL.md contains a long itemized list (diagnostic checks, validation rules, style guidelines).
**Fix**: Move the list to `references/[name].md`. Replace with: "Read `references/[name].md` and work through each item against [target]."
**Savings**: Typically 300-800 tokens.

### Pattern 2: Kill the Prose
**Symptom**: Procedure steps contain "why" explanations, background context, or hedging language.
**Fix**: Convert each step to a single imperative sentence. Move critical context to a one-line "Note:" if it affects correctness.
**Savings**: Typically 200-500 tokens. Often the single biggest win.

### Pattern 3: Deduplicate Output Specs
**Symptom**: The output format is described in prose AND shown as an example AND defined as a schema.
**Fix**: Keep only the example. Annotate variations inline with comments.
**Savings**: Typically 150-400 tokens.

### Pattern 4: Script the Mechanical Work
**Symptom**: The SKILL.md describes a multi-step file scanning, parsing, or formatting procedure in natural language.
**Fix**: Write a script that does the mechanical work. The SKILL.md step becomes: "Run `scripts/scan.sh [args]` and use the output for [next step]."
**Savings**: Variable, but also improves reliability since scripts are deterministic.

### Pattern 5: Decompose the Skill
**Symptom**: After applying patterns 1-4, the SKILL.md is still over budget.
**Fix**: The skill is doing too much. Split it into two specialist skills with a coordinator. The split point is usually where the skill changes modes (e.g., from investigation to remediation, from analysis to generation).
**Savings**: Each resulting skill is independently budgeted.

---

## Quick Reference Card

Pin this somewhere visible when authoring skills.

```
┌─────────────────────────────────────────────────┐
│          SKILL AUTHORING QUICK REFERENCE         │
├─────────────────────────────────────────────────┤
│                                                  │
│  BUDGETS                                         │
│  Coordinator ........... ≤800 tokens (~600 w)    │
│  Specialist ............ ≤2,000 tokens (~1,500 w)│
│  Reference ............. ≤1,500 tokens (~1,100 w)│
│  Max simultaneous ...... ≤5,000 tokens           │
│                                                  │
│  LOADING RULES                                   │
│  ✓ Coordinator always loaded                     │
│  ✓ One specialist at a time                      │
│  ✓ References loaded conditionally within steps  │
│  ✗ Never pre-load multiple specialists           │
│  ✗ Never embed eval cases in skill directories   │
│  ✗ Never cross-reference between specialists     │
│                                                  │
│  WRITING RULES                                   │
│  ✓ Imperative sentences for procedures           │
│  ✓ Inline conditionals for decision points       │
│  ✓ One compact example per output format         │
│  ✓ Extract checklists >10 items to references    │
│  ✗ No explanatory prose in procedures            │
│  ✗ No redundant schema + example combinations    │
│  ✗ No meta-instructions in reference files       │
│                                                  │
│  REFACTORING ORDER                               │
│  1. Extract checklists                           │
│  2. Kill prose                                   │
│  3. Deduplicate output specs                     │
│  4. Script mechanical work                       │
│  5. Decompose the skill                          │
│                                                  │
└─────────────────────────────────────────────────┘
```
