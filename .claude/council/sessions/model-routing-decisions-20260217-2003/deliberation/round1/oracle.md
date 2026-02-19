# Oracle Position -- Model Routing Decisions

## Debate 1: SOC Coordinator Tier (Sonnet vs Haiku)

**Core recommendation: Downgrade the SOC coordinator to Haiku, but invest the savings in a better routing table.**

Coordinators are classification functions, not reasoning engines. The task is: given a user request, select from a finite set of specialists. This is a bounded classification problem with a known label space -- exactly what smaller models handle well when given explicit decision criteria. Sonnet 4.6 and Haiku produce near-identical accuracy on well-structured classification tasks with clear routing tables; the gap only widens on ambiguous, open-ended reasoning. If the SOC coordinator's routing table has fuzzy boundaries (e.g., "review session handling" could be auth-security or general code review), the fix is to sharpen the routing table's decision criteria and add disambiguation examples, not to throw a 5x model at an underspecified prompt. I have seen this pattern repeatedly in production LLM systems: upgrading the model compensates for a weak prompt, but the prompt fix is both cheaper and more reliable. The one valid concern -- that security misrouting has higher blast radius than other domains -- is real but addressable: add a "confidence threshold" instruction to the coordinator prompt where ambiguous requests get routed to a general security triage skill rather than a wrong specialist.

**Dependency:** Tuner's suggestion of a 95% routing accuracy threshold at Haiku is the right bar. If the routing table is well-structured with few-shot examples, Haiku should clear that easily.

## Debate 2: Threat-Model Skill Ceiling (Sonnet vs Opus)

**Core recommendation: Sonnet 4.6 as preferred is defensible for standard STRIDE, but the skill needs a structured escalation trigger and an explicit output caveat -- not a flat Opus default.**

This is the debate where my domain expertise matters most. Sonnet 4.6 represents a genuine capability inflection point. Its 1M context window means it can hold an entire system architecture in working memory during threat analysis -- something previous Sonnet versions could not do reliably. Its reasoning improvements (59% preference over Opus 4.5 in head-to-head) put it firmly in the "analytical reasoning" tier, not just "classification." For standard STRIDE analysis against a single service or component, Sonnet 4.6 produces threat models that are structurally complete and identify the expected attack vectors. Where it falls short -- and this is measurable in eval, not speculative -- is in multi-hop adversarial chain synthesis: "attacker compromises A, pivots through B's trust relationship with C, escalates via D's overprivileged service account." These chains require holding 4-5 entities and their trust relationships simultaneously while reasoning adversarially about each link. This is where Opus's deeper reasoning still produces materially better output.

The right architecture is the Cascade pattern the Skeptic proposed, but specified precisely: Sonnet does the full STRIDE pass and attack tree construction. If the target system has 3+ trust boundaries or involves cross-service authentication chains, the skill triggers an Opus verification pass focused exclusively on multi-hop chain discovery. This limits Opus usage to roughly 15-20% of invocations (the complex cases) and brings the blended cost to approximately 8x haiku rather than a flat 25x. The skill's output should include a "coverage confidence" field: "standard" for Sonnet-only runs, "deep" for Sonnet+Opus cascade runs. This makes the quality tradeoff visible to the consumer.

**Non-negotiable:** The `conditions` block must be present. A flat `preferred: sonnet` with no escalation path for complex scenarios is an eval gap waiting to become a security gap.

## Debate 3: Opus Scope Boundary (What Justifies 25x)

**Core recommendation: The narrowed Opus scope is correct in principle. "Adversarial security analysis, formal verification, vulnerability chain synthesis" is the right boundary -- but the description should be capability-driven, not domain-driven.**

The PR's change from "Debugging, architecture, complex reasoning" to "Adversarial security analysis, formal verification, vulnerability chain synthesis" is a significant narrowing, and I think the direction is right but the framing is slightly wrong. The boundary should be defined by the cognitive operation required, not by the domain. The operations that genuinely differentiate Opus from Sonnet 4.6 are: (1) adversarial reasoning -- deliberately trying to break something, finding the path the defender missed; (2) formal constraint satisfaction -- proving properties hold across all inputs, not just tested ones; (3) long-chain causal reasoning -- following a 5+ step chain where each step depends on the previous one's conclusion being correct. These operations happen to cluster in security, but they also appear in correctness proofs, concurrency analysis, and protocol verification. The current description is fine for the security-focused skills in this repo, but if the routing spec is meant to be general-purpose, it should describe the cognitive capability, not the application domain.

Practically: architecture decisions, research synthesis, and novel data pipeline design are all tasks where Sonnet 4.6 produces output that is 90-95% as good as Opus, and the remaining 5-10% is exactly the kind of gap that human review is designed to catch. The cost-quality tradeoff does not justify 5x for that marginal improvement. The one exception I would carve out is "novel zero-day analysis" as Tuner suggested -- this is adversarial reasoning against unknown patterns, which is precisely the Opus sweet spot.

**Dependency:** All three debates ultimately need eval data to resolve definitively. I can design the eval harness: golden datasets of (1) ambiguous routing requests for coordinator accuracy, (2) threat model scenarios at varying complexity for Sonnet-vs-Opus quality comparison, and (3) architecture/research tasks for Opus boundary validation. Without evals, we are making informed guesses -- and informed guesses are fine for a v1.4 spec, but the spec should mandate eval-based validation in Phase 4.

## Summary of Positions

| Debate | Recommendation | Key Insight |
|--------|---------------|-------------|
| SOC coordinator | Downgrade to Haiku + sharpen routing table | Model upgrade compensates for prompt weakness; fix the prompt instead |
| Threat-model ceiling | Sonnet preferred + conditional Opus cascade for multi-hop chains | Sonnet 4.6 handles single-system STRIDE; Opus adds value only on multi-hop adversarial chains |
| Opus scope boundary | Current boundary is correct; reframe as cognitive operation, not domain | Adversarial reasoning, formal verification, long-chain causality -- these are Opus differentiators regardless of domain |

## Dependencies on Other Domains

- **Skeptic:** Align on the "confidence threshold" approach for coordinator ambiguity handling -- route to triage rather than guess.
- **Tuner:** Need agreement on eval thresholds: 95% coordinator accuracy, 90% threat-model must-pass at Sonnet.
- **Strategist:** The blended cost model (8x haiku for cascade threat modeling vs 25x flat Opus) needs validation against actual budget constraints and weekly Opus message limits.
