# Adopter Guide

Step-by-step onboarding for adding skill governance to your LLM agent skill repository.

---

## Prerequisites

- A git repository containing (or that will contain) SKILL.md-based agent skills
- Python 3.8+
- `pip install pre-commit pyyaml`

---

## Path A: Starting Fresh

Use this path if you have no existing skills yet, or are creating a new skill suite from scratch.

### 1. Run the installer

From your skill suite repo root:

```bash
curl -sSL https://raw.githubusercontent.com/dtsong/skill-governance/v1.3.0/install.sh \
  | bash -s -- --init
```

This creates:
- `pipeline/hooks/` — pre-commit hook scripts (token budget, frontmatter, references, isolation, prose, context load)
- `pipeline/scripts/` — analysis and validation scripts
- `pipeline/config/` — default budgets, security suppressions, model routing config
- `pipeline/templates/` — scaffolding templates for new skills and suites
- `pipeline/specs/` — governance specifications (source of truth)
- `pipeline/shell-helpers.sh` — CLI helpers for skill development
- `.pre-commit-config.yaml` — hook definitions
- `.github/workflows/` — CI workflow templates
- `.governance-version` — tracks installed governance version
- `CLAUDE.md` — governance directive added (or appended if the file already exists)

### 2. Verify the governance directive

The installer adds the governance directive to your `CLAUDE.md`. Open it and confirm the `## Skill Governance Directive` section is present. This section tells your LLM agent what rules to follow when authoring skills.

### 3. Create your first skill

```bash
source pipeline/shell-helpers.sh
skill-new my-first-skill
```

This scaffolds a new standalone skill from the template with correct frontmatter and structure. Edit the generated `my-first-skill/SKILL.md` to add your skill's content.

### 4. Run compliance checks

```bash
skill-check my-first-skill
```

This runs all pre-commit hooks on your skill directory and reports any violations. Fix anything flagged before committing.

For a broader check:

```bash
skill-audit
```

This runs hard checks (structural integrity), advisory checks (budget, prose quality), and a budget report.

### 5. Set up pre-commit hooks

```bash
pre-commit install
pre-commit install --hook-type commit-msg
```

Now every commit is automatically validated. You can also run all checks manually:

```bash
pre-commit run --all-files
```

### 6. (Optional) Set up CI workflows

The installer copies GitHub Actions workflows to `.github/workflows/`. These run the same checks on pull requests. Push the workflow files to enable CI enforcement.

For details on CI configuration, see [guides/skill-cicd-pipeline.md](guides/skill-cicd-pipeline.md).

---

## Path B: Existing Skills (Retrofit)

Use this path if you already have SKILL.md files that need to be brought into compliance.

### 1. Run the installer

```bash
curl -sSL https://raw.githubusercontent.com/dtsong/skill-governance/v1.3.0/install.sh \
  | bash -s -- --init
```

Same as Path A — installs hooks, configs, templates, and the governance directive.

### 2. Run a full audit

```bash
source pipeline/shell-helpers.sh
skill-audit
```

The audit output has two sections:

- **Hard failures** (block commits) — must fix before hooks will pass
- **Advisory warnings** (informational) — recommended improvements that don't block commits

### 3. Fix hard failures first

Common hard failures and fixes:

| Failure | Fix |
|---------|-----|
| **Missing frontmatter** | Add YAML frontmatter with `name`, `description`, `version` fields |
| **Broken references** | Update paths in SKILL.md to match actual file locations on disk |
| **Cross-skill references** | Remove direct references between specialist skills; use the coordinator's handoff protocol instead |
| **Missing scope constraints** | Add a `## Scope Constraints` section declaring what the skill can and cannot access |

### 4. Address advisory warnings

Common advisory warnings:

| Warning | Guidance |
|---------|----------|
| **Token budget exceeded** | Trim prose, move checklists >10 items to reference files, extract examples |
| **Prose patterns detected** | Rewrite explanatory paragraphs as imperative procedure steps |
| **Description quality** | Use third person, add negative boundaries, target 40-80 words |

Budget overages are acceptable when justified by eval data. Document overrides in `pipeline/config/budgets.json`.

### 5. Restructure into suites if applicable

If you have more than 3 related skills, consider organizing them as a suite:

```
my-suite/
├── SKILL.md              # Coordinator — routes to specialists
└── skills/
    ├── specialist-a/
    │   └── SKILL.md
    └── specialist-b/
        ├── SKILL.md
        └── references/
            └── checklist.md
```

Use `skill-new-suite <name>` to scaffold the suite structure, then move your existing skills into the `skills/` directory.

Decision criteria: if skills share a domain but handle different task types (e.g., "create", "debug", "review"), they belong in a suite with a coordinator that classifies the task and loads the right specialist.

### 6. Install hooks and CI

Same as Path A steps 5-6:

```bash
pre-commit install
pre-commit install --hook-type commit-msg
```

---

## What the Hooks Enforce

| Hook | What It Checks | Blocks Commit? |
|------|---------------|----------------|
| `skill-token-budget` | Word/token counts against budget limits | Advisory (warns) |
| `skill-frontmatter` | YAML frontmatter structure and required fields | Yes |
| `skill-references` | All referenced files exist on disk | Yes |
| `skill-isolation` | No cross-references between specialist skills | Yes |
| `skill-prose-check` | Flags explanatory prose that should be imperative | Advisory (warns) |
| `skill-context-load` | Suite worst-case context load under ceiling (5,500 tokens) | Yes |
| `skill-commit-msg` | Conventional commit format for skill changes | Yes |

For hook implementation details and configuration, see [guides/skill-precommit-hooks.md](guides/skill-precommit-hooks.md).

---

## Common Questions

**Can I override token budgets for a specific skill?**

Yes. Add an entry to `pipeline/config/budgets.json` under the `"overrides"` key with the skill's path and custom limits. The override should be backed by eval data showing the larger budget improves output quality.

**Which specs should I read first?**

Start with the [governance directive](directive/SKILL-GOVERNANCE-DIRECTIVE.md) — it's a compact summary of all rules. Read the [full governance spec](specs/SKILL-GOVERNANCE-SPEC.md) when you need the rationale behind a rule or details on edge cases.

**Does this work with non-Claude agents?**

The hook and CI infrastructure works with any SKILL.md-compatible agent platform. The governance directive in CLAUDE.md is Claude Code-specific, but the structural rules (budgets, references, isolation) apply universally to any system that loads skills into LLM context windows.

**Where do eval cases go?**

Eval cases live outside skill directories, typically in an `eval-cases/` directory at the repo root. See [guides/building-eval-cases-guide.md](guides/building-eval-cases-guide.md) for authoring guidance.

**How do I upgrade governance when a new version is released?**

```bash
curl -sSL https://raw.githubusercontent.com/dtsong/skill-governance/v1.3.0/install.sh \
  | bash -s -- --upgrade --version <new-version>
```

This updates hooks, workflows, and configs while preserving your local overrides in `pipeline/config/`.

**What's the difference between the governance repo and my suite repo?**

The governance repo contains specifications, hooks, and tooling. Your suite repo contains the actual skills. The installer copies governance tooling into your suite. You never need to clone the governance repo directly — the installer pulls what it needs from tagged releases.

---

## Next Steps

- [Authoring standard](guides/skill-authoring-standard.md) — detailed rules for writing compliant skills
- [Engineering patterns](guides/skill-engineering-patterns.md) — patterns library for common skill architectures
- [Pre-commit hooks deep dive](guides/skill-precommit-hooks.md) — hook implementation and customization
- [CI/CD pipeline](guides/skill-cicd-pipeline.md) — GitHub Actions workflow configuration
- [Full governance spec](specs/SKILL-GOVERNANCE-SPEC.md) — the source of truth for all rules
