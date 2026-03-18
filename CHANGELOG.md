# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v1.5.0] - 2026-03-18

### Added
- **Cross-Skill Composition** (§2.6) — skills may reference other skills by name; runtime-resolved, not context-loaded. Optional `depends_on` frontmatter field.
- **Setup & Configuration** (§5.9) — `config.json` pattern for user-specific settings with `config` frontmatter block for declaring expected keys.
- **Data Persistence** (§5.10) — guidance on `${CLAUDE_PLUGIN_DATA}` for durable cross-session storage, acceptable formats, and self-prune advisory.
- **Session Hooks** (§9.6) — skills can register session-scoped PreToolUse/PostToolUse hooks via frontmatter `hooks` block.
- **Distribution & Marketplace Lifecycle** (§11) — two distribution paths (repo-checked vs marketplace), lifecycle stages (draft → sandbox → published → promoted), curation criteria.
- New optional frontmatter fields: `config`, `hooks`, `depends_on`, `distribution`.
- Frontmatter validation for new fields in `check_frontmatter.py`.
- Shell helpers: `skill-init-config` and `skill-validate-config`.
- `config.json.example` template for standalone skills.
- `config.json` validation in `validate-structure.sh`.
- `config.json.example` included in `package-skill.sh` output.

### Changed
- **Conciseness hierarchy** (§4.1) — strengthened with "focus on information that pushes Claude OUT of its default behavior" principle.
- **Helper Scripts** (§5.7) — expanded with composable script library guidance (`scripts/lib/`).
- **Observability** (§10) — added undertrigger detection, `trigger_source` telemetry field, undertrigger analysis in 30-day review.
- **Isolation hook** (`check_isolation.py`) — tightened `alt_patterns` to path-specific matches, allowing name-only composition references.
- Enforcement tier mapping (§8.2) updated with rules for `config`, `hooks`, `depends_on`, `distribution`, and persistent data.
- Quick Reference Card updated with composition, config, hooks, and persistence sections.

## [v1.3.0] - 2025-02-15

### Added
- Degrees of Freedom framework for calibrating instruction specificity per procedure step (low/medium/high freedom).
- "Claude Already Knows This" as the first test in the conciseness hierarchy -- cut explanations of concepts the model already has from training.
- Third-person description requirement for frontmatter -- descriptions are injected into system prompts alongside other skills, so consistent point-of-view is required.
- One-level-deep reference rule to prevent partial file reads -- reference files must not reference other reference files.
- Feedback loops and progress tracking patterns (R1, Q7) for multi-step procedures.
- Verifiable intermediate outputs pattern (Q8) -- plan-validate-execute for batch and destructive operations.
- Compaction resilience patterns (R2) for surviving context window resets during long procedures.
- Time-sensitive content deprecation rules -- no temporal references without version context.
- Script robustness requirements -- explicit error handling, documented constants, verbose error messages, dependency documentation.
- MCP tool reference format requirements -- fully qualified `ServerName:tool_name` format to avoid resolution failures.
- Visual analysis as a quality pattern (Q9) -- convert output to image and verify visually.
- Platform feature integration for Claude Code: `context: fork` for subagent isolation and shell preprocessing (`!command` syntax).

### Changed
- Enforcement tier mapping updated with new validation rules for one-level-deep references, description quality, MCP tool format, script quality, and temporal references.
- Extracted governance into this standalone repo (previously embedded in skill suite repos).

## [v1.2.0] - 2025-01-15

### Added
- SKILL-MODEL-ROUTING-SPEC.md defining budget-aware model degradation zones (green/yellow/red).
- Frontmatter `model` block for per-skill tier preferences (`preferred`, `acceptable`, `minimum`, `allow_downgrade`, `reasoning_demand`).

### Changed
- Model tier annotations replaced with model routing configuration -- skills now declare model preferences in structured frontmatter rather than inline annotations.

## [v1.1.1] - 2025-01-10

### Added
- SKILL-SECURITY-SPEC.md defining threat model, static analysis rules, and escape hatch conventions.
- Security added as priority number 2 in the optimization hierarchy (after output quality, before structural integrity).
- Security rules added to enforcement tier mapping -- all classified as Hard tier.
- Security hook (`skill-security`) runs first in both pre-commit and CI pipelines.

## [v1.1.0] - 2025-01-01

### Changed
- Per-file token budgets reclassified from hard limits to guideline targets -- exceeding targets is acceptable when justified by output quality.
- Suite context load ceiling remains the only hard budget limit.
- Pre-commit budget checks changed from blocking to warning (advisory tier).
- Enforcement rebalanced to prioritize structural integrity over compression.

### Added
- Guidance on when to exceed budgets and documentation requirements (overrides in `budgets.json` with eval data).
- Quality-over-compression principle added to writing rules.

## [v1.0.0] - 2024-12-15

### Added
- Initial specification release (SKILL-GOVERNANCE-SPEC.md).
- Core skill architecture: coordinator, specialist, standalone, and reference file types.
- Progressive loading model: Layer 1 (coordinator) routes to Layer 2 (specialist) which references Layer 3 (reference files).
- Token budget enforcement as hard limits: coordinator 800 tokens, specialist/standalone 2000 tokens, reference 1500 tokens, suite ceiling 5500 tokens.
- Pre-commit hooks: frontmatter validation, reference integrity, cross-specialist isolation, suite context load.
- Skill suite templates for scaffolding new suites and standalone skills.
- Eval case standards with tiered grading rubrics (must pass, should pass, bonus).
- Cross-platform compatibility rules for Claude Code and OpenAI Codex.
- Commit message convention for skill-related changes.

[v1.5.0]: https://github.com/dtsong/skill-governance/compare/v1.4.0...v1.5.0
[v1.3.0]: https://github.com/dtsong/skill-governance/compare/v1.2.0...v1.3.0
[v1.2.0]: https://github.com/dtsong/skill-governance/compare/v1.1.1...v1.2.0
[v1.1.1]: https://github.com/dtsong/skill-governance/compare/v1.1.0...v1.1.1
[v1.1.0]: https://github.com/dtsong/skill-governance/compare/v1.0.0...v1.1.0
[v1.0.0]: https://github.com/dtsong/skill-governance/releases/tag/v1.0.0
