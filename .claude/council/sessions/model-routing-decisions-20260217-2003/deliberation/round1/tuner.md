# Tuner Position — Round 1

## Debate 1: SOC Coordinator Tier (Sonnet vs Haiku)

**Core recommendation:** Keep coordinators at Haiku.

Coordinators are the hot path -- they fire on every single skill suite invocation. At the current config (`model-routing.yaml` line 8), coordinators default to `preferred: haiku` at 1x cost. Moving the SOC coordinator to Sonnet (5x) means every security suite invocation pays a 5x multiplier before any specialist work even begins. If the suite handles N requests/day, that is 4N haiku-equivalents of pure overhead. The coordinator token footprint is small (the spec's session summary example shows ~1,200 tokens for a coordinator call at line 417), but the multiplier applies to every invocation regardless. The degradation cascade in the spec (line 166-167) explicitly lists "Downgrade coordinators to haiku" as Step 1 of budget pressure response, confirming coordinators are the first thing to shed cost on. Unless there is measured evidence that Haiku misroutes security requests at an unacceptable rate (I would want to see >5% misclassification on a representative sample), the 5x premium is not justified for what is fundamentally a classification and dispatch task -- low `reasoning_demand` by definition.

**Quantitative target:** Coordinator routing accuracy must exceed 95% at Haiku. If it does, the 5x premium buys nothing measurable. If it does not, the cost of re-runs from misrouting (~2x specialist cost per misroute) must be modeled against the 5x constant overhead.

## Debate 2: Threat-Model Skill Ceiling (Sonnet vs Opus)

**Core recommendation:** Sonnet as preferred is the right default, with a conditional escalation path to Opus.

The cost math favors Sonnet strongly: at 5x vs 25x, Sonnet is 5 times cheaper per invocation. The question is where the quality curve bends. Sonnet 4.6's 59% user preference over Opus 4.5 and its documented improvement in long-horizon planning suggest the quality gap has narrowed significantly at the analytical tier. For single-vector threat models and standard STRIDE/attack-tree analysis, Sonnet 4.6 likely delivers near-parity with Opus. The risk zone is multi-vector adversarial scenarios where the model must hold multiple attack chains in working memory simultaneously and reason about their interactions -- this is where Opus's deeper reasoning could produce materially different output. The spec already supports this pattern via the `conditions` block (lines 67-72): set `preferred: sonnet` with a condition like `when: "multi-vector or chained attack scenario" hold_at: opus`. This gives you 5x cost on the common case and 25x only when the reasoning demand actually justifies it. Without eval data comparing Sonnet vs Opus on representative threat model scenarios, I would estimate 80-90% of threat modeling tasks stay at Sonnet, with 10-20% escalating -- yielding an effective blended cost of ~9x haiku rather than a flat 25x.

**Quantitative target:** Run the threat-model eval suite at both tiers. If Sonnet passes >90% of must-pass cases, keep it as preferred with conditional Opus escalation.

## Debate 3: Opus Scope Boundary (60x to 25x)

**Core recommendation:** The 58% cost reduction changes the boundary meaningfully, but Opus should still be reserved for tasks where quality measurably degrades at Sonnet.

The old 60x ratio created a strong economic barrier -- a task needed to be worth 60 Haiku-equivalent calls to justify one Opus call. At 25x, the break-even threshold drops by more than half. Concretely: if an Opus call prevents even one re-run that would cost 25 Haiku-equivalents (or 5 Sonnet-equivalents), it pays for itself. This makes Opus viable for more tasks, but "viable" should not mean "default." The optimization target is the cost-quality Pareto frontier: Opus should be used precisely where the quality delta between Sonnet and Opus exceeds the 5x cost delta between them. The sharpest inflection point in the cost curve is at the Sonnet-to-Opus boundary -- going from 5x to 25x is still a 5x jump even after the reduction. Tasks that genuinely need adversarial reasoning, formal verification, or vulnerability chain synthesis (as defined in `model-routing.yaml` line 36) clear this bar. Tasks that are "hard but not adversarial" -- like complex code review or architectural analysis -- likely do not, given Sonnet 4.6's improved reasoning. I would widen the Opus boundary slightly (perhaps adding "novel zero-day analysis" or "cross-system attack surface mapping") but keep the bar at "measurable quality gap at Sonnet," not "slightly better at Opus."

**Quantitative target:** Define the Opus boundary as: tasks where Sonnet eval pass rate drops below 80% on must-pass cases, OR where the cost of a missed finding (security context) exceeds 5x the Opus invocation cost.

## Dependencies on Other Domains

- **Oracle:** Empirical quality benchmarks for Sonnet 4.6 vs Opus on reasoning-heavy security tasks. Without this data, all boundary decisions are estimates.
- **Skeptic:** What is the actual blast radius of a misrouted security request? This determines whether the coordinator accuracy threshold should be 95% or 99%.
- **Strategist:** Budget allocation across the portfolio. If Opus budget is finite (weekly message limits), the boundary decision is not just cost-per-call but opportunity cost -- every Opus call on a marginal task is one fewer for a critical task.
