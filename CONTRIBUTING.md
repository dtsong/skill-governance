# Contributing

## Proposing Spec Changes

Open an issue before submitting a PR for spec changes. Include:

1. **Which spec and section** -- e.g., "SKILL-GOVERNANCE-SPEC.md, Section 4.2 Procedure Sections"
2. **The problem** -- What is broken, unclear, or missing? Include concrete examples if possible.
3. **Proposed change** -- Describe the specific modification. Draft the new wording if you can.

Small fixes (typos, broken links, clarifications that do not change behavior) can go directly to a PR without an issue.

## PR Process

1. Fork the repo and create a branch from `main`.
2. Make your changes.
3. Run all checks locally:
   ```bash
   pre-commit run --all-files
   ```
4. If you modified hooks or scripts, run them against at least one real skill suite to verify behavior.
5. Submit a PR with a clear description of what changed and why.

### PR requirements

- One logical change per PR. Do not bundle unrelated spec changes with hook fixes.
- Spec changes must update the changelog section within the spec file itself (e.g., the "Changes in vX.Y" section at the top of `SKILL-GOVERNANCE-SPEC.md`).
- Hook changes must include or update tests.
- All CI checks must pass.

## Versioning Rules

This repo follows [semantic versioning](https://semver.org/):

| Change type | Version bump | Examples |
|-------------|-------------|----------|
| **Major** | X.0.0 | New hard enforcement rule that blocks previously-passing suites. Renamed config keys. Restructured directory layout. |
| **Minor** | x.Y.0 | New hook (advisory or hard). New spec section. New guide or template. New shell helper. All backward compatible. |
| **Patch** | x.y.Z | Bug fix in a hook. Typo correction in a spec. Clarification that does not change enforcement behavior. |

The version is tracked in the `VERSION` file at the repo root.

## Spec Modification Rules

Spec changes carry downstream impact -- every suite that pulls governance tooling is affected. Extra care is required:

1. **Pilot migration required.** Changes to specs or hard-enforcement hooks must be tested against at least one real skill suite before the PR is merged. Include the pilot results (what changed, what broke, how it was resolved) in the PR description.

2. **Changelog in the spec.** Every spec file contains its own changelog section near the top. Update this section as part of your change. Do not rely solely on the repo-level CHANGELOG.md.

3. **No silent enforcement changes.** If a change causes a previously-passing suite to fail (new hard rule, stricter validation), it is a major version bump regardless of how small the code change is.

4. **Advisory before hard.** New validation rules should ship as advisory (warn tier) first. Promote to hard enforcement in a subsequent release after suites have had time to adapt.

## Hook Development

All hooks live in `pipeline/hooks/` and share utilities from `_utils.py`.

### Requirements

- **Use `_utils.py`** for shared functions (token estimation, frontmatter parsing, file discovery). Do not duplicate this logic.
- **Default to advisory.** New hooks should warn, not block, unless the rule is already classified as Hard tier in the spec's enforcement tier mapping (Section 8.2).
- **Include tests.** Add test cases that cover passing files, failing files, and edge cases (empty files, missing frontmatter, deeply nested references).
- **Respect excludes.** Honor the `exclude` patterns in `pre-commit-config.yaml` -- templates, eval cases, and pipeline files are excluded from skill checks.
- **Stay fast.** Pre-commit hooks must complete in under 2 seconds for typical suite sizes.

### Testing hooks locally

```bash
# Run a single hook against specific files
pre-commit run skill-frontmatter --files path/to/SKILL.md

# Run all hooks against all files
pre-commit run --all-files
```

## Commit Messages

Follow the convention defined in the spec:

```
skill(name): description          -- skill or major change
skill-fix(name): description      -- bug fix
skill-ref(name): description      -- refactor
skill-eval(name): description     -- eval case changes
skill-docs(name): description     -- documentation only
chore(pipeline): description      -- pipeline/tooling changes
```
