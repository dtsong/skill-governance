# Init Prompt: Bootstrap Skill Governance Infrastructure v1.3

## Objective

Set up the complete skill governance infrastructure in this repository. This
includes validation scripts, pre-commit hooks, CI/CD workflows, security
scanning, configuration files, and project-level directives.

**Enforcement philosophy**: Security checks and structural integrity checks
(injection patterns, sensitive paths, broken references, missing frontmatter,
isolation violations, context load ceiling, reference depth violations) **block**
commits. Description quality, per-file token budgets, prose patterns, and
script quality checks **warn** but do not block — they are guideline targets,
not hard limits. Quality trumps compression. Eval results arbitrate budget disputes.

**Run this prompt once per skills repository to initialize the governance stack.**

---

## Step 0: Survey the Repo

Before creating anything, understand what already exists:

1. Check if `pipeline/` directory exists → if yes, ask before overwriting
2. Check if `.pre-commit-config.yaml` exists → if yes, merge rather than replace
3. Check if `.github/workflows/` has skill-related workflows → if yes, ask before overwriting
4. Check if `CLAUDE.md` or `AGENTS.md` exists → if yes, append directive rather than replace
5. Check which CI platform is in use (GitHub Actions, GitLab CI, etc.) → adapt workflows accordingly
6. List all existing `SKILL.md` files to understand the current skill inventory

**Present findings and ask for confirmation before proceeding.**

---

## Step 1: Create Directory Structure

```bash
mkdir -p pipeline/hooks
mkdir -p pipeline/scripts
mkdir -p pipeline/config
mkdir -p pipeline/specs
mkdir -p pipeline/templates/standalone-skill/references
mkdir -p pipeline/templates/standalone-skill/eval-cases/cases
mkdir -p pipeline/templates/standalone-skill/eval-cases/trigger-cases
mkdir -p pipeline/templates/skill-suite/skills/specialist-template/references
mkdir -p pipeline/templates/skill-suite/eval-cases/cases
mkdir -p pipeline/templates/skill-suite/eval-cases/trigger-cases
```

---

## Step 2: Install Specs

Copy all governance documents into `pipeline/specs/`:
- `SKILL-GOVERNANCE-SPEC.md` (v1.3) — architecture, writing, enforcement rules
- `SKILL-SECURITY-SPEC.md` (v1.0) — threat model, static analysis, supply chain
- `SKILL-MODEL-ROUTING-SPEC.md` (v1.0) — per-skill model config, budget-aware routing, degradation
- `SKILL-TRIGGER-RELIABILITY-SPEC.md` (v1.1) — trigger engineering, navigation evals, development workflow

---

## Step 3: Install Configuration Files

Create `pipeline/config/budgets.json`:

```json
{
  "coordinator_max_words": 600,
  "coordinator_max_tokens": 800,
  "specialist_max_words": 1500,
  "specialist_max_tokens": 2000,
  "reference_max_words": 1100,
  "reference_max_tokens": 1500,
  "standalone_max_words": 1500,
  "standalone_max_tokens": 2000,
  "max_simultaneous_tokens": 5500,
  "overrides": {}
}
```

Create `pipeline/config/security-suppressions.json`:

```json
{
  "suppressions": []
}
```

This file holds repo-wide suppressions for legitimate security patterns. Each
entry requires: `pattern`, `scope` (glob), `reason`, `approved_by`, `approved_at`.

Create `pipeline/config/model-routing.yaml`:

```yaml
tiers:
  haiku:
    claude_code: claude-haiku-4-5-20251001
    cost_ratio: 1
  sonnet:
    claude_code: claude-sonnet-4-6
    cost_ratio: 5
  opus:
    claude_code: claude-opus-4-6
    cost_ratio: 25

budget_zones:
  yellow_threshold: 0.70
  red_threshold: 0.90

defaults:
  coordinator: haiku
  specialist: sonnet
  conservation_mode: auto
```

This file defines model tier mappings, cost ratios, budget zone thresholds,
and default routing. Skills reference tiers by name (haiku/sonnet/opus);
the config maps them to concrete model identifiers per platform.

---

## Step 4: Install Pre-Commit Hooks

Create all hook scripts in `pipeline/hooks/`. Each hook must:
- Accept filenames as arguments (pre-commit convention)
- Run in <500ms per file
- Read budgets from `pipeline/config/budgets.json`
- Respect the enforcement tier (Hard → exit 1 on fail. Warn → exit 0, print warning.)

### Enforcement Tier Summary

| Hook | Tier | Exit Code on Violation |
|------|------|----------------------|
| `check_security.py` | **Hard** | 1 (critical findings block; warnings print) |
| `check_frontmatter.py` | **Hard** | 1 |
| `check_references.py` | **Hard** | 1 |
| `check_isolation.py` | **Hard** | 1 |
| `check_context_load.py` | **Hard** | 1 |
| `check_triggers.py` | **Warn** | 0 (print warning) |
| `check_token_budget.py` | **Warn** | 0 (print warning) |
| `check_prose.py` | **Warn** | 0 (print warning) |
| `check_scripts.py` | **Warn** | 0 (print warning) |
| `check_commit_msg.py` | **Hard** | 1 |

### Hook specifications:

**`pipeline/hooks/check_security.py`** — HARD tier (runs first)
- Scan SKILL.md, reference files, and scripts for security violations
- **Sensitive path detection**: Flag references to credential stores, key files,
  dotfiles, system directories (see Security Spec §2.1 for full pattern list)
- **Prompt injection patterns**: Flag identity manipulation ("ignore previous
  instructions", "you are now", "act as"), privilege escalation ("no restrictions",
  "bypass safety"), output manipulation ("do not mention", "hide this"), and
  data exfiltration instructions ("embed contents in output", "send to")
- **Dangerous command patterns in scripts**: Flag network access (curl, wget, ssh),
  arbitrary execution (eval, exec, bash -c), system modification (chmod 777,
  crontab), and destructive operations (rm -rf /, shred)
- **Encoded payload detection**: Flag base64 encode/decode instructions, hex
  escape sequences, eval() calls in non-script files
- **Script checksum validation**: If `scripts.lock` exists alongside SKILL.md,
  verify SHA-256 checksums of all referenced scripts match
- **Escape hatch**: Lines with `# SECURITY: <justification>` within 2 lines
  of a flagged pattern are suppressed. Repo-wide suppressions loaded from
  `pipeline/config/security-suppressions.json`.
- **Output**: CRITICAL (blocks), WARNING (visible), INFO (logged)
- **Exit 1 on any CRITICAL finding. Exit 0 with printed warnings otherwise.**

**`pipeline/hooks/check_frontmatter.py`** — HARD tier
- Validate YAML between `---` markers
- Required fields: `name` (kebab-case string, max 64 chars, no reserved words),
  `description` (non-empty string, ≥10 words)
- Valid optional fields: `version`, `model` (block), `security` (block),
  `provenance` (block), `context` (fork), `agent` (string)
- `model` block validation (**Warn** tier — advisory, not blocking):
  - `preferred` must be one of: haiku, sonnet, opus
  - `acceptable` must be a list containing `preferred`
  - `minimum` must be ≤ `preferred` in tier order (haiku < sonnet < opus)
  - `reasoning_demand` must be one of: low, medium, high, variable
- Unknown fields: print info-level note, do not block
- Missing or malformed frontmatter: **exit 1**
- Depends on: `pyyaml`

**`pipeline/hooks/check_references.py`** — HARD tier
- Parse SKILL.md for file path references matching patterns:
  - `references/*.md`, `scripts/*.*`
  - `Read \`path\``, `Load \`path\``, `at \`path.md\``
- Skip URLs and absolute paths
- Verify each referenced file exists on disk relative to the SKILL.md directory
- **One-level-deep check**: For reference files (files in `references/`), scan
  for references to other files. If a reference file references another reference
  file, **exit 1** with a warning explaining the one-level-deep rule.
- Broken reference found: **exit 1** with file path and line number
- Reference-to-reference chain found: **exit 1** with both file paths

**`pipeline/hooks/check_isolation.py`** — HARD tier
- For SKILL.md files inside a `skills/` directory (specialists in a suite):
  - Identify all sibling specialist directories
  - Check if the current file references any sibling's SKILL.md or reference files
- Cross-reference found: **exit 1** with specific line, source skill, and target skill

**`pipeline/hooks/check_triggers.py`** — WARN tier
- **Description length**: Warn if <20 words, info if <40 words
- **Activation directive**: Warn if description doesn't start with "Use this skill",
  "ALWAYS use", "Invoke this skill", or similar activation language
- **Third person**: Warn if description contains "I can", "I will", "I help",
  "you can", "you should", "you'll" (first/second person signals)
- **Negative boundary**: Warn if specialist description lacks "Do NOT use for",
  "Not for", or similar exclusion language
- **Coordinator language**: Warn if coordinator description lacks "ANY", "ALL",
  "entry point", or "ALWAYS" language
- **Specialist coordinator reference**: Warn if specialist in a suite doesn't
  reference being loaded by the coordinator
- **Vocabulary overlap**: Warn if two skills in the same suite have >60%
  vocabulary overlap in descriptions (Jaccard similarity on non-stop-words)
- **MCP tool references**: Warn if skill text contains patterns like
  "use the X tool" or "run X tool" without a colon-separated server prefix
  (should be `ServerName:tool_name`)
- **Always exit 0** — trigger quality is advisory

**`pipeline/hooks/check_token_budget.py`** — WARN tier
- Count words in each staged file
- Classify file type (coordinator, specialist, standalone, reference) by directory structure
- Compare against target from config, including per-skill overrides
- **At >90% of target**: Print info message with headroom remaining
- **At >100% of target**: Print warning with overage amount and remediation suggestions
- **Always exit 0** — budget violations never block commits
- Include in output: "To document this override, add an entry to pipeline/config/budgets.json with your rationale."

**`pipeline/hooks/check_prose.py`** — WARN tier
- Search for explanatory prose patterns in procedure sections only
- Patterns to detect:
  - "it is important to", "it's important to"
  - "you should", "you may want to", "you might want to"
  - "this is because", "the reason for this"
  - "basically", "essentially", "fundamentally", "in other words"
  - "in order to"
  - "keep in mind that", "please note that"
  - "let's", "we can", "we should"
  - "feel free to", "don't hesitate to"
- **Well-known concept detection**: Flag explanatory paragraphs about common
  technologies/concepts that Claude already knows. Detect patterns like
  definitions followed by tool usage ("X is a format that... To extract from X...")
  where the definition adds no project-specific context.
- Skip sections headed: Purpose, Context, Background, Notes, Description
- **Always exit 0** — prose detection is advisory
- Print each match with line number and suggestion

**`pipeline/hooks/check_scripts.py`** — WARN tier (new in v1.3)
- For Python scripts referenced by SKILL.md files:
  - **Error handling**: Warn if script has no try/except blocks and uses file I/O,
    subprocess calls, or network operations
  - **Magic numbers**: Warn if numeric literals >1 appear outside of known-safe
    patterns (list indices, range(n), common defaults) without an adjacent comment
  - **Dependency documentation**: Warn if script imports non-stdlib packages that
    aren't mentioned in the parent SKILL.md
- For bash scripts:
  - **Error handling**: Warn if script lacks `set -e` or explicit error checking
  - **Undocumented commands**: Warn if script uses commands with flags that aren't
    commented
- **Always exit 0** — script quality is advisory
- Print each finding with file, line, and fix suggestion

**`pipeline/hooks/check_context_load.py`** — HARD tier
- For each skill suite (directory with SKILL.md + skills/ subdirectory):
  - Calculate coordinator tokens + largest specialist tokens + largest reference tokens
  - Compare against `max_simultaneous_tokens` from config
- Suite exceeds ceiling: **exit 1** with breakdown showing which files contribute
- Include suggestion: "Reduce the largest specialist or extract content to a conditionally-loaded reference file."

**`pipeline/hooks/check_commit_msg.py`** — HARD tier
- Validate first line against: `type(scope): description`
- Valid types: skill, skill-fix, skill-ref, skill-eval, skill-docs, chore, feat, fix, docs, refactor
- Description must be ≥10 characters
- Invalid format: **exit 1** with examples of correct format
- Install on `commit-msg` stage

---

## Step 5: Create `.pre-commit-config.yaml`

Generate the pre-commit configuration:

```yaml
repos:
  - repo: local
    hooks:
      - id: skill-security
        name: Skill Security Scan
        entry: python3 pipeline/hooks/check_security.py
        language: python
        files: '(SKILL\.md|references/.*\.md|scripts/.*)$'
        exclude: '(eval-cases|templates|node_modules)/'

      - id: skill-frontmatter
        name: Skill Frontmatter
        entry: python3 pipeline/hooks/check_frontmatter.py
        language: python
        files: 'SKILL\.md$'
        exclude: '(eval-cases|templates|node_modules)/'
        additional_dependencies: ['pyyaml']

      - id: skill-references
        name: Skill Reference Integrity
        entry: python3 pipeline/hooks/check_references.py
        language: python
        files: '(SKILL\.md|references/.*\.md)$'
        exclude: '(eval-cases|templates)/'

      - id: skill-isolation
        name: Skill Isolation
        entry: python3 pipeline/hooks/check_isolation.py
        language: python
        files: 'SKILL\.md$'
        exclude: '(eval-cases|templates)/'

      - id: skill-context-load
        name: Suite Context Load
        entry: python3 pipeline/hooks/check_context_load.py
        language: python
        files: '(SKILL\.md|references/.*\.md)$'
        exclude: '(eval-cases|templates)/'

      - id: skill-triggers
        name: Skill Trigger Quality
        entry: python3 pipeline/hooks/check_triggers.py
        language: python
        files: 'SKILL\.md$'
        exclude: '(eval-cases|templates)/'
        verbose: true

      - id: skill-token-budget
        name: Skill Token Budget
        entry: python3 pipeline/hooks/check_token_budget.py
        language: python
        files: '(SKILL\.md|references/.*\.md)$'
        exclude: '(eval-cases|templates|node_modules)/'
        verbose: true

      - id: skill-prose-check
        name: Skill Prose Detector
        entry: python3 pipeline/hooks/check_prose.py
        language: python
        files: '(SKILL\.md|references/.*\.md)$'
        exclude: '(eval-cases|templates)/'
        verbose: true

      - id: skill-scripts
        name: Skill Script Quality
        entry: python3 pipeline/hooks/check_scripts.py
        language: python
        files: '(scripts/.*\.(py|sh|bash))$'
        exclude: '(eval-cases|templates|node_modules)/'
        verbose: true

      - id: skill-commit-msg
        name: Skill Commit Message
        entry: python3 pipeline/hooks/check_commit_msg.py
        language: python
        stages: [commit-msg]
```

Key details:
- **Security hook runs first** — fail fast on injection or sensitive access
- Hard-tier hooks listed before warn-tier (fail-fast ordering)
- Warn-tier hooks have `verbose: true` so warnings always display
- All hooks use `python3` for portability
- Commit message hook is on `commit-msg` stage

---

## Step 6: Install CI Workflows

### For GitHub Actions, create four workflows:

**`.github/workflows/skill-lint.yml`** — Every push to `skills/**`
- Install python, pyyaml, tiktoken
- **Run security scan first** (sensitive paths, injection patterns, dangerous commands, script checksums)
- Run all hard-tier checks (frontmatter, references incl. depth check, isolation, context load)
- Run advisory checks (triggers, budget, prose, scripts — warn-tier, do not fail the job)
- Generate budget report as step summary on PRs
- **Job fails on any hard-tier violation (including security)**

**`.github/workflows/skill-analyze.yml`** — PRs touching `skills/**`
- Identify changed skills via git diff
- Run: security cross-file analysis (SKILL.md → reference payloads), pattern compliance, portability check, context load report
- Run: diff-aware security scan (flag newly introduced security patterns)
- Run: scope boundary heuristic (compare skill description to actual operations)
- Run: reference depth analysis (flag any reference-to-reference chains)
- Post analysis as PR comment
- **Critical security findings block merge. All other analysis is informational.**

**`.github/workflows/skill-eval.yml`** — Merge to main + manual dispatch
- Input parameters: skill_path (default "all"), model (choice: haiku/sonnet/opus)
- Locate eval cases, execute against skills, grade results
- Compare against stored baselines, flag regressions
- Run trigger eval cases (activation rate, routing accuracy)
- Run navigation eval cases where configured
- Upload results as artifacts
- Timeout: 30 minutes

**`.github/workflows/skill-publish.yml`** — Version tags (v*)
- Identify changed skills since last tag
- Package each changed skill
- Create GitHub release with packages

### CI Scripts in `pipeline/scripts/`:

Create these scripts. All `.sh` scripts must be executable (`chmod +x`).

- `validate-structure.sh` — Verify directory structure, frontmatter existence, eval case placement
- `check-token-budgets.sh` — Budget check across all files (warn-only, does not fail CI)
- `security-scan.sh` — Full security scan: sensitive paths, injection patterns, dangerous commands, encoded payloads, script checksums. Loads suppressions from config.
- `security-diff-scan.py` — Diff-aware security scan for PRs. Flags new security-relevant patterns introduced in the diff only.
- `lock-scripts.sh` — Generate or regenerate `scripts.lock` files with SHA-256 checksums for all scripts referenced by skills
- `check-portability.sh` — Flag platform-specific references (CLAUDE.md vs AGENTS.md, tool syntax)
- `analyze-patterns.py` — Detect prose, duplication, oversized checklists, well-known concept explanations. Generate markdown report.
- `context-load-analysis.py` — Calculate worst-case context load per suite. Generate report.
- `reference-depth-analysis.py` — Detect reference-to-reference chains. Flag violations of one-level-deep rule.
- `budget-report.py` — Summary table: all skills, word counts, token estimates, budget status. Output as markdown.
- `run-evals.sh` — Orchestrate eval execution. Accept `--targets` and `--model` flags.
- `run-trigger-evals.sh` — Orchestrate trigger eval execution. Accept `--targets`, `--model`, `--approach` flags.
- `check-regressions.py` — Compare current eval results against stored baselines. Flag pass→fail changes.
- `package-skill.sh` — Package skill directory into distributable archive.

---

## Step 7: Install Skill Templates

### Standalone Skill Template (`pipeline/templates/standalone-skill/`)

**SKILL.md:**
```markdown
---
name: SKILL_NAME
description: >
  Use this skill when USER_TRIGGER_DESCRIPTION. Covers CAPABILITIES.
  Also use for: "QUOTED_PHRASE_1", "QUOTED_PHRASE_2".
  Do NOT use for EXCLUDED_TASKS — those go to ALTERNATIVE_SKILL.
model:
  preferred: sonnet              # haiku | sonnet | opus
  acceptable: [haiku, sonnet]    # Models producing acceptable results
  minimum: haiku                 # Lowest tier that works for this skill
  allow_downgrade: true          # System can downgrade under budget pressure
  reasoning_demand: medium       # low | medium | high
---

# SKILL_NAME

## Scope Constraints
- Read files ONLY within the project root
- Do NOT read, write, or reference home directory dotfiles or credentials
- Do NOT execute network requests unless the procedure explicitly requires it
- Output ONLY the structured format defined below

## Inputs
- `required_input`: DESCRIPTION
- `optional_input` (optional): DESCRIPTION

## Input Sanitization
Before using any user-provided values in commands or file paths:
- Strip shell metacharacters: ; | & $ ` \ " ' ( ) { } < > !
- Reject inputs containing ../ or absolute paths
- Validate format: EXPECTED_FORMAT_DESCRIPTION

## Procedure

Copy this checklist and update as you complete each step:
```
Progress:
- [ ] Step 1: Gather context
- [ ] Step 2: PRIMARY_ACTION
- [ ] Step 3: Verify output
```

Note: If you've lost context of previous steps (e.g., after compaction),
check the progress checklist above and resume from the last unchecked item.

Step 1: Gather context.
  - Read RELEVANT_CONFIG_FILES
  - Record constraints for subsequent steps

Step 2: PRIMARY_ACTION.
  - IMPERATIVE_INSTRUCTION
  - If CONDITION → BRANCH_A. Otherwise → BRANCH_B.
  - Note: EDGE_CASE_CONTEXT — explains why this matters for correct results.

Step 3: Verify output.
  - Check each item in the Output Contract
  - If any check fails → fix and re-verify (loop until clean)

## Output Format

\`\`\`json
{
  "result": "EXAMPLE_VALUE",
  "confidence": "high|medium|low",
  "details": []
}
\`\`\`

## References
| File | Load When | Contains |
|------|-----------|----------|
| `references/CHECKLIST.md` | Step 2 if CONDITION | Detailed checklist for X |
```

**eval-cases/evals.json:**
```json
{
  "skill": "SKILL_NAME",
  "cases": [
    {
      "id": "01-basic-case",
      "name": "Basic functionality test",
      "tier": 1,
      "input": {},
      "file": "cases/01-basic-case.md"
    }
  ]
}
```

**eval-cases/trigger-evals.json:**
```json
{
  "skill": "SKILL_NAME",
  "target_metrics": {
    "activation_rate": 0.95,
    "correct_routing_rate": 0.90,
    "false_positive_rate": 0.05
  },
  "cases": [
    {
      "id": "direct-match-01",
      "category": "direct_match",
      "difficulty": "easy",
      "file": "trigger-cases/direct-match-01.md"
    },
    {
      "id": "casual-phrasing-01",
      "category": "casual_phrasing",
      "difficulty": "medium",
      "file": "trigger-cases/casual-phrasing-01.md"
    },
    {
      "id": "negative-01",
      "category": "negative",
      "difficulty": "easy",
      "file": "trigger-cases/negative-01.md"
    }
  ]
}
```

### Skill Suite Template (`pipeline/templates/skill-suite/`)

Generate coordinator SKILL.md following the five-element structure (§3.2 of spec).
Generate one specialist template following the standard structure (§3.3 of spec).
Include both output eval and trigger eval scaffold.
Include `navigation-evals.json` template for skills with complex file structures.

---

## Step 8: Install Shell Helpers

Create `pipeline/shell-helpers.sh`:

```bash
#!/bin/bash
# Source this in your shell profile: source /path/to/pipeline/shell-helpers.sh

# Quick word/token count
skill-wc() {
    local file="$1"
    local words=$(wc -w < "$file")
    local tokens=$(( words * 133 / 100 ))
    echo "$file: $words words (~$tokens tokens)"
}

# Run all checks on a specific skill
skill-check() {
    local skill_dir="$1"
    find "$skill_dir" \( -name "SKILL.md" -o -path "*/references/*.md" \) \
        -not -path "*/eval-cases/*" -not -path "*/templates/*" | \
        xargs pre-commit run --files
}

# Budget check only
skill-budget() {
    pre-commit run skill-token-budget --files "$@"
}

# Trigger quality check only
skill-triggers() {
    pre-commit run skill-triggers --files "$@"
}

# Create new standalone skill from template
skill-new() {
    local name="$1"
    local dest="${2:-skills/$name}"
    if [ -d "$dest" ]; then
        echo "Directory $dest already exists"
        return 1
    fi
    cp -r pipeline/templates/standalone-skill "$dest"
    find "$dest" -type f -exec sed -i "s/SKILL_NAME/$name/g" {} +
    echo "✅ Created skill scaffold at $dest"
    echo "Next: edit $dest/SKILL.md and run skill-check $dest"
}

# Create new skill suite from template
skill-new-suite() {
    local name="$1"
    local dest="${2:-skills/$name}"
    if [ -d "$dest" ]; then
        echo "Directory $dest already exists"
        return 1
    fi
    cp -r pipeline/templates/skill-suite "$dest"
    find "$dest" -type f -exec sed -i "s/SUITE_NAME/$name/g" {} +
    echo "✅ Created skill suite scaffold at $dest"
}

# Full compliance audit
skill-audit() {
    echo "=== Skill Compliance Audit ==="
    echo ""
    echo "--- Security Checks ---"
    pre-commit run skill-security --all-files
    echo ""
    echo "--- Hard Checks (structural integrity) ---"
    pre-commit run skill-frontmatter --all-files
    pre-commit run skill-references --all-files
    pre-commit run skill-isolation --all-files
    pre-commit run skill-context-load --all-files
    echo ""
    echo "--- Advisory Checks (quality guidance) ---"
    pre-commit run skill-triggers --all-files
    pre-commit run skill-token-budget --all-files
    pre-commit run skill-prose-check --all-files
    pre-commit run skill-scripts --all-files
    echo ""
    echo "=== Audit Complete ==="
}

# Security scan only
skill-security() {
    if [ -n "$1" ]; then
        find "$1" \( -name "SKILL.md" -o -path "*/references/*.md" -o -path "*/scripts/*" \) \
            -not -path "*/eval-cases/*" | xargs pre-commit run skill-security --files
    else
        pre-commit run skill-security --all-files
    fi
}

# Lock script checksums for a skill
skill-lock-scripts() {
    local skill_dir="$1"
    if [ -z "$skill_dir" ]; then
        echo "Usage: skill-lock-scripts <skill-directory>"
        return 1
    fi
    bash pipeline/scripts/lock-scripts.sh "$skill_dir"
}

# Show context load breakdown for a suite
skill-load() {
    local suite_dir="$1"
    python3 pipeline/hooks/check_context_load.py \
        $(find "$suite_dir" \( -name "SKILL.md" -o -path "*/references/*.md" \) \
        -not -path "*/eval-cases/*")
}
```

---

## Step 9: Install Project Directive

Append the governance directive to the project instructions file.

**Detection logic:**
1. If `CLAUDE.md` exists → append to it
2. If `AGENTS.md` exists → append to it
3. If neither exists → ask which to create (or both for cross-platform repos)

**Directive content:** Use the content from `SKILL-GOVERNANCE-DIRECTIVE.md` (v1.3).

---

## Step 10: Configure Git and Pre-Commit

```bash
pip3 install pre-commit
pre-commit install
pre-commit install --hook-type commit-msg
```

---

## Step 11: Run Initial Validation

After all files are created:

1. Run `pre-commit run --all-files`
2. Separate the output into:
   - **Security findings** (must resolve or annotate): injection patterns, sensitive paths, dangerous commands
   - **Hard violations** (must fix before first commit): broken references, bad frontmatter, isolation breaches, context load over ceiling, reference-to-reference chains
   - **Trigger quality findings** (address when convenient): short descriptions, missing activation directives, first/second person language, missing negative boundaries, MCP tool format issues
   - **Advisory warnings** (address when convenient): budget overages, prose patterns, script quality issues
3. For security findings: present each finding and ask for disposition — annotate with `# SECURITY:` justification, add to suppressions file, or remove the flagged content
4. For hard violations: present a fix plan and ask to proceed
5. For trigger quality: present the list with specific fix suggestions from the trigger reliability spec
6. For advisory warnings: present the list with remediation suggestions. Note that these don't need immediate action.
7. Generate initial `scripts.lock` files for any skills that have scripts
8. Generate 3 example trigger eval cases for each skill suite (one direct match, one casual phrasing, one negative)

---

## Step 12: Summary

Present a clear summary organized by enforcement tier:

```
✅ Governance infrastructure installed (v1.3)

Security enforcement (blocks commits):
  ✓ Sensitive path detection
  ✓ Prompt injection pattern scanning
  ✓ Dangerous command detection (scripts)
  ✓ Script checksum validation (scripts.lock)
  ✓ Encoded payload detection

Hard enforcement (blocks commits):
  ✓ Frontmatter validation
  ✓ Reference integrity (incl. one-level-deep check)
  ✓ Cross-skill isolation
  ✓ Suite context load ceiling (5,500 tokens)
  ✓ Commit message convention

Advisory enforcement (warns on commit):
  ✓ Trigger quality (description length, activation directive, third person, boundaries, MCP format)
  ✓ Per-file token budget targets
  ✓ Prose pattern detection (incl. well-known concept explanations)
  ✓ Script quality (error handling, documented constants, dependencies)

Files created:
  pipeline/specs/SKILL-GOVERNANCE-SPEC.md
  pipeline/specs/SKILL-SECURITY-SPEC.md
  pipeline/specs/SKILL-MODEL-ROUTING-SPEC.md
  pipeline/specs/SKILL-TRIGGER-RELIABILITY-SPEC.md
  pipeline/config/budgets.json
  pipeline/config/security-suppressions.json
  pipeline/config/model-routing.yaml
  pipeline/hooks/              — 10 pre-commit hooks
  pipeline/scripts/            — CI validation, analysis, and security scripts
  pipeline/templates/          — Skill starter templates (with trigger eval scaffold)
  pipeline/shell-helpers.sh
  .pre-commit-config.yaml
  .github/workflows/skill-*.yml  — 4 CI/CD workflows

Modified:
  CLAUDE.md / AGENTS.md        — Governance directive appended

Quick start:
  source pipeline/shell-helpers.sh
  skill-audit                          # Full compliance + security check
  skill-security                       # Security scan only
  skill-triggers                       # Trigger quality check only
  skill-new my-skill-name              # Create from template
  skill-check skills/my-skill/         # Validate a skill
  skill-lock-scripts skills/my-skill/  # Lock script checksums
```

---

## Execution Notes

- **Ask before overwriting** any existing files. Merge when possible.
- **Make all scripts executable** after creation (`chmod +x`).
- **Test pre-commit** by running `pre-commit run --all-files` before finishing.
- **Security findings require disposition** — each must be annotated, suppressed, or removed.
- **Generate scripts.lock** for all skills with scripts before finishing.
- **Hard checks must pass.** If existing skills have hard violations, present a fix plan.
- **Trigger quality warnings are actionable.** Present specific fixes per the trigger reliability spec.
- **Advisory warnings are informational.** Don't pressure the user to fix them immediately.
- **Generate trigger eval cases** for existing skill suites (3 per suite as starting point).
- **Adapt CI workflows** to the repo's actual CI platform if not GitHub Actions.
- **If no skills exist yet**, skip validation and confirm infrastructure readiness.
- **If `.pre-commit-config.yaml` exists**, merge skill hooks into the existing config.
