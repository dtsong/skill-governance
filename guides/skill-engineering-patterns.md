# Skill Engineering Patterns: Quality, Efficiency & Tool Intelligence

## How to Use This Document

This is a patterns reference — a catalog of techniques you can embed into SKILL.md files to improve output quality, reduce token waste, and make tool usage smarter. Each pattern includes:

- What it does and when to use it
- How to codify it (the actual SKILL.md language)
- The tradeoff (every pattern has a cost)

Not every skill needs every pattern. Pick the ones relevant to the skill's domain and complexity. The patterns are organized by concern but many serve multiple purposes — a technique that improves quality often also reduces tokens by eliminating rework cycles.

This document is a **reference file** (Layer 3 in the authoring standard). Load it when authoring or improving skills, not during skill execution.

---

## Part 1: Output Quality Patterns

### 1.1 — Pre-Flight Context Gathering

**Problem**: The agent starts working with incomplete understanding of the project, produces output that doesn't match conventions, then has to redo work.

**Pattern**: Before any action step, add an explicit context-gathering phase that reads project configuration and establishes constraints.

**Codify as**:
```markdown
## Procedure

Step 1: Gather project context (do NOT skip this step).
  - Read package.json → note framework, key dependencies, scripts
  - Read tsconfig.json → note path aliases, strict mode, target
  - Read .eslintrc / eslint.config → note active rules and style conventions
  - Read the nearest 3 files of the same type as the target → note naming conventions,
    import patterns, and code style
  - Record these as constraints for all subsequent steps.
```

**Tradeoff**: Costs 500-1,500 tokens of context reading upfront. Saves 3,000-10,000 tokens of rework when the agent would have produced output that doesn't match project conventions.

**When to use**: Any skill that generates or modifies code, documents, or configuration files. Skip for pure analysis/diagnostic skills.

---

### 1.2 — Convention Mirroring

**Problem**: Generated code is technically correct but stylistically inconsistent with the existing codebase (different naming, different patterns, different import ordering).

**Pattern**: Before generating, read 2-3 exemplar files and explicitly extract the conventions to follow.

**Codify as**:
```markdown
Step 2: Extract conventions from existing code.
  - Read 2-3 existing files of the same type as what you'll produce
  - Note and adopt:
    - Naming convention (camelCase vs PascalCase vs kebab-case for files)
    - Import ordering (external first? grouped by type?)
    - Export style (named vs default, bottom-of-file vs inline)
    - Comment style and density
    - Error handling pattern (try/catch style, error boundary usage)
    - Type annotation style (inline vs separate interface, type vs interface)
  - Apply these conventions to all code you generate. Do not introduce
    new patterns that don't exist in the codebase.
```

**Tradeoff**: Adds ~300 tokens per exemplar file read. Dramatically reduces the "it works but looks foreign" problem.

**When to use**: Any code generation skill. Especially valuable when skills will be used across multiple projects with different conventions.

---

### 1.3 — Output Contracts

**Problem**: The agent produces output that is vaguely correct but doesn't meet specific structural or content requirements. Quality is inconsistent across runs.

**Pattern**: Define explicit, checkable contracts for the output. Not just "produce a component map" but specific required fields, relationships, and completeness criteria.

**Codify as**:
```markdown
## Output Contract

The output MUST satisfy ALL of these conditions:
1. Every component has: file_path (absolute from project root), server_or_client,
   props_type_name, hooks_list, children_list
2. Every file_path resolves to an actual file (verify with file existence check)
3. Every parent-child relationship is bidirectional (if A lists B as child,
   B's entry exists in the map)
4. No component appears more than once (deduplicate by file path)
5. The total component count matches the number of unique imports traced

If any condition fails, fix the output before presenting it.
```

**Tradeoff**: Adds a verification step that costs tokens. But it converts vague quality into checkable assertions that the agent can self-enforce.

**When to use**: Any skill where output structure matters. Especially valuable for skills whose output feeds into other skills (the contract becomes the integration interface).

---

### 1.4 — Self-Verification Loop

**Problem**: The agent produces output, presents it, and moves on — even when the output contains errors it could have caught.

**Pattern**: After producing output, add an explicit verification step where the agent checks its own work against the output contract or domain-specific rules.

**Codify as**:
```markdown
Step 6: Verify your output before presenting it.
  - Re-read the output you just produced
  - Check each item in the Output Contract above
  - For code changes: run `tsc --noEmit` on modified files
  - For component maps: spot-check 3 random file paths exist on disk
  - For diagnoses: confirm the root cause explains ALL reported symptoms,
    not just the first one you found
  - If any check fails → fix and re-verify. Do not present unverified output.
```

**Tradeoff**: Costs 200-800 tokens depending on output size. Catches 60-80% of errors that would otherwise require a user correction round-trip (which costs far more tokens).

**When to use**: Every skill that produces actionable output (code changes, diagnoses, recommendations). Skip for pure information gathering.

---

### 1.5 — Graduated Confidence Signaling

**Problem**: The agent presents all findings with equal confidence, making it hard for the user to know what to trust and what to verify.

**Pattern**: Require the agent to annotate findings with confidence levels and evidence quality.

**Codify as**:
```markdown
For each finding in your diagnosis, indicate confidence:
  - HIGH: Directly confirmed by reading the code. The specific lines are identified.
  - MEDIUM: Consistent with the symptoms and code patterns, but not definitively
    confirmed. Other explanations are possible.
  - LOW: Inferred from indirect evidence. Requires user verification.

Present HIGH confidence findings first. For MEDIUM and LOW, state what additional
information would raise confidence.
```

**Tradeoff**: Adds ~50-100 tokens per finding. Makes outputs dramatically more useful by helping the user prioritize what to act on.

**When to use**: Diagnostic and analytical skills. Not needed for mechanical/generative skills.

---

### 1.6 — Negative Space Documentation

**Problem**: The agent reports what it found but doesn't report what it checked and didn't find. The user can't distinguish "I checked and it's fine" from "I didn't check."

**Pattern**: Require the agent to document what it examined and ruled out, not just what it found.

**Codify as**:
```markdown
Your diagnosis report must include a "Ruled Out" section listing:
- Each category you checked that did NOT reveal issues
- What specific checks you performed for each
- Example: "Event handling: Checked for stopPropagation gaps, duplicate handlers,
  and incorrect event signatures. No issues found."

This section is as important as the findings. It tells the user what ground
has been covered and what hasn't.
```

**Tradeoff**: Adds 100-300 tokens to the output. Builds user trust and prevents redundant follow-up investigations.

**When to use**: Diagnostic, audit, and review skills. Any skill where the user needs to know the coverage of the analysis.

---

## Part 2: Token Optimization Patterns

### 2.1 — Targeted File Reading

**Problem**: The agent reads entire files when it only needs specific sections, consuming thousands of tokens on irrelevant code.

**Pattern**: Specify reading strategies that minimize tokens while getting the needed information.

**Codify as**:
```markdown
File reading rules:
- When checking for "use client": read only the first 5 lines of the file
- When extracting imports: read only lines starting with `import` or `from`
  (stop at the first non-import line after the import block)
- When finding a specific function or component: search for the function/component
  name first, then read a ±30 line window around it
- When understanding overall structure: read the file's exports only
  (search for `export` statements)
- NEVER read an entire file >200 lines unless the task specifically requires
  understanding the full file logic
```

**Tradeoff**: Risk of missing context that lives outside the targeted section. Mitigate by expanding the read window when initial reading is insufficient.

**When to use**: Every skill that reads source files. The savings are proportional to file size — most impactful on large files.

---

### 2.2 — Progressive Detail Expansion

**Problem**: The agent gathers maximum detail on every item before knowing which items matter, wasting tokens on irrelevant deep-dives.

**Pattern**: Start with a shallow pass to identify what's relevant, then go deep only on the relevant items.

**Codify as**:
```markdown
Step 3: Shallow scan (do this BEFORE any deep analysis).
  - List all components by name and file path only
  - Classify each as: likely relevant to the bug / possibly relevant / unlikely relevant
  - Base classification on: proximity to the reported symptom, shared state/context
    with the affected component, parent-child relationship with affected component

Step 4: Deep analysis (ONLY for "likely relevant" components).
  - For each likely-relevant component: read full source, trace state, analyze hooks
  - For possibly-relevant components: read only props interface and hooks list
  - For unlikely-relevant components: skip entirely unless deep analysis reveals
    a dependency you didn't initially see
```

**Tradeoff**: Adds a classification step (~200 tokens). But prevents reading 10 full component files when only 2-3 are relevant.

**When to use**: Any skill that operates on a set of items where relevance varies. Component debugging, dependency analysis, migration planning.

---

### 2.3 — Output Token Discipline

**Problem**: The agent over-explains, repeats information, or produces verbose output that could be said in fewer tokens.

**Pattern**: Set explicit output constraints for each section of the skill's output.

**Codify as**:
```markdown
## Output Constraints

- Diagnosis summary: ≤3 sentences stating the root cause
- Evidence: Quote the specific code lines (with line numbers), no surrounding context
- Proposed fix: Show ONLY the diff (changed lines with ±2 lines of context), not
  the entire modified file
- Risk assessment: ≤2 sentences on what else the fix could affect
- Do NOT repeat the bug description back to the user
- Do NOT explain how you found the bug (your process is not the deliverable)
- Do NOT suggest alternative approaches unless the primary fix has clear downsides
```

**Tradeoff**: Can feel terse if the user wants explanation. Mitigate by adding: "If you want more detail on any finding, ask and I'll expand."

**When to use**: Every skill. This is the single highest-leverage pattern for token efficiency. Most agent verbosity is habitual, not informational.

---

### 2.4 — Structured Data Over Prose for Handoffs

**Problem**: When skills chain together, the handoff data is verbose prose that the next skill must parse and compress, wasting tokens in both directions.

**Pattern**: Define handoff formats as compact structured data (JSON) rather than narrative text.

**Codify as**:
```markdown
## Handoff Output

When passing results to the next skill, output this JSON structure ONLY
(no surrounding prose):

{
  "component": "AvatarUpload",
  "file": "components/settings/avatar-upload.tsx",
  "root_cause": "stale closure in useEffect capturing initial fileUrl",
  "fix_type": "dependency_array",
  "affected_lines": [34, 38],
  "confidence": "high",
  "siblings_to_check": ["ProfileForm"]
}

Do NOT wrap this in explanation. The next skill parses this directly.
```

**Tradeoff**: Less human-readable for intermediate steps. But if the user is watching, they can see the structured data. The token savings compound through every step of a chain.

**When to use**: Any skill that outputs data consumed by another skill. Not needed for terminal skills (last in a chain) that present to the user.

---

### 2.5 — Early Termination Conditions

**Problem**: The agent exhaustively completes every step of a procedure even when an early step definitively answers the question.

**Pattern**: Add explicit exit ramps at key decision points.

**Codify as**:
```markdown
Step 2: Check for obvious causes first.
  - If the component has no "use client" directive but uses hooks → STOP.
    This is the root cause. Skip Steps 3-7. Go directly to Step 8 (fix).
  - If the component's props interface doesn't match what the parent passes →
    STOP. This is likely the root cause. Go to Step 8.
  - If neither of these applies → continue to Step 3.
```

**Tradeoff**: Risk of premature diagnosis if the "obvious" cause masks a deeper issue. Mitigate by including: "If the fix from an early termination doesn't resolve the issue, return to the step where you exited and continue the full procedure."

**When to use**: Diagnostic skills where common issues have clear signatures. Not appropriate for comprehensive audit/review skills that must check everything.

---

### 2.6 — Cache-Friendly Context Ordering

**Problem**: Skills that read context in variable order prevent KV-cache reuse across invocations, increasing latency and compute cost.

**Pattern**: Standardize the order of context reading so the prompt prefix is stable.

**Codify as**:
```markdown
## Context Reading Order (follow this exact sequence)

1. Read project configuration (package.json, tsconfig.json) — ALWAYS FIRST
2. Read the target entry file (page.tsx or specified component)
3. Read parent layout files (from nearest to root)
4. Read the specific component under investigation
5. Read sibling/related components only as needed

This order ensures the project context prefix is identical across invocations,
maximizing cache utilization.
```

**Tradeoff**: Slightly less intuitive ordering in some cases. The cache benefit depends on how often the skill is invoked with the same project context.

**When to use**: Skills invoked repeatedly within the same project. Most impactful for high-frequency skills like bug investigation and code generation.

---

## Part 3: Intelligent Tool Utilization Patterns

### 3.1 — Tool Selection Heuristics

**Problem**: The agent uses familiar tools even when a better tool exists, or uses expensive tools when a cheap one would suffice.

**Pattern**: Provide explicit decision rules for which tool to use in which situation.

**Codify as**:
```markdown
## Tool Selection Rules

For finding files by name:
  → Use `find` or `fd` (fast, no token cost for file contents)
  → Do NOT use grep to search file contents when you just need to locate a file

For checking if a file exists:
  → Use `test -f <path>` (1 token cost)
  → Do NOT read the file to check existence

For reading specific lines:
  → Use `sed -n '30,60p' <file>` (reads only the needed lines)
  → Do NOT read the entire file and then extract lines

For searching code patterns:
  → Use `grep -rn 'pattern' --include='*.tsx'` (targeted, returns line numbers)
  → Do NOT read files one by one looking for a pattern

For running multiple independent checks:
  → Batch them into a single shell command with `&&` or `;`
  → Do NOT make separate tool calls for each check

For project-wide analysis:
  → Use `find ... | xargs grep ...` pipelines
  → Do NOT traverse directories manually
```

**Tradeoff**: Adds ~200 tokens of instruction. Prevents hundreds of tokens wasted on inefficient tool calls across the skill's execution.

**When to use**: Every skill that uses shell tools. These heuristics are universal.

---

### 3.2 — Batched Tool Calls

**Problem**: The agent makes one tool call per piece of information, creating round-trip overhead that compounds across many small operations.

**Pattern**: Explicitly instruct batching of related queries into single tool calls.

**Codify as**:
```markdown
When gathering information about multiple files, batch into single commands:

Instead of:
  call 1: cat components/button.tsx
  call 2: cat components/input.tsx
  call 3: cat components/select.tsx

Do:
  call 1: head -5 components/button.tsx components/input.tsx components/select.tsx

Instead of checking "use client" in each file separately:
  call 1: grep -l '"use client"' components/*.tsx

Instead of running lint, typecheck, and tests separately when all are needed:
  call 1: npm run lint -- --quiet && npx tsc --noEmit && npm test -- --bail 2>&1 | tail -20
```

**Tradeoff**: Batched commands produce combined output that's slightly harder to parse. But the round-trip savings are significant — each tool call has fixed overhead regardless of complexity.

**When to use**: Any skill with multiple information-gathering steps. Most impactful when the skill operates on many files.

---

### 3.3 — Pre-Flight Validation Before Expensive Operations

**Problem**: The agent runs a long, expensive operation (full test suite, large refactor) then discovers a basic precondition wasn't met (wrong directory, missing dependency, syntax error in modified file).

**Pattern**: Add cheap validation checks before expensive operations.

**Codify as**:
```markdown
Before running the test suite:
  1. Verify the modified file has no syntax errors: `npx tsc --noEmit <file>` (fast)
  2. Verify the test file exists: `test -f <test-file>` (instant)
  3. Verify node_modules is populated: `test -d node_modules` (instant)
  4. Only then: `npm test -- --testPathPattern=<pattern>` (expensive)

Before applying a multi-file refactor:
  1. Verify all target files exist and are readable
  2. Verify no target file has unsaved changes (check git status)
  3. Create a restoration point: `git stash` or copy originals
  4. Only then: apply changes
```

**Tradeoff**: Adds 2-4 cheap tool calls. Prevents wasting 5,000+ tokens on an operation that was doomed to fail.

**When to use**: Any skill that runs tests, builds, deployments, or multi-file modifications.

---

### 3.4 — Fallback Chains

**Problem**: The agent tries one approach, fails, and either gives up or asks the user what to do — even when a reasonable alternative exists.

**Pattern**: Define ordered fallback strategies for common failure modes.

**Codify as**:
```markdown
If the primary approach fails, follow this fallback chain:

For "test command not found":
  1. Try: `npx vitest run` → if fails →
  2. Try: `npx jest` → if fails →
  3. Try: `npm test` → if fails →
  4. Check package.json scripts for test command → use whatever is configured →
  5. If still no test runner found → report to user, skip test verification step

For "file import can't be resolved":
  1. Check tsconfig.json paths for alias resolution → if not there →
  2. Check for barrel export (index.ts in the import directory) → if not there →
  3. Check for .ts/.tsx/.js/.jsx extension variations → if not there →
  4. Search project-wide for a file with matching export name →
  5. If still unresolved → flag as unresolved in output, continue with other files
```

**Tradeoff**: Adds complexity to the skill procedure. But eliminates dead-end states that require user intervention (which is the most expensive outcome in terms of wall-clock time).

**When to use**: Skills that interact with project tooling (test runners, build systems, package managers) where the specific tools vary between projects.

---

### 3.5 — Tool Output Parsing Discipline

**Problem**: The agent reads the full output of a tool call even when it only needs a specific piece of information, loading irrelevant text into context.

**Pattern**: Pipe tool output through filters before consuming it.

**Codify as**:
```markdown
When running commands that produce verbose output, filter at the source:

For test results (only care about failures):
  `npm test 2>&1 | grep -A 3 'FAIL\|Error\|✕'`

For TypeScript errors (only care about the error messages):
  `npx tsc --noEmit 2>&1 | grep 'error TS'`

For git status (only care about modified files):
  `git diff --name-only`

For dependency trees (only care about direct deps):
  `npm ls --depth=0`

For file search results (only care about file paths, not content):
  `grep -rl 'pattern' --include='*.tsx' src/`

NEVER consume raw output from: npm install, full test suite runs, webpack/vite
build logs, or git log without filtering. These can be thousands of lines.
```

**Tradeoff**: Risk of filtering out information that turns out to be relevant. Mitigate by including: "If filtered output doesn't contain what you need, re-run without the filter on a targeted scope."

**When to use**: Every skill that runs shell commands. This is the tool-usage equivalent of targeted file reading (Pattern 2.1).

---

### 3.6 — Capability Detection Before Use

**Problem**: The agent assumes a tool or feature is available, crafts a plan around it, then fails at execution and has to re-plan.

**Pattern**: Detect available tools and capabilities before planning the approach.

**Codify as**:
```markdown
Step 1: Detect project tooling (run these checks first).
  - Test runner: `grep -q '"vitest\|jest\|mocha"' package.json && echo "found"`
  - E2E framework: `test -f playwright.config.ts && echo "playwright" || (test -f cypress.config.ts && echo "cypress")`
  - Linter: `test -f .eslintrc* || test -f eslint.config.* && echo "eslint"`
  - Formatter: `test -f .prettierrc* && echo "prettier"`
  - Styling: `test -f tailwind.config.* && echo "tailwind"`

  Record what's available. Adapt subsequent steps to use only detected tools.
  Do NOT assume a tool exists. If a tool is needed but missing, skip that
  verification step and note it in the output.
```

**Tradeoff**: Adds 1 batched tool call (~100 tokens). Prevents entire wasted procedure branches built on wrong assumptions.

**When to use**: Any skill that depends on project tooling. Critical for skills meant to work across different projects.

---

### 3.7 — Incremental Verification Over Batch Verification

**Problem**: The agent makes multiple changes, then runs verification once at the end. If it fails, it's unclear which change caused the failure, requiring costly debugging.

**Pattern**: Verify after each significant change, not at the end.

**Codify as**:
```markdown
When applying multiple changes:
  For each file modification:
    1. Apply the change
    2. Run `npx tsc --noEmit <modified-file>` immediately
    3. If it passes → continue to next change
    4. If it fails → revert this change, diagnose the type error,
       adjust approach, re-apply, re-verify

Do NOT batch all changes and run verification once at the end.
The cost of isolating a failure across N changes is much higher
than N individual checks.
```

**Tradeoff**: More tool calls (one per change instead of one total). But each call is cheap and targeted, and the total cost is lower than debugging a batch failure.

**When to use**: Any skill that modifies multiple files. Especially important for fix-and-verify and refactoring skills.

---

## Part 4: Composing Patterns Into Skills

Not every skill needs every pattern. Here's a guide for which patterns to prioritize by skill type:

| Skill Type | Must Have | Should Have | Consider |
|------------|-----------|-------------|----------|
| **Code Generation** | Pre-flight context (1.1), Convention mirroring (1.2), Output contracts (1.3), Tool selection (3.1) | Self-verification (1.4), Targeted reading (2.1), Output discipline (2.3) | Cache-friendly ordering (2.6) |
| **Diagnosis/Debugging** | Progressive detail (2.2), Early termination (2.5), Confidence signaling (1.5), Negative space (1.6) | Batched tools (3.2), Fallback chains (3.4), Tool output parsing (3.5) | Output discipline (2.3) |
| **Fix & Verify** | Pre-flight validation (3.3), Incremental verification (3.7), Fallback chains (3.4), Capability detection (3.6) | Self-verification (1.4), Output discipline (2.3) | Batched tools (3.2) |
| **Analysis/Mapping** | Targeted reading (2.1), Batched tools (3.2), Tool selection (3.1), Output contracts (1.3) | Progressive detail (2.2), Structured handoffs (2.4) | Cache-friendly ordering (2.6) |
| **Test Generation** | Pre-flight context (1.1), Convention mirroring (1.2), Capability detection (3.6), Self-verification (1.4) | Output contracts (1.3), Fallback chains (3.4) | Output discipline (2.3) |
| **Coordinator/Router** | Structured handoffs (2.4), Early termination (2.5), Capability detection (3.6) | Output discipline (2.3) | — |

---

## Part 5: Anti-Patterns to Explicitly Prohibit

These are common agent behaviors that waste tokens or reduce quality. Consider adding explicit prohibitions to skills where you've seen these patterns:

```markdown
## Do NOT:
- Read an entire file when you need only a specific section
- Repeat the user's problem statement back to them before answering
- Explain your reasoning process unless the user asks for it
- Generate a complete file when only a diff is needed
- Run the full test suite when a targeted test would suffice
- Ask the user for information you can determine from the code
- Present multiple alternative approaches when one is clearly best
  (save alternatives for genuinely ambiguous situations)
- Read the same file twice in one procedure (cache the content mentally)
- Produce markdown-heavy output with headers, horizontal rules, and
  formatting when the content is 2-3 sentences
```

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────┐
│        SKILL ENGINEERING PATTERNS                    │
├─────────────────────────────────────────────────────┤
│                                                      │
│  QUALITY                                             │
│  1.1 Pre-flight context ........ Know before you act │
│  1.2 Convention mirroring ...... Match existing style │
│  1.3 Output contracts .......... Define "good" output│
│  1.4 Self-verification ......... Check your own work │
│  1.5 Confidence signaling ...... Rate your certainty │
│  1.6 Negative space ............ Show what you ruled │
│                                        out           │
│  EFFICIENCY                                          │
│  2.1 Targeted file reading ..... Read only what's    │
│                                       needed         │
│  2.2 Progressive detail ........ Shallow then deep   │
│  2.3 Output token discipline ... Say less, mean more │
│  2.4 Structured handoffs ....... JSON between skills │
│  2.5 Early termination ......... Exit when answered  │
│  2.6 Cache-friendly ordering ... Stable prefix       │
│                                                      │
│  TOOL INTELLIGENCE                                   │
│  3.1 Tool selection heuristics.. Right tool, right   │
│                                       job            │
│  3.2 Batched tool calls ........ One call, many ops  │
│  3.3 Pre-flight validation ..... Cheap checks first  │
│  3.4 Fallback chains ........... Plan B, C, D        │
│  3.5 Output parsing discipline.. Filter at source    │
│  3.6 Capability detection ...... Know your tools     │
│  3.7 Incremental verification .. Verify per change   │
│                                                      │
└─────────────────────────────────────────────────────┘
```
