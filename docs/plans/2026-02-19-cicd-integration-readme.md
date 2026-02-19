# CI/CD Integration Section Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a "CI/CD Integration" section to README.md that serves both evaluating adopters (understand the CI story) and active integrators (enough detail to wire it up).

**Architecture:** Insert one new top-level section between "How It Works" and "Documentation". The section contains a four-row pipeline stage table and three short subsections: what install.sh sets up, what secrets/config are needed, and how to customize per repo.

**Tech Stack:** Markdown only — no code changes.

---

### Task 1: Insert the CI/CD Integration section into README.md

**Files:**
- Modify: `README.md` (between the `### Governance Workflow` subsection and `## Documentation`)

**Step 1: Locate the insertion point**

Open `README.md` and confirm the line that reads `## Documentation` — the new section goes immediately before it.

**Step 2: Insert the section**

Add the following block directly before `## Documentation`:

```markdown
## CI/CD Integration

`install.sh` installs four GitHub Actions workflows into your repo. Each maps to a distinct stage of the pipeline:

| Stage | Trigger | Checks | Blocking |
|-------|---------|--------|----------|
| 1 · Lint & Validate | Every push | Token budgets · frontmatter · reference integrity · cross-skill isolation | Yes — blocks merge |
| 2 · Static Analysis | Every PR | Pattern compliance · writing rules · portability · context load | Advisory — PR comment |
| 3 · Eval Execution | Merge to main · manual | Runs eval cases · regression detection | Yes — on regression |
| 4 · Publish | Release tag | Packages skills · version bump · distribute | — |

### What `install.sh` sets up

- `.github/workflows/skill-lint.yml` — Stage 1, runs on every push to `skills/**`
- `.github/workflows/skill-analyze.yml` — Stage 2, runs on every PR touching `skills/**`
- `.github/workflows/skill-eval.yml` — Stage 3, runs on merge to main; also manually dispatchable
- `.github/workflows/skill-publish.yml` — Stage 4, runs on `v*` tags
- `pipeline/scripts/` — validation, analysis, and eval scripts
- `pipeline/config/` — budget thresholds, security rules, routing config
- `.githooks/pre-commit` — local enforcement before commits reach CI

### What you need

- GitHub Actions enabled on your repo
- `ANTHROPIC_API_KEY` secret added to repo settings (Stage 3 eval execution only — Stages 1–2 have no API dependency)

### Customizing per repo

Per-skill budget overrides go in `pipeline/config/budgets.json` with a `reason` field. Security scan suppressions go in `pipeline/config/security-suppressions.json`. Both files are preserved on upgrade. See the [CI/CD Pipeline guide](guides/skill-cicd-pipeline.md) for the full configuration reference.

```

**Step 3: Verify the section renders correctly**

Check that:
- The table has four rows with the correct stage labels, triggers, checks, and blocking status
- All four `skill-*.yml` filenames are correct
- The `ANTHROPIC_API_KEY` note correctly scopes to Stage 3 only
- No other sections were modified

**Step 4: Commit**

```bash
git add README.md docs/plans/2026-02-19-cicd-integration-readme.md
git commit -m "docs(readme): add CI/CD integration section"
```
