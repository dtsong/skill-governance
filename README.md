# Skill Governance

Specifications, pre-commit hooks, CI workflows, and tooling for governing LLM agent skill suites. Works with Claude Code, OpenAI Codex, and any SKILL.md-compatible agent platform.

This repo is the shared governance layer. Individual skill suites (the domain-specific skills themselves) live in their own repositories and pull governance tooling from here.

## Quick Start

### New suite

Bootstrap a new skill suite with governance tooling pre-configured:

```bash
curl -sSL https://raw.githubusercontent.com/dtsong/skill-governance/v1.3.0/install.sh | bash -s -- --init
```

This copies pre-commit hooks, CI workflows, budget configs, and templates into your suite repo, and writes a `.governance-version` file to track which governance version you installed.

### Upgrade existing suite

```bash
curl -sSL https://raw.githubusercontent.com/dtsong/skill-governance/v1.3.0/install.sh | bash -s -- --upgrade --version v1.3.0
```

This updates hooks, workflows, and configs to the target version while preserving your local overrides in `pipeline/config/`.

## Repo Structure

```
skill-governance/
├── specs/                     # Normative specifications (source of truth)
│   ├── SKILL-GOVERNANCE-SPEC.md
│   ├── SKILL-SECURITY-SPEC.md
│   ├── SKILL-MODEL-ROUTING-SPEC.md
│   └── SKILL-TRIGGER-RELIABILITY-SPEC.md
├── directive/                 # Compact directives for project instruction files
│   ├── SKILL-GOVERNANCE-DIRECTIVE.md
│   └── SKILL-GOVERNANCE-INIT.md
├── guides/                    # Authoring guides, patterns, and prompt templates
│   ├── skill-authoring-standard.md
│   ├── skill-engineering-patterns.md
│   ├── skill-precommit-hooks.md
│   ├── skill-cicd-pipeline.md
│   ├── skill-audit-refactor-prompt.md
│   ├── context-efficient-skill-architecture.md
│   ├── building-eval-cases-guide.md
│   └── eval-case-generator-prompt.md
├── pipeline/
│   ├── pre-commit-config.yaml # Hook definitions (copy into suites)
│   ├── shell-helpers.sh       # CLI helpers for skill development
│   ├── scripts/               # Analysis and validation scripts
│   ├── config/                # Default budget, security, and routing configs
│   ├── templates/             # Scaffolding for new skills and suites
│   └── workflows/             # GitHub Actions CI workflows
└── VERSION                    # Current governance version
```

## What Belongs Where

| This repo (governance)              | Suite repos (domain-specific)               |
|--------------------------------------|---------------------------------------------|
| Specifications                       | Skills (SKILL.md files)                     |
| Pre-commit hooks                     | Reference files and scripts                 |
| CI workflow definitions              | Eval cases and trigger evals                |
| Shell helpers and analysis scripts   | Budget overrides (`pipeline/config/`)       |
| Templates and scaffolding            | Security suppressions                       |
| Default config values                | Domain-specific content                     |

Governance tooling is copied into suites by the install script. Suites override defaults through their local `pipeline/config/` files.

## Development

### Pre-commit hooks

Install pre-commit hooks for local development:

```bash
pip install pre-commit
pre-commit install
pre-commit install --hook-type commit-msg
```

Run all checks manually:

```bash
pre-commit run --all-files
```

### Shell helpers

Source the helpers in your shell profile:

```bash
source pipeline/shell-helpers.sh
```

Available commands:

| Command            | Purpose                                              |
|--------------------|------------------------------------------------------|
| `skill-wc <file>`          | Show word and estimated token count for a file |
| `skill-check <dir>`        | Run all pre-commit checks on a skill directory |
| `skill-budget <file...>`   | Check token budgets for specific files         |
| `skill-audit`              | Full compliance audit (hard checks + advisory) |
| `skill-new <name>`         | Scaffold a new standalone skill from template  |
| `skill-new-suite <name>`   | Scaffold a new skill suite from template       |
| `skill-load <suite-dir>`   | Show context load breakdown for a suite        |

### Running a full audit

```bash
skill-audit
```

This runs all hard checks (frontmatter, references, isolation, context load), then advisory checks (token budgets, prose quality), and finishes with a budget report.

## Versioning

This repo follows [semantic versioning](https://semver.org/):

- **Major**: Breaking changes -- new hard enforcement rules, renamed config keys, structural changes requiring suite migration
- **Minor**: New features, hooks, or guides that are backward compatible
- **Patch**: Bug fixes, typo corrections, clarifications

Each suite tracks the installed governance version in its `.governance-version` file. The install script checks this file during upgrades to determine what has changed.

Current version: see `VERSION` file.

## License

MIT. See [LICENSE](LICENSE).
