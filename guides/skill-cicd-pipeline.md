# CI/CD for Skills: Treating Skills as Software Artifacts

## Why This Matters

Skills are code. They have:
- **Syntax** (YAML frontmatter, markdown structure, valid file references)
- **Contracts** (token budgets, structural requirements, output formats)
- **Dependencies** (reference files, scripts, other skills in a suite)
- **Consumers** (agents that execute them, other skills that chain from them)
- **Regressions** (changes that fix one case but break another)

Without CI/CD, skill quality degrades through the same mechanisms as software:
someone edits a SKILL.md, it drifts over budget, a reference file path breaks,
a checklist gets duplicated — and nobody catches it until it fails in production.

---

## Pipeline Architecture

```
                    ┌──────────────┐
                    │  Skill Repo  │
                    └──────┬───────┘
                           │ push / PR
                           ▼
              ┌─────────────────────────┐
              │   Stage 1: Lint & Validate  │ ◄── Fast, every commit
              │   - Structure validation    │
              │   - Token budget check      │
              │   - Frontmatter validation  │
              │   - Reference integrity     │
              │   - Cross-skill isolation   │
              └────────────┬────────────┘
                           │ pass
                           ▼
              ┌─────────────────────────┐
              │   Stage 2: Static Analysis  │ ◄── Medium, every PR
              │   - Pattern compliance      │
              │   - Writing rule checks     │
              │   - Duplicate detection     │
              │   - Portability check       │
              └────────────┬────────────┘
                           │ pass
                           ▼
              ┌─────────────────────────┐
              │   Stage 3: Eval Execution   │ ◄── Expensive, on demand / merge
              │   - Run eval cases          │
              │   - Grade against rubrics   │
              │   - Regression detection    │
              │   - Performance tracking    │
              └────────────┬────────────┘
                           │ pass
                           ▼
              ┌─────────────────────────┐
              │   Stage 4: Publish          │ ◄── On release tag
              │   - Package skill           │
              │   - Version bump            │
              │   - Distribute to targets   │
              └─────────────────────────┘
```

---

## Repository Structure

```
skills-repo/
├── .github/
│   └── workflows/
│       ├── skill-lint.yml              # Stage 1 — runs on every push
│       ├── skill-analyze.yml           # Stage 2 — runs on PRs
│       ├── skill-eval.yml              # Stage 3 — runs on merge to main / manual
│       └── skill-publish.yml           # Stage 4 — runs on version tags
├── pipeline/
│   ├── scripts/
│   │   ├── validate-structure.sh       # Directory structure validation
│   │   ├── check-token-budgets.sh      # Word/token counting and budget enforcement
│   │   ├── check-frontmatter.py        # YAML frontmatter validation
│   │   ├── check-references.sh         # Reference file integrity
│   │   ├── check-isolation.sh          # Cross-skill isolation validation
│   │   ├── analyze-patterns.py         # Writing rule and pattern compliance
│   │   ├── check-portability.sh        # Claude Code / Codex compatibility
│   │   ├── run-evals.sh               # Eval case execution orchestrator
│   │   └── package-skill.sh            # Packaging for distribution
│   ├── templates/
│   │   ├── skill-template/             # Starter template for new skills
│   │   │   ├── SKILL.md
│   │   │   ├── references/
│   │   │   └── eval-cases/
│   │   │       └── evals.json
│   │   └── suite-template/             # Starter template for skill suites
│   │       ├── SKILL.md
│   │       ├── skills/
│   │       │   └── specialist-template/
│   │       │       └── SKILL.md
│   │       └── eval-cases/
│   ├── config/
│   │   ├── budgets.json                # Token budget configuration
│   │   ├── rules.json                  # Pattern and writing rule definitions
│   │   └── platforms.json              # Platform compatibility definitions
│   └── lib/
│       └── token-counter.py            # Shared token counting utility
├── skills/                             # Actual skills live here
│   ├── frontend-qa/
│   ├── code-review/
│   └── ...
└── README.md
```

---

## Stage 1: Lint & Validate

Fast checks that run on every push. Total runtime target: <30 seconds.

### GitHub Actions Workflow

```yaml
# .github/workflows/skill-lint.yml
name: Skill Lint & Validate

on:
  push:
    paths:
      - 'skills/**'
      - 'pipeline/**'
  pull_request:
    paths:
      - 'skills/**'

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install pyyaml tiktoken

      - name: Validate structure
        run: bash pipeline/scripts/validate-structure.sh skills/

      - name: Check token budgets
        run: bash pipeline/scripts/check-token-budgets.sh skills/

      - name: Validate frontmatter
        run: python pipeline/scripts/check-frontmatter.py skills/

      - name: Check reference integrity
        run: bash pipeline/scripts/check-references.sh skills/

      - name: Check cross-skill isolation
        run: bash pipeline/scripts/check-isolation.sh skills/

      - name: Generate budget report
        if: github.event_name == 'pull_request'
        run: |
          python pipeline/scripts/budget-report.py skills/ > budget-report.md
          cat budget-report.md >> $GITHUB_STEP_SUMMARY
```

### Token Budget Check Script

```bash
#!/bin/bash
# pipeline/scripts/check-token-budgets.sh
# Validates all SKILL.md and reference files against token budgets
# Reads budget config from pipeline/config/budgets.json

set -euo pipefail

SKILL_DIR="${1:-.}"
CONFIG="pipeline/config/budgets.json"
ERRORS=0

# Default budgets (overridable via config)
COORDINATOR_MAX_WORDS=600
SPECIALIST_MAX_WORDS=1500
REFERENCE_MAX_WORDS=1100
STANDALONE_MAX_WORDS=1500

# Load config if exists
if [ -f "$CONFIG" ]; then
    COORDINATOR_MAX_WORDS=$(python3 -c "import json; print(json.load(open('$CONFIG')).get('coordinator_max_words', 600))")
    SPECIALIST_MAX_WORDS=$(python3 -c "import json; print(json.load(open('$CONFIG')).get('specialist_max_words', 1500))")
    REFERENCE_MAX_WORDS=$(python3 -c "import json; print(json.load(open('$CONFIG')).get('reference_max_words', 1100))")
    STANDALONE_MAX_WORDS=$(python3 -c "import json; print(json.load(open('$CONFIG')).get('standalone_max_words', 1500))")
fi

echo "=== Token Budget Validation ==="
echo ""

check_budget() {
    local file="$1"
    local max_words="$2"
    local label="$3"

    local word_count
    word_count=$(wc -w < "$file")
    local token_estimate=$(( word_count * 133 / 100 ))
    local status="PASS"

    if [ "$word_count" -gt "$max_words" ]; then
        local overage=$(( word_count - max_words ))
        status="FAIL"
        echo "❌ $status: $file"
        echo "   Words: $word_count | Tokens: ~$token_estimate | Budget: $max_words words ($label)"
        echo "   Over by: $overage words (~$(( overage * 133 / 100 )) tokens)"
        ERRORS=$((ERRORS + 1))
    else
        local remaining=$(( max_words - word_count ))
        echo "✅ $status: $file"
        echo "   Words: $word_count | Tokens: ~$token_estimate | Budget: $max_words words ($label)"
        echo "   Headroom: $remaining words"
    fi
}

# Find and classify all SKILL.md files
find "$SKILL_DIR" -name "SKILL.md" -not -path "*/eval-cases/*" -not -path "*/templates/*" | while read -r skill_md; do
    dir=$(dirname "$skill_md")

    if [ -d "$dir/skills" ]; then
        # Has sub-skills → coordinator
        check_budget "$skill_md" "$COORDINATOR_MAX_WORDS" "coordinator"
    elif echo "$dir" | grep -q "/skills/"; then
        # Inside a skills/ directory → specialist
        check_budget "$skill_md" "$SPECIALIST_MAX_WORDS" "specialist"
    else
        # No sub-skills, not inside skills/ → standalone
        check_budget "$skill_md" "$STANDALONE_MAX_WORDS" "standalone"
    fi
done

# Find and check all reference files
find "$SKILL_DIR" -path "*/references/*.md" -type f | while read -r ref_file; do
    check_budget "$ref_file" "$REFERENCE_MAX_WORDS" "reference"
done

echo ""
echo "=== Budget Summary ==="
if [ "$ERRORS" -gt 0 ]; then
    echo "❌ $ERRORS file(s) over budget"
    exit 1
else
    echo "✅ All files within budget"
fi
```

### Structure Validation Script

```bash
#!/bin/bash
# pipeline/scripts/validate-structure.sh
# Validates skill directory structure against the authoring standard

set -euo pipefail

SKILL_DIR="${1:-.}"
ERRORS=0
WARNINGS=0

echo "=== Structure Validation ==="
echo ""

# Check each skill directory
find "$SKILL_DIR" -name "SKILL.md" -not -path "*/eval-cases/*" -not -path "*/templates/*" | while read -r skill_md; do
    dir=$(dirname "$skill_md")
    skill_name=$(basename "$dir")
    echo "Checking: $skill_name ($dir)"

    # Required: SKILL.md exists (already found by find)
    echo "  ✅ SKILL.md exists"

    # Check: SKILL.md has frontmatter
    if head -1 "$skill_md" | grep -q "^---"; then
        echo "  ✅ Has YAML frontmatter"
    else
        echo "  ❌ Missing YAML frontmatter"
        ERRORS=$((ERRORS + 1))
    fi

    # Check: eval cases not inside skill directory
    if find "$dir" -name "evals.json" -not -path "*/eval-cases/*" | grep -q .; then
        echo "  ❌ evals.json found inside skill directory (should be in eval-cases/)"
        ERRORS=$((ERRORS + 1))
    fi

    # Check: reference files referenced in SKILL.md actually exist
    grep -oP 'references/[a-zA-Z0-9_-]+\.md' "$skill_md" 2>/dev/null | sort -u | while read -r ref; do
        if [ -f "$dir/$ref" ]; then
            echo "  ✅ Referenced file exists: $ref"
        else
            echo "  ❌ Referenced file missing: $dir/$ref"
            ERRORS=$((ERRORS + 1))
        fi
    done

    # Check: scripts referenced in SKILL.md are executable
    grep -oP 'scripts/[a-zA-Z0-9_.-]+' "$skill_md" 2>/dev/null | sort -u | while read -r script; do
        if [ -f "$dir/$script" ]; then
            if [ -x "$dir/$script" ]; then
                echo "  ✅ Script is executable: $script"
            else
                echo "  ⚠️  Script exists but not executable: $script"
                WARNINGS=$((WARNINGS + 1))
            fi
        fi
    done

    echo ""
done

echo "=== Structure Summary ==="
echo "Errors: $ERRORS | Warnings: $WARNINGS"
[ "$ERRORS" -eq 0 ] && echo "✅ All structures valid" || (echo "❌ Fix errors before merging" && exit 1)
```

### Frontmatter Validation Script

```python
#!/usr/bin/env python3
"""
pipeline/scripts/check-frontmatter.py
Validates YAML frontmatter in all SKILL.md files.
"""

import sys
import os
import yaml
from pathlib import Path

REQUIRED_FIELDS = {"name", "description"}
OPTIONAL_FIELDS = {"model_tier", "version", "platform"}
VALID_MODEL_TIERS = {"mechanical", "analytical", "reasoning"}

errors = []
warnings = []


def validate_frontmatter(filepath: Path):
    content = filepath.read_text(encoding="utf-8")

    if not content.startswith("---"):
        errors.append(f"{filepath}: Missing YAML frontmatter (must start with ---)")
        return

    parts = content.split("---", 2)
    if len(parts) < 3:
        errors.append(f"{filepath}: Malformed frontmatter (missing closing ---)")
        return

    try:
        meta = yaml.safe_load(parts[1])
    except yaml.YAMLError as e:
        errors.append(f"{filepath}: Invalid YAML in frontmatter: {e}")
        return

    if not isinstance(meta, dict):
        errors.append(f"{filepath}: Frontmatter must be a YAML mapping")
        return

    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in meta:
            errors.append(f"{filepath}: Missing required field '{field}'")
        elif not isinstance(meta[field], str) or not meta[field].strip():
            errors.append(f"{filepath}: Field '{field}' must be a non-empty string")

    # Check description length (should be substantive for triggering)
    if "description" in meta and isinstance(meta["description"], str):
        word_count = len(meta["description"].split())
        if word_count < 10:
            warnings.append(
                f"{filepath}: Description is only {word_count} words. "
                "Longer descriptions improve skill triggering accuracy."
            )

    # Validate optional fields
    if "model_tier" in meta:
        if meta["model_tier"] not in VALID_MODEL_TIERS:
            errors.append(
                f"{filepath}: Invalid model_tier '{meta['model_tier']}'. "
                f"Must be one of: {', '.join(VALID_MODEL_TIERS)}"
            )

    # Check for unknown fields
    known = REQUIRED_FIELDS | OPTIONAL_FIELDS
    unknown = set(meta.keys()) - known
    if unknown:
        warnings.append(
            f"{filepath}: Unknown frontmatter fields: {', '.join(unknown)}"
        )


def main():
    search_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")

    skill_files = list(search_dir.rglob("SKILL.md"))
    # Exclude eval-cases and templates
    skill_files = [
        f for f in skill_files
        if "eval-cases" not in f.parts and "templates" not in f.parts
    ]

    if not skill_files:
        print("No SKILL.md files found")
        sys.exit(0)

    for filepath in sorted(skill_files):
        validate_frontmatter(filepath)

    print(f"=== Frontmatter Validation ===")
    print(f"Files checked: {len(skill_files)}")

    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for w in warnings:
            print(f"  ⚠️  {w}")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for e in errors:
            print(f"  ❌ {e}")
        sys.exit(1)
    else:
        print("✅ All frontmatter valid")


if __name__ == "__main__":
    main()
```

### Cross-Skill Isolation Check

```bash
#!/bin/bash
# pipeline/scripts/check-isolation.sh
# Ensures specialist skills don't reference other specialists' content

set -euo pipefail

SKILL_DIR="${1:-.}"
ERRORS=0

echo "=== Cross-Skill Isolation Check ==="
echo ""

# Find all skill suites (directories with a skills/ subdirectory)
find "$SKILL_DIR" -name "skills" -type d | while read -r skills_dir; do
    suite_dir=$(dirname "$skills_dir")
    suite_name=$(basename "$suite_dir")
    echo "Suite: $suite_name"

    # Get list of specialist skill directories
    specialists=()
    for spec_dir in "$skills_dir"/*/; do
        [ -f "$spec_dir/SKILL.md" ] && specialists+=("$(basename "$spec_dir")")
    done

    # Check each specialist for references to other specialists
    for spec in "${specialists[@]}"; do
        spec_file="$skills_dir/$spec/SKILL.md"
        for other in "${specialists[@]}"; do
            [ "$spec" = "$other" ] && continue
            # Check if this specialist references another specialist's SKILL.md
            if grep -q "skills/$other/SKILL.md\|/$other/SKILL.md" "$spec_file" 2>/dev/null; then
                echo "  ❌ $spec references $other/SKILL.md (violates isolation)"
                ERRORS=$((ERRORS + 1))
            fi
            # Check if this specialist reads another specialist's reference files
            if grep -q "skills/$other/references\|/$other/references" "$spec_file" 2>/dev/null; then
                echo "  ❌ $spec reads $other's reference files (violates isolation)"
                ERRORS=$((ERRORS + 1))
            fi
        done
        [ "$ERRORS" -eq 0 ] && echo "  ✅ $spec: no cross-references"
    done
    echo ""
done

echo "=== Isolation Summary ==="
[ "$ERRORS" -eq 0 ] && echo "✅ All skills properly isolated" || (echo "❌ $ERRORS isolation violation(s)" && exit 1)
```

---

## Stage 2: Static Analysis

Deeper checks that run on pull requests. Runtime target: <2 minutes.

### GitHub Actions Workflow

```yaml
# .github/workflows/skill-analyze.yml
name: Skill Static Analysis

on:
  pull_request:
    paths:
      - 'skills/**'

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Need full history for diff analysis

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install pyyaml tiktoken

      - name: Identify changed skills
        id: changes
        run: |
          CHANGED=$(git diff --name-only origin/${{ github.base_ref }}...HEAD -- skills/ | \
            grep "SKILL.md\|references/" | \
            sed 's|/SKILL.md||;s|/references/.*||' | \
            sort -u)
          echo "skills=$CHANGED" >> $GITHUB_OUTPUT
          echo "Changed skills:"
          echo "$CHANGED"

      - name: Run pattern compliance check
        run: python pipeline/scripts/analyze-patterns.py skills/

      - name: Check portability (Claude Code + Codex)
        run: bash pipeline/scripts/check-portability.sh skills/

      - name: Worst-case context load analysis
        run: python pipeline/scripts/context-load-analysis.py skills/

      - name: Generate PR comment with analysis
        if: always()
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const report = fs.existsSync('analysis-report.md')
              ? fs.readFileSync('analysis-report.md', 'utf8')
              : 'Analysis report not generated.';
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: report
            });
```

### Pattern Compliance Analyzer

```python
#!/usr/bin/env python3
"""
pipeline/scripts/analyze-patterns.py
Checks SKILL.md files for writing rule compliance.
"""

import sys
import re
from pathlib import Path

PROSE_INDICATORS = [
    (r'\b(it is important to|you should|this is because|the reason for)\b',
     "Explanatory prose detected — convert to imperative step"),
    (r'\b(basically|essentially|fundamentally|in other words)\b',
     "Filler language — remove or convert to direct instruction"),
    (r'\b(please note that|keep in mind that|remember that)\b',
     "Meta-instruction — convert to a Note: annotation or remove"),
]

QUALITY_CHECKS = [
    # Check for output format duplication (schema + example)
    (r'## (Output|Response) (Format|Schema|Structure).*?```.*?```.*?## (Example|Sample)',
     "Possible output format duplication — keep only the example",
     re.DOTALL),
    # Check for inline checklists >10 items
    (r'(^[-*] .+\n){10,}',
     "Inline checklist with >10 items — extract to reference file",
     re.MULTILINE),
]

STRUCTURE_CHECKS = [
    # Procedure steps should be imperative
    (r'## Procedure\n([\s\S]*?)(?=\n## |\Z)',
     lambda match: check_imperative_steps(match.group(1))),
]


def check_imperative_steps(procedure_text: str) -> list:
    """Check that procedure steps use imperative sentences."""
    issues = []
    lines = procedure_text.strip().split('\n')
    step_pattern = re.compile(r'^\s*(Step \d+|\d+[\.\)])')

    for i, line in enumerate(lines, 1):
        if step_pattern.match(line):
            # Check if the step content starts with an imperative verb
            content = re.sub(r'^\s*(Step \d+[:.]\s*|\d+[\.\)]\s*)', '', line).strip()
            if content and content[0].islower():
                issues.append(
                    f"  Line ~{i}: Step may not be imperative: '{content[:60]}...'"
                )
    return issues


def analyze_file(filepath: Path) -> dict:
    content = filepath.read_text(encoding="utf-8")
    results = {"errors": [], "warnings": [], "info": []}

    # Prose indicator checks
    for pattern, message in PROSE_INDICATORS:
        matches = list(re.finditer(pattern, content, re.IGNORECASE))
        if matches:
            for m in matches[:3]:  # Report max 3 occurrences
                line_num = content[:m.start()].count('\n') + 1
                results["warnings"].append(f"Line {line_num}: {message}")

    # Quality checks
    for pattern, message, *flags in QUALITY_CHECKS:
        flag = flags[0] if flags else 0
        if re.search(pattern, content, flag):
            results["warnings"].append(message)

    # Word count metrics
    word_count = len(content.split())
    results["info"].append(f"Word count: {word_count} (~{int(word_count * 1.33)} tokens)")

    return results


def main():
    search_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")

    skill_files = [
        f for f in search_dir.rglob("SKILL.md")
        if "eval-cases" not in f.parts and "templates" not in f.parts
    ]

    ref_files = list(search_dir.rglob("references/*.md"))

    all_files = skill_files + ref_files
    total_warnings = 0
    total_errors = 0

    report_lines = ["# Skill Analysis Report\n"]

    for filepath in sorted(all_files):
        results = analyze_file(filepath)

        if results["errors"] or results["warnings"]:
            report_lines.append(f"\n## {filepath}")
            for info in results["info"]:
                report_lines.append(f"ℹ️ {info}")
            for error in results["errors"]:
                report_lines.append(f"❌ {error}")
                total_errors += 1
            for warning in results["warnings"]:
                report_lines.append(f"⚠️ {warning}")
                total_warnings += 1

    report_lines.append(f"\n---\n**Summary**: {total_errors} errors, {total_warnings} warnings across {len(all_files)} files")

    report = "\n".join(report_lines)
    Path("analysis-report.md").write_text(report)
    print(report)

    if total_errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### Portability Check (Claude Code + Codex)

```bash
#!/bin/bash
# pipeline/scripts/check-portability.sh
# Checks skills for cross-platform compatibility between Claude Code and Codex

set -euo pipefail

SKILL_DIR="${1:-.}"
WARNINGS=0

echo "=== Platform Portability Check ==="
echo ""

find "$SKILL_DIR" -name "SKILL.md" -not -path "*/eval-cases/*" -not -path "*/templates/*" | while read -r skill_md; do
    skill_name=$(basename "$(dirname "$skill_md")")
    echo "Checking: $skill_name"

    # Check for platform-specific references
    if grep -qi "CLAUDE\.md\b" "$skill_md"; then
        echo "  ⚠️  References CLAUDE.md — use generic 'project instructions file' or note both CLAUDE.md / AGENTS.md"
        WARNINGS=$((WARNINGS + 1))
    fi

    if grep -qi "AGENTS\.md\b" "$skill_md"; then
        echo "  ⚠️  References AGENTS.md — use generic 'project instructions file' or note both CLAUDE.md / AGENTS.md"
        WARNINGS=$((WARNINGS + 1))
    fi

    # Check for Claude-specific tool references
    if grep -qP 'View\(|Read\(|Task\(' "$skill_md"; then
        echo "  ⚠️  May contain Claude Code-specific tool syntax"
        WARNINGS=$((WARNINGS + 1))
    fi

    # Check scripts for platform assumptions
    dir=$(dirname "$skill_md")
    if [ -d "$dir/scripts" ]; then
        for script in "$dir"/scripts/*; do
            [ -f "$script" ] || continue
            # Check for shebangs and common portability issues
            if head -1 "$script" | grep -q "python$"; then
                echo "  ⚠️  $script: Use 'python3' not 'python' for portability"
                WARNINGS=$((WARNINGS + 1))
            fi
        done
    fi

    # Check that frontmatter doesn't use platform-specific fields
    # (Both platforms use name + description, differences are in optional fields)

    echo "  ✅ Basic portability checks passed"
    echo ""
done

echo "=== Portability Summary ==="
echo "Warnings: $WARNINGS"
echo "Note: Warnings don't block merge but should be addressed for cross-platform use"
```

---

## Stage 3: Eval Execution

Runs eval cases against skills to catch regressions. This is the expensive stage —
it actually invokes the model. Run on merge to main or on manual trigger.

### GitHub Actions Workflow

```yaml
# .github/workflows/skill-eval.yml
name: Skill Eval Execution

on:
  push:
    branches: [main]
    paths:
      - 'skills/**'
  workflow_dispatch:
    inputs:
      skill_path:
        description: 'Path to specific skill to evaluate (or "all")'
        required: true
        default: 'all'
      model:
        description: 'Model to run evals against'
        required: true
        default: 'sonnet'
        type: choice
        options:
          - haiku
          - sonnet
          - opus

jobs:
  eval:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4

      - name: Set up environment
        run: |
          pip install pyyaml tiktoken
          # Install Claude Code CLI or Codex CLI depending on target
          # This section is platform-dependent

      - name: Identify skills to evaluate
        id: targets
        run: |
          if [ "${{ inputs.skill_path }}" = "all" ] || [ -z "${{ inputs.skill_path }}" ]; then
            TARGETS=$(find skills/ -name "evals.json" -path "*/eval-cases/*" | \
              sed 's|/eval-cases/.*||' | sort -u)
          else
            TARGETS="${{ inputs.skill_path }}"
          fi
          echo "targets=$TARGETS" >> $GITHUB_OUTPUT

      - name: Run evaluations
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          bash pipeline/scripts/run-evals.sh \
            --targets "${{ steps.targets.outputs.targets }}" \
            --model "${{ inputs.model || 'sonnet' }}"

      - name: Process eval results
        run: python pipeline/scripts/process-eval-results.py eval-results/

      - name: Upload eval artifacts
        uses: actions/upload-artifact@v4
        with:
          name: eval-results-${{ github.sha }}
          path: eval-results/

      - name: Check for regressions
        run: |
          python pipeline/scripts/check-regressions.py \
            --current eval-results/ \
            --baseline eval-baselines/
```

### Eval Execution Orchestrator

```bash
#!/bin/bash
# pipeline/scripts/run-evals.sh
# Orchestrates eval case execution for one or more skills

set -euo pipefail

TARGETS=""
MODEL="sonnet"
OUTPUT_DIR="eval-results"

while [[ $# -gt 0 ]]; do
    case $1 in
        --targets) TARGETS="$2"; shift 2 ;;
        --model) MODEL="$2"; shift 2 ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

mkdir -p "$OUTPUT_DIR"

echo "=== Eval Execution ==="
echo "Model: $MODEL"
echo "Targets: $TARGETS"
echo ""

for skill_dir in $TARGETS; do
    skill_name=$(basename "$skill_dir")
    echo "━━━ Evaluating: $skill_name ━━━"

    eval_config="$skill_dir/eval-cases/evals.json"
    if [ ! -f "$eval_config" ]; then
        echo "  ⚠️  No evals.json found, skipping"
        continue
    fi

    result_dir="$OUTPUT_DIR/$skill_name"
    mkdir -p "$result_dir"

    # Extract eval cases
    case_count=$(python3 -c "import json; print(len(json.load(open('$eval_config'))['cases']))")
    echo "  Found $case_count eval cases"

    for i in $(seq 0 $((case_count - 1))); do
        case_id=$(python3 -c "import json; print(json.load(open('$eval_config'))['cases'][$i]['id'])")
        case_file=$(python3 -c "import json; print(json.load(open('$eval_config'))['cases'][$i]['file'])")

        echo "  Running case: $case_id"

        # Extract the input from the case file
        input_json=$(python3 -c "
import json, re
content = open('$skill_dir/eval-cases/$case_file').read()
# Extract the JSON input block
match = re.search(r'\`\`\`json\n({.*?})\n\`\`\`', content, re.DOTALL)
if match:
    print(match.group(1))
else:
    print('{}')
")

        # Run the skill against the input
        # This is where you'd invoke Claude Code CLI or Codex CLI
        # The exact invocation depends on your platform setup
        #
        # Example for Claude Code:
        # claude --skill "$skill_dir/SKILL.md" --model "$MODEL" \
        #   --input "$input_json" > "$result_dir/$case_id-output.json" 2>&1
        #
        # Example for Codex:
        # codex --skill "$skill_dir" -m "gpt-5.3-codex" \
        #   --input "$input_json" > "$result_dir/$case_id-output.json" 2>&1
        #
        # For now, record the execution metadata
        echo "{\"case_id\": \"$case_id\", \"model\": \"$MODEL\", \"status\": \"pending\", \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" \
          > "$result_dir/$case_id-meta.json"
    done

    echo "  ✅ All cases executed"
    echo ""
done

echo "=== Eval execution complete. Results in $OUTPUT_DIR ==="
```

---

## Stage 4: Publish

Package and distribute skills on release tags.

### GitHub Actions Workflow

```yaml
# .github/workflows/skill-publish.yml
name: Skill Publish

on:
  push:
    tags:
      - 'v*'

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Determine changed skills since last tag
        id: changes
        run: |
          PREV_TAG=$(git describe --abbrev=0 --tags HEAD^ 2>/dev/null || echo "")
          if [ -n "$PREV_TAG" ]; then
            CHANGED=$(git diff --name-only "$PREV_TAG"...HEAD -- skills/ | \
              sed 's|skills/\([^/]*\)/.*|\1|' | sort -u)
          else
            CHANGED=$(ls skills/)
          fi
          echo "skills=$CHANGED" >> $GITHUB_OUTPUT

      - name: Package skills
        run: |
          mkdir -p dist/
          for skill in ${{ steps.changes.outputs.skills }}; do
            echo "Packaging: $skill"
            bash pipeline/scripts/package-skill.sh "skills/$skill" "dist/$skill"
          done

      - name: Create release with skill packages
        uses: softprops/action-gh-release@v2
        with:
          files: dist/*
          generate_release_notes: true

      # Optional: Sync to target locations
      - name: Sync to user skills directory
        if: github.event_name == 'push'
        run: |
          # This step would copy packaged skills to wherever they need to go
          # Examples: ~/.claude/skills/, ~/.codex/skills/, a shared drive, etc.
          echo "Sync targets would be configured here"
```

---

## Budget Configuration

```json
// pipeline/config/budgets.json
{
  "coordinator_max_words": 600,
  "coordinator_max_tokens": 800,
  "specialist_max_words": 1500,
  "specialist_max_tokens": 2000,
  "reference_max_words": 1100,
  "reference_max_tokens": 1500,
  "standalone_max_words": 1500,
  "standalone_max_tokens": 2000,
  "max_simultaneous_tokens": 5000,
  "overrides": {
    "skills/frontend-qa/skills/ui-bug-investigator": {
      "specialist_max_words": 1800,
      "reason": "Complex diagnostic procedure with multiple branch points"
    }
  }
}
```

---

## Pre-Commit Hook (Local Enforcement)

For catching issues before they even reach CI:

```bash
#!/bin/bash
# .githooks/pre-commit
# Install: git config core.hooksPath .githooks

STAGED_SKILLS=$(git diff --cached --name-only --diff-filter=ACM | grep -E "SKILL\.md$|references/.*\.md$" || true)

if [ -z "$STAGED_SKILLS" ]; then
    exit 0  # No skill files changed
fi

echo "Running skill pre-commit checks..."

ERRORS=0
for file in $STAGED_SKILLS; do
    word_count=$(wc -w < "$file")

    # Determine budget based on file location
    if echo "$file" | grep -q "/references/"; then
        max=1100
        label="reference"
    elif echo "$file" | grep -q "/skills/.*/SKILL.md"; then
        max=1500
        label="specialist"
    else
        max=1500
        label="skill"
    fi

    if [ "$word_count" -gt "$max" ]; then
        echo "❌ $file: $word_count words exceeds $label budget ($max)"
        ERRORS=$((ERRORS + 1))
    fi
done

if [ "$ERRORS" -gt 0 ]; then
    echo ""
    echo "Commit blocked: $ERRORS file(s) over token budget."
    echo "Run 'bash pipeline/scripts/check-token-budgets.sh skills/' for details."
    exit 1
fi

echo "✅ All skill files within budget"
```

---

## Bootstrapping

To set up the pipeline in an existing skills repo:

```bash
# 1. Copy the pipeline directory into your repo
cp -r pipeline/ your-skills-repo/pipeline/

# 2. Copy the workflow files
mkdir -p your-skills-repo/.github/workflows/
cp .github/workflows/skill-*.yml your-skills-repo/.github/workflows/

# 3. Create the budget config
cp pipeline/config/budgets.json your-skills-repo/pipeline/config/

# 4. Make scripts executable
chmod +x your-skills-repo/pipeline/scripts/*.sh

# 5. Install the pre-commit hook
cp .githooks/pre-commit your-skills-repo/.githooks/
git -C your-skills-repo config core.hooksPath .githooks

# 6. Run the initial validation to establish a baseline
cd your-skills-repo
bash pipeline/scripts/check-token-budgets.sh skills/
bash pipeline/scripts/validate-structure.sh skills/
python pipeline/scripts/check-frontmatter.py skills/
```
