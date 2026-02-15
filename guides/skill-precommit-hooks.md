# Pre-Commit Enforcement for Skill Authoring

## Why Pre-Commit Over CI-Only

CI catches problems after you've pushed. Pre-commit catches them before you've
committed. The difference matters for skills specifically because:

1. **Skill edits are iterative.** You tweak a SKILL.md, test it, tweak again.
   If each tweak requires a push → CI failure → fix → push cycle, you lose
   10-15 minutes per iteration. Pre-commit gives you sub-second feedback.

2. **Budget violations are the most common issue.** Skills grow during editing.
   You add a checklist item, expand a procedure step, include an example.
   Catching the budget violation at commit time — before you've context-switched
   away from the file — means the fix is trivial.

3. **Broken references are silent.** If you rename a reference file but forget
   to update the SKILL.md that points to it, nothing fails until execution.
   Pre-commit catches the broken link immediately.

The pre-commit hooks below are designed to run in <2 seconds total so they
never feel like friction.

---

## Setup: Using the `pre-commit` Framework

We use the [pre-commit](https://pre-commit.com/) framework rather than raw
git hooks. It gives you reproducible environments, easy sharing across repos,
and the ability to run hooks on-demand outside of commits.

### Installation

```bash
# Install pre-commit
pip install pre-commit

# From your skills repo root
pre-commit install

# Optional: install for commit-msg hook too (for conventional commit enforcement)
pre-commit install --hook-type commit-msg
```

### Configuration

```yaml
# .pre-commit-config.yaml

repos:
  # Local hooks — these run scripts from the repo itself
  - repo: local
    hooks:
      # ── Token Budget Enforcement ──────────────────────────────────
      - id: skill-token-budget
        name: Skill Token Budget
        description: Enforce token/word limits on SKILL.md and reference files
        entry: python pipeline/hooks/check_token_budget.py
        language: python
        files: '(SKILL\.md|references/.*\.md)$'
        exclude: '(eval-cases|templates|node_modules)/'
        additional_dependencies: []

      # ── Frontmatter Validation ────────────────────────────────────
      - id: skill-frontmatter
        name: Skill Frontmatter
        description: Validate YAML frontmatter structure and required fields
        entry: python pipeline/hooks/check_frontmatter.py
        language: python
        files: 'SKILL\.md$'
        exclude: '(eval-cases|templates)/'
        additional_dependencies: ['pyyaml']

      # ── Reference Integrity ───────────────────────────────────────
      - id: skill-references
        name: Skill Reference Integrity
        description: Verify all referenced files exist
        entry: python pipeline/hooks/check_references.py
        language: python
        files: 'SKILL\.md$'
        exclude: '(eval-cases|templates)/'

      # ── Cross-Skill Isolation ─────────────────────────────────────
      - id: skill-isolation
        name: Skill Isolation
        description: Ensure specialist skills don't cross-reference each other
        entry: python pipeline/hooks/check_isolation.py
        language: python
        files: 'SKILL\.md$'
        exclude: '(eval-cases|templates)/'

      # ── Prose Detector ────────────────────────────────────────────
      - id: skill-prose-check
        name: Skill Prose Detector
        description: Flag explanatory prose that should be imperative steps
        entry: python pipeline/hooks/check_prose.py
        language: python
        files: '(SKILL\.md|references/.*\.md)$'
        exclude: '(eval-cases|templates)/'
        # Warn only — doesn't block commit
        verbose: true

      # ── Suite Context Load ────────────────────────────────────────
      - id: skill-context-load
        name: Skill Suite Context Load
        description: Verify worst-case context load stays under ceiling
        entry: python pipeline/hooks/check_context_load.py
        language: python
        files: '(SKILL\.md|references/.*\.md)$'
        exclude: '(eval-cases|templates)/'

      # ── Conventional Commits for Skills ───────────────────────────
      - id: skill-commit-msg
        name: Skill Commit Message
        description: Enforce conventional commit format for skill changes
        entry: python pipeline/hooks/check_commit_msg.py
        language: python
        stages: [commit-msg]
```

---

## Hook Implementations

All hooks live in `pipeline/hooks/` and follow the pre-commit convention:
they receive filenames as arguments and exit 0 (pass) or 1 (fail).

### Token Budget Hook

```python
#!/usr/bin/env python3
"""
pipeline/hooks/check_token_budget.py

Enforces word/token budgets on SKILL.md and reference files.
Runs only on staged files — fast by design.

Exit 0 = pass, Exit 1 = fail with details.
"""

import sys
import json
from pathlib import Path

# Default budgets
DEFAULTS = {
    "coordinator_max_words": 600,
    "specialist_max_words": 1500,
    "reference_max_words": 1100,
    "standalone_max_words": 1500,
}

# Load overrides if config exists
CONFIG_PATH = Path("pipeline/config/budgets.json")
config = {}
if CONFIG_PATH.exists():
    config = json.loads(CONFIG_PATH.read_text())

overrides = config.get("overrides", {})


def get_budget(filepath: str) -> tuple[int, str]:
    """Determine the word budget for a file based on its location."""
    fp = Path(filepath)

    # Check for per-skill overrides
    for override_path, override_config in overrides.items():
        if override_path in filepath:
            if "references/" in filepath:
                return override_config.get("reference_max_words",
                    config.get("reference_max_words", DEFAULTS["reference_max_words"])), "reference (override)"
            return override_config.get("specialist_max_words",
                config.get("specialist_max_words", DEFAULTS["specialist_max_words"])), "specialist (override)"

    # Reference file
    if "references/" in filepath:
        return config.get("reference_max_words", DEFAULTS["reference_max_words"]), "reference"

    # SKILL.md — determine if coordinator, specialist, or standalone
    if fp.name == "SKILL.md":
        parent = fp.parent
        # Coordinator: has a skills/ subdirectory
        if (parent / "skills").is_dir():
            return config.get("coordinator_max_words", DEFAULTS["coordinator_max_words"]), "coordinator"
        # Specialist: inside a skills/ directory
        if "skills" in fp.parts:
            return config.get("specialist_max_words", DEFAULTS["specialist_max_words"]), "specialist"
        # Standalone
        return config.get("standalone_max_words", DEFAULTS["standalone_max_words"]), "standalone"

    return DEFAULTS["reference_max_words"], "unknown"


def check_file(filepath: str) -> tuple[bool, str]:
    """Check a single file against its budget. Returns (passed, message)."""
    path = Path(filepath)
    if not path.exists():
        return True, ""  # File was deleted, skip

    content = path.read_text(encoding="utf-8", errors="replace")
    word_count = len(content.split())
    token_estimate = int(word_count * 1.33)
    budget, label = get_budget(filepath)

    if word_count > budget:
        overage = word_count - budget
        overage_tokens = int(overage * 1.33)
        return False, (
            f"❌ OVER BUDGET: {filepath}\n"
            f"   {word_count} words (~{token_estimate} tokens) — "
            f"limit is {budget} words for {label}\n"
            f"   Over by: {overage} words (~{overage_tokens} tokens)\n"
            f"   Tip: Extract checklists to references/, "
            f"convert prose to imperative steps, or remove explanatory text"
        )
    else:
        headroom = budget - word_count
        pct_used = int((word_count / budget) * 100)
        # Warn if >90% of budget used
        if pct_used > 90:
            return True, (
                f"⚠️  NEAR BUDGET: {filepath}\n"
                f"   {word_count}/{budget} words ({pct_used}%) — "
                f"only {headroom} words of headroom"
            )
        return True, ""


def main():
    files = sys.argv[1:]
    if not files:
        sys.exit(0)

    failed = False
    messages = []

    for f in files:
        passed, msg = check_file(f)
        if msg:
            messages.append(msg)
        if not passed:
            failed = True

    if messages:
        print("\n".join(messages))

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
```

### Reference Integrity Hook

```python
#!/usr/bin/env python3
"""
pipeline/hooks/check_references.py

Verifies that all file paths referenced in SKILL.md files actually exist.
Catches broken links from renames, moves, or deletions.
"""

import sys
import re
from pathlib import Path

# Patterns that indicate a file reference in a SKILL.md
REFERENCE_PATTERNS = [
    # references/filename.md
    re.compile(r'(?:references/[\w.-]+\.md)'),
    # scripts/filename.ext
    re.compile(r'(?:scripts/[\w.-]+\.\w+)'),
    # Read `path/to/file`
    re.compile(r'Read\s+`([^`]+)`'),
    # Load `path/to/file`
    re.compile(r'Load\s+`([^`]+)`'),
    # at `path/to/file`
    re.compile(r'at\s+`([^`]+\.md)`'),
]


def check_file(filepath: str) -> list[str]:
    """Check all references in a SKILL.md. Returns list of error messages."""
    path = Path(filepath)
    if not path.exists():
        return []

    content = path.read_text(encoding="utf-8", errors="replace")
    skill_dir = path.parent
    errors = []

    # Collect all referenced paths
    referenced = set()
    for pattern in REFERENCE_PATTERNS:
        for match in pattern.finditer(content):
            # Use the last group if there are capture groups, otherwise full match
            ref = match.group(match.lastindex or 0)
            # Skip URLs and absolute paths
            if ref.startswith(("http", "/", "$", "~")):
                continue
            referenced.add(ref)

    # Check each reference
    for ref in sorted(referenced):
        ref_path = skill_dir / ref
        if not ref_path.exists():
            # Find the line number for better error messages
            for i, line in enumerate(content.split("\n"), 1):
                if ref in line:
                    errors.append(
                        f"❌ {filepath}:{i} — references '{ref}' but file not found at {ref_path}"
                    )
                    break
            else:
                errors.append(
                    f"❌ {filepath} — references '{ref}' but file not found at {ref_path}"
                )

    return errors


def main():
    files = sys.argv[1:]
    if not files:
        sys.exit(0)

    all_errors = []
    for f in files:
        all_errors.extend(check_file(f))

    if all_errors:
        print("Reference integrity check failed:\n")
        print("\n".join(all_errors))
        print(f"\n{len(all_errors)} broken reference(s) found")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
```

### Prose Detector Hook

```python
#!/usr/bin/env python3
"""
pipeline/hooks/check_prose.py

Detects explanatory prose, filler language, and non-imperative patterns
in SKILL.md procedure sections. Warns but does not block commits.
"""

import sys
import re
from pathlib import Path

# Patterns that indicate non-imperative, explanatory writing
PROSE_PATTERNS = [
    # Explanatory hedging
    (r'\b(it is important to|it\'s important to)\b', "Explanatory — just state the action"),
    (r'\b(you should|you may want to|you might want to)\b', "Hedging — use imperative: 'Do X'"),
    (r'\b(this is because|the reason for this|this helps ensure)\b', "Explanation — remove or convert to Note:"),
    (r'\b(keep in mind that|please note that|note that|remember that)\b', "Meta-instruction — convert to inline Note:"),
    (r'\b(basically|essentially|fundamentally|in other words)\b', "Filler word — remove"),
    (r'\b(in order to)\b', "Verbose — replace with 'to'"),
    (r'\b(it\'s worth noting|it should be noted)\b', "Passive filler — state the fact directly"),
    (r'\b(as mentioned (earlier|above|before|previously))\b', "Self-reference — remove or restructure"),
    (r'\b(make sure to|be sure to|ensure that you)\b', "Indirect — use imperative: 'Verify X'"),

    # Conversational tone in procedures
    (r'\b(let\'s|we can|we should|we need to)\b', "Conversational — use imperative"),
    (r'\b(feel free to|don\'t hesitate to)\b', "Casual — use imperative or remove"),
]

# Sections where prose is acceptable (not procedure sections)
PROSE_OK_SECTIONS = {"Purpose", "Context", "Background", "Notes", "Description"}


def in_procedure_section(content: str, position: int) -> bool:
    """Check if a position is within a Procedure section."""
    # Find all section headers
    headers = list(re.finditer(r'^##\s+(.+)$', content[:position], re.MULTILINE))
    if not headers:
        return True  # No headers found, assume it's procedural

    last_header = headers[-1].group(1).strip()
    return last_header not in PROSE_OK_SECTIONS


def check_file(filepath: str) -> list[str]:
    """Check a file for prose patterns. Returns list of warnings."""
    path = Path(filepath)
    if not path.exists():
        return []

    content = path.read_text(encoding="utf-8", errors="replace")
    warnings = []

    # Skip reference files for most checks (they should be pure content)
    is_reference = "references/" in filepath

    for pattern, message in PROSE_PATTERNS:
        for match in re.finditer(pattern, content, re.IGNORECASE):
            # Skip if not in a procedure section (for SKILL.md files)
            if not is_reference and not in_procedure_section(content, match.start()):
                continue

            line_num = content[:match.start()].count('\n') + 1
            matched_text = match.group(0)
            warnings.append(f"  ⚠️  {filepath}:{line_num} — \"{matched_text}\" → {message}")

    return warnings


def main():
    files = sys.argv[1:]
    if not files:
        sys.exit(0)

    all_warnings = []
    for f in files:
        all_warnings.extend(check_file(f))

    if all_warnings:
        print("Prose patterns detected (warnings — commit not blocked):\n")
        print("\n".join(all_warnings))
        print(f"\n{len(all_warnings)} pattern(s) found. Consider tightening to imperative style.")

    # Always exit 0 — prose check is advisory, not blocking
    sys.exit(0)


if __name__ == "__main__":
    main()
```

### Cross-Skill Isolation Hook

```python
#!/usr/bin/env python3
"""
pipeline/hooks/check_isolation.py

Ensures specialist skills in a suite don't reference each other's
SKILL.md or reference files directly. All inter-skill communication
should go through the coordinator's handoff protocol.
"""

import sys
import re
from pathlib import Path


def find_suite_context(filepath: str) -> tuple[Path | None, list[str]]:
    """Find the suite root and sibling specialist names for a given SKILL.md."""
    path = Path(filepath)

    # Walk up to find a parent with a skills/ directory
    current = path.parent
    while current != current.parent:
        if current.name == "skills" and (current.parent / "SKILL.md").exists():
            # We're inside a suite's skills/ directory
            suite_root = current.parent
            # Find sibling specialists
            siblings = [
                d.name for d in current.iterdir()
                if d.is_dir() and (d / "SKILL.md").exists()
            ]
            return suite_root, siblings
        current = current.parent

    return None, []


def check_file(filepath: str) -> list[str]:
    """Check for cross-skill references. Returns list of errors."""
    path = Path(filepath)
    if not path.exists():
        return []

    suite_root, siblings = find_suite_context(filepath)
    if not suite_root or not siblings:
        return []  # Not part of a suite, skip

    content = path.read_text(encoding="utf-8", errors="replace")
    current_skill = None
    # Determine which specialist this file belongs to
    for part in path.parts:
        if part in siblings:
            current_skill = part
            break

    if not current_skill:
        return []

    errors = []
    for sibling in siblings:
        if sibling == current_skill:
            continue

        # Check for references to sibling's SKILL.md
        patterns = [
            f"skills/{sibling}/SKILL.md",
            f"{sibling}/SKILL.md",
            f"skills/{sibling}/references/",
            f"{sibling}/references/",
        ]

        for pattern in patterns:
            for i, line in enumerate(content.split("\n"), 1):
                if pattern in line:
                    errors.append(
                        f"❌ {filepath}:{i} — references sibling skill '{sibling}'\n"
                        f"   Cross-skill references violate isolation. "
                        f"Use the coordinator's handoff protocol instead."
                    )

    return errors


def main():
    files = sys.argv[1:]
    if not files:
        sys.exit(0)

    all_errors = []
    for f in files:
        all_errors.extend(check_file(f))

    if all_errors:
        print("Cross-skill isolation violation(s):\n")
        print("\n".join(all_errors))
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
```

### Suite Context Load Hook

```python
#!/usr/bin/env python3
"""
pipeline/hooks/check_context_load.py

Calculates worst-case simultaneous context load for skill suites
and flags when the ceiling is exceeded.

Worst case = coordinator + largest specialist + largest reference
"""

import sys
import json
from pathlib import Path
from collections import defaultdict

CONFIG_PATH = Path("pipeline/config/budgets.json")
MAX_SIMULTANEOUS = 5000  # Default token ceiling

if CONFIG_PATH.exists():
    config = json.loads(CONFIG_PATH.read_text())
    MAX_SIMULTANEOUS = config.get("max_simultaneous_tokens", MAX_SIMULTANEOUS)


def word_count(filepath: Path) -> int:
    if not filepath.exists():
        return 0
    return len(filepath.read_text(encoding="utf-8", errors="replace").split())


def tokens(words: int) -> int:
    return int(words * 1.33)


def find_suites(files: list[str]) -> set[Path]:
    """From a list of changed files, find all affected skill suites."""
    suites = set()
    for f in files:
        path = Path(f)
        # Walk up to find suite root (directory with both SKILL.md and skills/)
        current = path.parent
        while current != current.parent:
            if (current / "SKILL.md").exists() and (current / "skills").is_dir():
                suites.add(current)
                break
            current = current.parent
    return suites


def analyze_suite(suite_root: Path) -> tuple[bool, str]:
    """Analyze worst-case context load for a suite."""
    coordinator = suite_root / "SKILL.md"
    coordinator_tokens = tokens(word_count(coordinator))

    # Find all specialist SKILL.md files
    specialists = {}
    for skill_md in (suite_root / "skills").rglob("SKILL.md"):
        name = skill_md.parent.name
        specialists[name] = tokens(word_count(skill_md))

    # Find all reference files per specialist
    references = defaultdict(dict)
    for ref_file in (suite_root / "skills").rglob("references/*.md"):
        specialist_name = None
        for part in ref_file.parts:
            if part in specialists:
                specialist_name = part
                break
        if specialist_name:
            references[specialist_name][ref_file.name] = tokens(word_count(ref_file))

    # Calculate worst case
    largest_specialist_name = max(specialists, key=specialists.get) if specialists else "none"
    largest_specialist_tokens = specialists.get(largest_specialist_name, 0)

    largest_ref_tokens = 0
    largest_ref_name = "none"
    for spec_name, refs in references.items():
        for ref_name, ref_tokens in refs.items():
            if ref_tokens > largest_ref_tokens:
                largest_ref_tokens = ref_tokens
                largest_ref_name = f"{spec_name}/{ref_name}"

    worst_case = coordinator_tokens + largest_specialist_tokens + largest_ref_tokens

    report = (
        f"Suite: {suite_root.name}\n"
        f"  Coordinator: ~{coordinator_tokens} tokens\n"
        f"  Largest specialist: {largest_specialist_name} (~{largest_specialist_tokens} tokens)\n"
        f"  Largest reference: {largest_ref_name} (~{largest_ref_tokens} tokens)\n"
        f"  Worst-case load: ~{worst_case} tokens (ceiling: {MAX_SIMULTANEOUS})"
    )

    passed = worst_case <= MAX_SIMULTANEOUS
    return passed, report


def main():
    files = sys.argv[1:]
    if not files:
        sys.exit(0)

    suites = find_suites(files)
    if not suites:
        sys.exit(0)  # No suites affected

    failed = False
    for suite in sorted(suites):
        passed, report = analyze_suite(suite)
        prefix = "✅" if passed else "❌"
        print(f"{prefix} {report}")
        if not passed:
            failed = True
        print()

    if failed:
        print("Worst-case context load exceeds ceiling. Refactor to reduce.")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
```

### Commit Message Convention Hook

```python
#!/usr/bin/env python3
"""
pipeline/hooks/check_commit_msg.py

Enforces conventional commit format for skill changes.
Validates that commits touching skill files use skill-specific types.

Valid types:
  skill(name): description       — new skill or major change
  skill-fix(name): description   — bug fix in a skill
  skill-ref(name): description   — refactor (no behavior change)
  skill-eval(name): description  — eval case changes
  skill-docs(name): description  — documentation only
  chore(pipeline): description   — pipeline/tooling changes
"""

import sys
import re
from pathlib import Path

VALID_PATTERN = re.compile(
    r'^(skill|skill-fix|skill-ref|skill-eval|skill-docs|chore|feat|fix|docs|refactor)'
    r'\([a-z0-9-]+\): .{10,}'
)

SKILL_TYPES = {"skill", "skill-fix", "skill-ref", "skill-eval", "skill-docs"}


def main():
    commit_msg_file = sys.argv[1]
    msg = Path(commit_msg_file).read_text().strip().split("\n")[0]

    if not VALID_PATTERN.match(msg):
        print(
            f"❌ Commit message doesn't match convention:\n"
            f"   \"{msg}\"\n\n"
            f"Expected format: type(scope): description (min 10 chars)\n\n"
            f"Skill-specific types:\n"
            f"  skill(name):      New skill or major change\n"
            f"  skill-fix(name):  Bug fix in a skill\n"
            f"  skill-ref(name):  Refactor (no behavior change)\n"
            f"  skill-eval(name): Eval case changes\n"
            f"  skill-docs(name): Documentation only\n"
            f"  chore(pipeline):  Pipeline/tooling changes\n\n"
            f"Examples:\n"
            f"  skill(frontend-qa): add css-layout-debugger specialist\n"
            f"  skill-fix(page-mapper): handle barrel exports in component tracing\n"
            f"  skill-ref(ui-investigator): extract rendering checklist to reference file\n"
            f"  skill-eval(page-mapper): add complex nested layout eval case\n"
        )
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
```

---

## Running Hooks Manually

You don't have to wait for a commit to run checks:

```bash
# Run all hooks on all skill files
pre-commit run --all-files

# Run a specific hook
pre-commit run skill-token-budget --all-files

# Run all hooks on staged files only (same as commit-time)
pre-commit run

# Run on specific files
pre-commit run skill-token-budget --files skills/frontend-qa/SKILL.md

# Run prose check on a skill you're editing
pre-commit run skill-prose-check --files skills/frontend-qa/skills/ui-bug-investigator/SKILL.md
```

---

## Developer Workflow Integration

### Quick feedback while editing

Add these shell aliases to your profile for instant checks during editing:

```bash
# ~/.bashrc or ~/.zshrc

# Check budget on the file you're editing
alias skill-budget='pre-commit run skill-token-budget --files'

# Full check on a specific skill
skill-check() {
    local skill_dir="$1"
    echo "=== Checking $skill_dir ==="
    find "$skill_dir" -name "SKILL.md" -o -name "*.md" -path "*/references/*" | \
        xargs pre-commit run --files
}

# Quick word count while editing
skill-wc() {
    local file="$1"
    local words=$(wc -w < "$file")
    local tokens=$(( words * 133 / 100 ))
    echo "$file: $words words (~$tokens tokens)"
}
```

Usage:
```bash
# While editing a skill
skill-wc skills/frontend-qa/skills/ui-bug-investigator/SKILL.md
# → skills/.../ui-bug-investigator/SKILL.md: 1423 words (~1893 tokens)

skill-budget skills/frontend-qa/skills/ui-bug-investigator/SKILL.md
# → ✅ PASS: ... 1423/1500 words (94%) — only 77 words of headroom

skill-check skills/frontend-qa/
# → Runs all hooks on all files in the frontend-qa skill suite
```

### Editor Integration

For VS Code, add a task that runs the budget check on save:

```json
// .vscode/tasks.json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Skill Budget Check",
      "type": "shell",
      "command": "pre-commit run skill-token-budget --files ${file}",
      "presentation": {
        "reveal": "silent",
        "panel": "shared"
      },
      "problemMatcher": [],
      "runOptions": {
        "runOn": "folderOpen"
      }
    }
  ]
}
```

For neovim, add an autocommand:

```lua
-- In your neovim config
vim.api.nvim_create_autocmd("BufWritePost", {
  pattern = { "SKILL.md", "*/references/*.md" },
  callback = function()
    local file = vim.fn.expand("%:p")
    vim.fn.system("pre-commit run skill-token-budget --files " .. file)
  end,
})
```

---

## Directory Structure

```
pipeline/
├── hooks/
│   ├── check_token_budget.py
│   ├── check_frontmatter.py
│   ├── check_references.py
│   ├── check_isolation.py
│   ├── check_prose.py
│   ├── check_context_load.py
│   └── check_commit_msg.py
├── config/
│   └── budgets.json
├── scripts/
│   └── ... (CI scripts from the pipeline doc)
└── ...

.pre-commit-config.yaml              # Hook configuration
.vscode/tasks.json                   # Optional editor integration
```

---

## Interaction with CI Pipeline

Pre-commit and CI are complementary, not redundant:

| Check | Pre-Commit | CI (Stage 1) | CI (Stage 2) |
|-------|-----------|--------------|--------------|
| Token budgets | ✅ Blocks commit | ✅ Blocks merge | — |
| Frontmatter | ✅ Blocks commit | ✅ Blocks merge | — |
| Reference integrity | ✅ Blocks commit | ✅ Blocks merge | — |
| Cross-skill isolation | ✅ Blocks commit | ✅ Blocks merge | — |
| Prose detection | ⚠️ Warns only | — | ⚠️ PR comment |
| Context load ceiling | ✅ Blocks commit | ✅ Blocks merge | — |
| Pattern compliance | — | — | ⚠️ PR comment |
| Portability check | — | — | ⚠️ PR comment |
| Commit message | ✅ Blocks commit | — | — |
| Eval execution | — | — | On merge only |

Pre-commit catches the fast stuff locally. CI catches the same things as a
safety net (in case someone bypasses hooks with `--no-verify`) plus the
slower analysis and eval execution.
