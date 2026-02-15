# Claude Code Prompt: Context-Efficient Skill Architecture for Frontend QA Suite

## Objective

This prompt defines **mandatory architectural constraints** for the frontend QA skill suite. Apply these constraints when scaffolding or refactoring any skill in the `.claude/skills/frontend-qa/` directory. These rules exist to prevent context window overload and instruction interference between skills.

This prompt should be applied **before and alongside** the main scaffolding prompt. Every SKILL.md you write must comply with these constraints.

---

## The Core Problem We're Solving

When multiple detailed skills are loaded into context simultaneously:
1. Instruction blending occurs — steps from one skill leak into another skill's execution
2. The agent becomes indecisive about which procedure applies, wasting tokens on deliberation
3. Actual code and reasoning get squeezed out of the context window by static instructions
4. Cache hit rates drop because the context prefix keeps changing based on which skills happen to be loaded

The architecture below prevents all four problems through **progressive context loading** — only the instructions needed for the current step are in context at any given time.

---

## Context Budget — Hard Limits

Every file in this skill suite must respect these token budgets. Measure by approximate word count (1 token ≈ 0.75 words).

| Layer | File | Max Tokens | Max Words (approx) |
|-------|------|-----------|---------------------|
| **Always loaded** | Coordinator `SKILL.md` | 800 | ~600 |
| **Loaded on demand** | Each specialist `SKILL.md` | 2,000 | ~1,500 |
| **Loaded on demand** | Each reference/checklist file | 1,500 | ~1,100 |
| **Never loaded during execution** | Eval cases, templates, examples | N/A | N/A |

**Total worst-case instruction footprint at any point in execution**: Coordinator (800) + one specialist skill (2,000) + one reference file (1,500) = **4,300 tokens**. This must never exceed 5,000 tokens of skill instructions in context at once.

---

## Architecture: Three-Layer Progressive Loading

### Layer 1: Coordinator (Always in Context)

The coordinator SKILL.md at `.claude/skills/frontend-qa/SKILL.md` is the only skill file that's always loaded. It must contain **only**:

1. **A one-sentence purpose statement** for the skill suite
2. **Issue classification logic** — a decision tree that maps the user's input to the correct specialist skill. Write this as a concise conditional block, not prose:
   ```
   If the user wants to understand what components are on a page → page-component-mapper
   If the issue is visual/layout (alignment, spacing, responsive, styling) → css-layout-debugger
   If the issue is behavioral (clicks, state, events, data) → ui-bug-investigator
   If the user has a diagnosis and wants to apply a fix → component-fix-and-verify
   If a fix was applied and tests are needed → regression-test-generator
   If unclear → start with page-component-mapper, then ask the user
   ```
3. **A skill registry** — a simple table with skill name, file path, one-line description, and model recommendation:
   ```
   | Skill | Path | Purpose | Suggested Model |
   |-------|------|---------|-----------------|
   | page-component-mapper | skills/page-component-mapper/SKILL.md | Trace route to component tree | Sonnet (mechanical tracing) |
   | ui-bug-investigator | skills/ui-bug-investigator/SKILL.md | Diagnose behavioral/state/data bugs | Opus (complex reasoning) |
   | ... | ... | ... | ... |
   ```
4. **The load-then-execute instruction** — an explicit directive:
   ```
   After classifying the issue, read ONLY the relevant specialist SKILL.md file
   and follow its procedure. Do NOT read other specialist skills — they are not
   needed and will interfere with the current task.
   ```
5. **A handoff protocol** — how to pass context from one skill to the next when chaining (e.g., mapper → investigator → fix-and-verify):
   ```
   When chaining skills, pass forward ONLY:
   - The component map JSON (from page-component-mapper)
   - The diagnosis summary (from ui-bug-investigator or css-layout-debugger)
   - The fix specification (from the diagnostic skill)
   Do NOT pass raw file contents, full trace logs, or intermediate reasoning.
   ```

**The coordinator must NOT contain**: Detailed procedures, diagnostic checklists, output format specifications, examples, or any content that belongs in a specialist skill.

### Layer 2: Specialist Skills (Loaded One at a Time)

Each specialist SKILL.md under `skills/[name]/SKILL.md` contains the full procedure for that skill. It's read into context only when the coordinator routes to it.

**Structure each specialist SKILL.md as**:

```markdown
---
name: [skill-name]
description: [one-line trigger description]
---

# [Skill Name]

## Inputs
[What this skill expects — 3-5 lines max]

## Procedure
[Numbered steps. Terse. Action-oriented. No explanatory prose.]
[Each step = one clear action + one clear output]
[Decision points as inline conditionals, not nested sub-sections]

## Output Format
[Exact structure — use a compact example, not a verbose schema]

## Handoff
[What to pass to the next skill if chaining. 2-3 lines.]

## References (load only if needed)
[List reference files that contain detailed checklists or lookup tables]
[Format: "If you need the [X] checklist, read: [path]"]
```

**Writing rules for specialist skills**:
- **Procedure steps must be imperative sentences.** Write "Read the file. Check for `use client`. Record the result." not "You should read the file to determine whether it contains a use client directive, which would indicate..."
- **No background explanations.** Don't explain why a step matters. Just say what to do. The skill author (me) understands the reasoning — the executing agent just needs the procedure.
- **Decision points inline, not nested.** Write "If the file has `use client` → classify as client component. Otherwise → classify as server component." Don't create sub-sections for each branch.
- **One output format, shown by compact example.** Don't describe the schema in prose then also show an example. Show one tight example and note any variations inline.
- **Reference files for long lists.** If a skill needs a 40-item diagnostic checklist, that checklist goes in a separate reference file (Layer 3) that the skill loads only when it reaches that step. The SKILL.md contains the step "Read the diagnostic checklist at `references/diagnostic-checklist.md` and work through each item."

### Layer 3: Reference Files (Loaded Within a Skill Step)

These are detailed lookup tables, checklists, or templates that a specialist skill needs at a specific step. They live under each skill's directory:

```
skills/ui-bug-investigator/
├── SKILL.md
└── references/
    ├── rendering-checklist.md
    ├── event-handling-checklist.md
    ├── data-flow-checklist.md
    └── nextjs-checklist.md
```

**Why split checklists out of the SKILL.md**: The ui-bug-investigator classifies the bug type first, then only needs the relevant checklist. Loading all four checklists when you only need one wastes ~4,500 tokens. The SKILL.md procedure says:

```
Step 4: Based on the classification from Step 3, read the relevant checklist:
  - Rendering/state issue → references/rendering-checklist.md
  - Event handling issue → references/event-handling-checklist.md
  - Data flow issue → references/data-flow-checklist.md
  - Next.js-specific issue → references/nextjs-checklist.md
Work through each item in the loaded checklist against the target component.
```

**Writing rules for reference files**:
- Pure content, no meta-instructions. Just the checklist items or lookup data.
- Each item is one line: what to check + what indicates a problem.
- No introduction, no conclusion, no "how to use this checklist" preamble.

---

## File Structure (Updated for Progressive Loading)

```
.claude/skills/frontend-qa/
├── SKILL.md                                    # Coordinator (Layer 1) — ≤800 tokens
├── skills/
│   ├── page-component-mapper/
│   │   ├── SKILL.md                            # Specialist (Layer 2) — ≤2,000 tokens
│   │   └── references/
│   │       └── import-resolution-rules.md      # Reference (Layer 3) — ≤1,500 tokens
│   ├── ui-bug-investigator/
│   │   ├── SKILL.md                            # Specialist (Layer 2) — ≤2,000 tokens
│   │   └── references/
│   │       ├── rendering-checklist.md           # Reference (Layer 3)
│   │       ├── event-handling-checklist.md
│   │       ├── data-flow-checklist.md
│   │       └── nextjs-checklist.md
│   ├── css-layout-debugger/
│   │   ├── SKILL.md                            # Specialist (Layer 2) — ≤2,000 tokens
│   │   └── references/
│   │       ├── tailwind-checklist.md
│   │       ├── layout-checklist.md
│   │       └── animation-checklist.md
│   ├── component-fix-and-verify/
│   │   └── SKILL.md                            # Specialist (Layer 2) — ≤2,000 tokens
│   └── regression-test-generator/
│       ├── SKILL.md                            # Specialist (Layer 2) — ≤2,000 tokens
│       └── references/
│           ├── rtl-patterns.md                  # React Testing Library patterns
│           └── playwright-patterns.md           # Playwright E2E patterns
├── templates/                                   # Never loaded during execution
│   ├── component-map.example.json
│   ├── diagnosis-report.example.md
│   └── fix-summary.example.md
└── eval-cases/                                  # Never loaded during execution
    └── page-component-mapper/
        ├── evals.json
        └── cases/
```

---

## Enforcement: Self-Check Before Finishing

After writing every SKILL.md and reference file, perform this compliance check:

### For the coordinator SKILL.md:
- [ ] Under 800 tokens / ~600 words? Count it.
- [ ] Contains ONLY: purpose sentence, classification logic, skill registry, load-then-execute instruction, handoff protocol?
- [ ] Zero detailed procedures? Zero checklists? Zero output format specs?
- [ ] Explicitly tells the agent to read only ONE specialist skill at a time?

### For each specialist SKILL.md:
- [ ] Under 2,000 tokens / ~1,500 words? Count it.
- [ ] Procedure steps are imperative sentences, not explanatory prose?
- [ ] No background paragraphs explaining "why" something matters?
- [ ] Decision points are inline conditionals, not nested sub-sections?
- [ ] Long checklists (>10 items) are extracted to reference files?
- [ ] Output format shown by one compact example, not a verbose schema?
- [ ] References section lists which files to load and under what condition?

### For each reference file:
- [ ] Under 1,500 tokens / ~1,100 words?
- [ ] Pure content — no meta-instructions, no preamble, no "how to use" section?
- [ ] Each checklist item is one line?

### For the full suite:
- [ ] Worst-case instruction load (coordinator + one specialist + one reference) ≤ 5,000 tokens?
- [ ] Eval cases and templates are outside the skill directories (won't be auto-loaded)?
- [ ] No specialist skill references or loads another specialist skill's content?

**If any check fails, refactor the offending file before proceeding.** Split content, tighten prose, extract to references, or restructure. Do not ship a skill that exceeds its budget.

---

## How to Apply This Prompt

This prompt is a **design constraint document**. Use it in one of two ways:

1. **When scaffolding from scratch**: Load this prompt first, then load the main scaffolding prompt. Write all skills in compliance with these constraints from the start.

2. **When refactoring existing skills**: Load this prompt, read each existing SKILL.md, and refactor to comply. Check each file against the enforcement checklist above.

In either case, produce a **token budget report** at the end showing the actual token/word count of each file and the worst-case combined load.
