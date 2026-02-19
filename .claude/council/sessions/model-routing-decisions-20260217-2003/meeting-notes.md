# Council Meeting: Model Routing Decisions — Sonnet 4.6 PR
**Date:** 2026-02-17
**Panel:** Oracle, Strategist, Skeptic, Architect, Tuner
**Session ID:** model-routing-decisions-20260217-2003
**Mode:** --meet (discussion only, no action plan)

## Topic
Three ambiguous routing decisions in `chore/sonnet-4.6-model-routing` that were
not council-validated before the PR was prepared. Branch: `chore/sonnet-4.6-model-routing`.

---

## Opening Perspectives (Round 1)

### Debate 1: SOC Coordinator Tier — Sonnet vs Haiku?

**Oracle:** Downgrade to Haiku. Coordinators are bounded classification. A sharper routing table with few-shot examples and an ambiguity-triage fallback will match Sonnet accuracy at 1/5th the cost. Model upgrades compensate for weak prompts — fix the prompt instead.

**Strategist:** Downgrade to Haiku. Coordinators classify and route; they don't reason about security. A well-structured routing table eliminates misrouting risk at 1x cost. If Haiku misroutes, one wasted round-trip is cheaper than paying 5x on every call.

**Skeptic:** Haiku — but needs eval data first. Security routing has harder ambiguous boundaries (e.g., "authentication" vs "API design") than other domains. Threshold: if Haiku scores above 90% on ambiguous cases in a 30+ prompt eval, downgrade. Without eval data, the 5x premium is paid on vibes.

**Architect:** Keep all coordinators at Haiku. Classification complexity is a function of routing table branching factor, not domain risk. The spec explicitly states coordinators route, they don't reason. If the SOC coordinator's routing table is ambiguous, sharpen the table — don't upgrade the model tier.

**Tuner:** Keep at Haiku. Coordinators are the hot path — 5x overhead on every invocation is unjustified for a classification/dispatch task. The spec's degradation cascade sheds coordinator cost first. Threshold: need evidence of >5% misroute rate at Haiku before upgrading.

### Debate 2: threat-model-skill Ceiling — `preferred: sonnet` + `reasoning_demand: high`?

**Oracle:** Sonnet 4.6 as preferred is defensible for standard STRIDE. Mandatory `conditions` block for Opus cascade on multi-hop adversarial chains (3+ trust boundaries). Blended cost ~8x haiku vs flat 25x.

**Strategist:** Sonnet 4.6 default is correct, but add a conditional upgrade trigger for complex multi-system threat models (3+ trust boundaries, supply chain vectors). 85-90% of invocations stay at 5x; 10-15% escalate for the high-consequence cases.

**Skeptic (HIGH SEVERITY):** The spec explicitly reserves "adversarial security analysis" and "vulnerability chain synthesis" for Opus, yet the threat-model skill runs at Sonnet. This is a contradiction. Sonnet will enumerate obvious vectors but miss multi-hop attack chains (SSRF → metadata → IAM escalation). A threat model covering 80% of vectors gives 100% confidence, meaning the missed 20% gets zero mitigation.

**Architect:** The combination `preferred: sonnet` + `reasoning_demand: high` is an **invalid schema state**. In the degradation cascade, `reasoning_demand: high` means "hold at opus in yellow zone," but a sonnet-preferred skill never reaches opus — the cascade only downgrades from preferred, it never upgrades. This makes `high` functionally identical to `medium` with `minimum: sonnet`. The validator should reject this combination.

**Tuner:** Sonnet as preferred is correct, with conditional Opus escalation via `conditions` block for multi-vector scenarios. Blended cost estimate ~9x haiku vs flat 25x. Need eval data to confirm Sonnet passes >90% of must-pass threat model cases.

### Debate 3: Opus Scope Boundary — Too Narrow?

**Oracle:** The narrowed boundary is correct, but should be reframed as **cognitive-operation-driven** rather than domain-driven: adversarial reasoning, formal constraint satisfaction, and long-chain causal reasoning are what differentiate Opus from Sonnet 4.6 — regardless of whether the task is security or architecture.

**Strategist:** Current boundary is approximately right. Architecture decisions and research synthesis are safe at Sonnet because humans review the output anyway. Err narrow on Opus scope; expand based on eval signal.

**Skeptic:** The bright line between "security task" and "task with security implications" is porous. Architecture reviews at Sonnet will miss security gaps (shared API keys vs mTLS) because adversarial thinking is not in their routing mandate. Proposes a `security_adjacent` tag that injects a lightweight security checklist into non-security skills touching auth, authz, encryption, and input validation domains. No tier change needed.

**Architect:** The current `reasoning` task type description is too narrow and too security-domain-specific. Should be reformulated around cognitive properties — chain depth, branching factor, consequence of error — rather than domain examples. Missing categories: multi-step causal reasoning across system boundaries, adversarial reasoning in non-security contexts, novel problem solving.

**Tuner:** Don't widen default Opus scope. The 60x→25x drop doesn't change the boundary (only lowers break-even). Widen slightly for novel zero-day and cross-system attack surface analysis, but keep the bar at "measurable quality gap."

---

## Cross-Examination Highlights (Round 2)

### Skeptic vs Strategist on Debate 2: Is Cascade mandatory?

**Skeptic's challenge:** The conditional upgrade trigger has a fatal self-assessment flaw. Sonnet is the model deciding whether it needs Opus, and Sonnet lacks the adversarial depth to identify the very complexity signals (hidden trust boundaries, multi-hop chains) that would trigger the upgrade. "The model that cannot see the attack chains is the one deciding whether attack chains exist." Additionally, Architect's schema point confirms that `reasoning_demand: high` is dead code for a sonnet-preferred skill. **Verdict: Modify** — Cascade pattern required, but the schema needs to support it. Three valid paths: (a) `preferred: opus, minimum: sonnet`, (b) dishonestly downgrade to `reasoning_demand: medium` (rejected as wrong), (c) extend schema for cascade routing.

### Oracle vs Architect on Debate 2: Does `conditions` block resolve the schema contradiction?

**Oracle's concession:** Re-reading spec Section 7.1 confirms Architect is correct. The `conditions` block only defines `downgrade_to` and `hold_at` — there is no `upgrade_to` action. The cascade is exclusively a downgrade path. Oracle's Round 1 proposal ("sonnet preferred with conditions block triggering opus") is **architecturally invalid** under the current spec. **Revised position:** `preferred: opus, minimum: sonnet` with `conditions: [{when: "known STRIDE pattern, single component", downgrade_to: sonnet}]`. Blended cost ~9-15x haiku (depending on downgrade rate) vs flat 25x.

### Architect vs Skeptic on Debate 3: Cognitive boundary vs `security_adjacent` tag

**Architect's response:** The two proposals are **complementary, not competing** — they operate at different layers. The cognitive-operations boundary governs model selection (task_types table). The checklist injection governs prompt composition (context augmentation). However: (1) `security_adjacent` is a domain-specific patch to a general problem — the same concern applies to performance, accessibility, etc. Proposes generalizing to `cross_concerns: [security, performance, ...]` in frontmatter with shared checklist files. (2) Checklist injection does not guarantee reasoning quality — appending "check for mTLS" doesn't mean Sonnet catches the subtle case. Defense in depth: checklist = "remember to think about this," cognitive boundary = "you need a more capable model to think about this well." **Key conclusion:** Both mechanisms should exist as separate layers.

---

## Key Insights

- **Oracle:** Model routing decisions must be grounded in the spec's actual mechanics — the `conditions` block is a downgrade-only system. "Fix the routing table quality, not the model tier" applies to coordinators; "set preferred at the right tier and allow downgrade" applies to specialists.
- **Strategist:** The self-assessment trap (Sonnet choosing its own upgrade) is the decisive argument for `preferred: opus` on threat-model-skill. The conditional downgrade path (opus → sonnet for simple cases) achieves the same cost savings without the reliability gap.
- **Skeptic:** `reasoning_demand: high` on a sonnet-preferred skill is worse than medium — it creates false documentation that promises a safety guarantee the routing system cannot deliver.
- **Architect:** The `conditions` block architecture (downgrade from preferred) is the correct mental model for all conditional routing. The validator should enforce `reasoning_demand: high` → `preferred: opus` as a required pairing.
- **Tuner:** The 60x→25x Opus cost reduction (v1.3 → v1.4) doesn't change where quality boundaries lie, but it does lower the break-even threshold for Opus on marginal cases. The boundary should still track quality gaps, not cost ratios.

---

## Unresolved Tensions

1. **Eval data requirement (Skeptic's pre-condition for Debate 1):** Skeptic's position on SOC coordinator includes a call for routing accuracy eval before finalizing the downgrade. The council agrees with the direction (Haiku) but no eval infrastructure exists yet. Resolved by direction: downgrade now, build eval harness as follow-up.

2. **`cross_concerns` mechanism scope (Debate 3):** Architect's generalization of `security_adjacent` to a `cross_concerns` frontmatter field is agreed in principle, but this is a new schema addition — not in the current PR scope. The Opus cognitive-operation reframe is in scope; the `cross_concerns` mechanism is a follow-up.

3. **Cascade schema extension (Skeptic's Option C):** Skeptic prefers extending the schema to support true cascade routing (Sonnet → Opus verification pass). Oracle and Architect converged on `preferred: opus, minimum: sonnet` as spec-compliant. The cascade as a full extension is deferred — the simpler `preferred: opus` with downgrade conditions achieves 90% of the benefit within the current schema.

---

## Recommendations to the User

1. **SOC coordinator:** Downgrade to Haiku (`preferred: haiku, minimum: haiku, reasoning_demand: low`). Sharpen the routing table with few-shot examples and explicit ambiguity-triage logic instead. All 5 agents agree.

2. **threat-model-skill:** Set `preferred: opus, minimum: sonnet` with a `conditions` block that downgrades to sonnet for simple single-component STRIDE analysis. Remove `reasoning_demand: high` from the current `preferred: sonnet` combination — the spec validator should reject this pairing. Blended cost estimate: ~9-15x haiku vs flat 25x.

3. **Opus scope boundary in spec:** Reframe `task_types.reasoning.description` from domain-specific examples to cognitive-operation properties: "Tasks requiring adversarial reasoning, formal constraint satisfaction, or long-chain causal reasoning across system boundaries — regardless of application domain." Keep adversarial security analysis, formal verification, and vulnerability chain synthesis as examples within this framing, not as the definition itself. Add architecture, novel problem-solving, and cross-system causal reasoning as additional examples.

4. **Schema validator (follow-up PR):** Add a validation rule: `reasoning_demand: high` requires `preferred: opus`. The current combination of `preferred: sonnet + reasoning_demand: high` is dead code and should be a hard error.

5. **`cross_concerns` mechanism (future PR):** After the Opus scope reframe ships, add a generalized `cross_concerns: [security, performance, ...]` frontmatter field to enable checklist injection into skills that touch these domains without changing their model tier. This is complementary to the cognitive boundary, not a replacement.

---

## Questions for the User

1. **Scope for this PR:** The council unanimously recommends updating `task_types.reasoning.description` to a cognitive-operations framing. Is this change in scope for `chore/sonnet-4.6-model-routing`, or should it be a follow-up PR? (The model ID and cost ratio changes are already in scope; this extends the spec update further.)

2. **SOC coordinator validation:** The council recommends downgrading the SOC coordinator to Haiku, but the soc-security-skills repo is where the actual SKILL.md frontmatter lives — not in this governance repo. Does the PR description need to call out the SOC coordinator as a recommended change for adopters, or is it sufficient to note it in the spec's guidance section?

3. **threat-model-skill change scope:** Setting `preferred: opus, minimum: sonnet` for threat-model-skill is a substantive behavior change. Is this change being made in the governance spec only (as guidance), or does it need to propagate to the soc-security-skills repo as part of this PR?

---

## Recommended Next Steps

1. Update `task_types.reasoning.description` in the spec to cognitive-operation framing (Debate 3 resolution)
2. Add a note to the spec that `preferred: sonnet + reasoning_demand: high` is invalid — validator enforcement is a follow-up
3. Document the SOC coordinator tier decision as a recommended adopter action in the PR description
4. Document the threat-model-skill routing recommendation as guidance in the spec
5. Future PR: schema validator rule + `cross_concerns` frontmatter mechanism
