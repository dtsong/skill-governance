# Strategist Position -- Model Routing Decisions

## Debate 1: SOC Coordinator Tier (Sonnet vs Haiku)

**Core recommendation: Downgrade the SOC coordinator to Haiku. The 5x cost premium is not justified for classification/routing work.**

Coordinators perform one job: read the request, match it to a specialist, hand off. The spec itself states "Coordinators route, they don't reason" and lists Haiku as the default. The SOC coordinator is not doing threat analysis -- it is deciding whether to call `threat-model-skill`, `incident-response`, or `vuln-assessment`. This is pattern matching against a routing table, not security reasoning. If Haiku misroutes 1 in 20 requests, the user simply re-routes -- a low-cost recovery. At scale, a team running 50 coordinator invocations/day pays 5x for every single one, with zero quality improvement on the actual security analysis (which happens in the specialist). The "security context nuance" argument conflates the coordinator's job with the specialist's job. If the routing table is well-structured, Haiku classifies correctly. If it is not, fix the routing table rather than paying 5x to compensate for ambiguous instructions.

**Risk of being wrong:** If Haiku misroutes a subtle security request to the wrong specialist, the user wastes one round-trip. Cost of that failure: one wasted specialist invocation (~5x). Cost of the insurance policy: 5x on every coordinator call. The math favors Haiku with a good routing table.

## Debate 2: Threat-Model Skill Ceiling (Sonnet vs Opus)

**Core recommendation: Sonnet 4.6 at `preferred` is the right call, but set `minimum: sonnet` and add a conditional upgrade trigger for multi-system threat models.**

Sonnet 4.6 is the key data point here. It was preferred over Opus 4.5 by 59% of users in benchmarks, and it runs at 5x vs 25x cost -- a 5x savings per invocation. For single-system STRIDE analysis and standard attack trees, Sonnet 4.6 has the reasoning depth. The risk is in complex multi-system threat models (e.g., distributed microservices with trust boundary chains, or supply chain attack vectors across multiple dependencies). These represent maybe 10-15% of threat modeling invocations but carry disproportionate consequence if attack vectors are missed. The solution is not to run everything at Opus "just in case" -- it is to add a conditional upgrade: `when: "threat model spans 3+ trust boundaries or involves supply chain" -> hold_at: opus`. This captures the 10-15% that genuinely needs deeper reasoning while keeping 85-90% of invocations at 5x instead of 25x.

**Risk of being wrong:** A missed attack vector in a threat model is a silent failure -- the team does not know what they did not find. This is the highest-consequence debate of the three. Mitigate with the conditional upgrade trigger and periodic Opus-tier spot-checks on Sonnet-generated threat models.

## Debate 3: Opus Scope Boundary (Which Tasks Justify 25x)

**Core recommendation: The current Opus boundary is approximately correct. Hold adversarial security, formal verification, and vulnerability chain synthesis at Opus. Keep architecture decisions and research synthesis at Sonnet.**

The 5x-to-25x jump is the steepest cost boundary in the routing table. At 25x, Opus must deliver value that Sonnet cannot approximate. Adversarial security analysis (red-team thinking, finding what defenders miss) and vulnerability chain synthesis (reasoning about multi-step exploit chains) are genuinely harder reasoning tasks where missing a link in the chain means the entire analysis is wrong -- these justify the premium. Architecture decisions and research synthesis, by contrast, are tasks where Sonnet 4.6 produces 90%+ quality output. The missing 10% in an architecture decision is usually polish or edge-case consideration that a human reviewer catches anyway. The missing 10% in a vulnerability chain is an exploitable gap that nobody catches until it is exploited.

The one area I would watch is "novel data pipeline design." If "novel" means genuinely unprecedented patterns (new streaming paradigms, novel consistency models), Sonnet may produce workable-but-suboptimal designs. But workable-but-suboptimal is acceptable for a first draft that gets human review. Ship at Sonnet, escalate to Opus only if the pipeline design fails review.

**Risk of being wrong:** If Opus scope is too narrow, we get slightly lower quality on architecture/research tasks that humans review anyway -- low consequence. If Opus scope is too broad, we burn 5x more budget on every task for marginal quality gains -- high ongoing cost. Err on the side of narrower Opus scope and expand based on quality signal from evals.

## Summary of Positions

| Debate | Recommendation | Savings vs Alternative | Risk Level |
|--------|---------------|----------------------|------------|
| SOC coordinator | Downgrade to Haiku | 5x per coordinator call | Low (misroute = 1 wasted round-trip) |
| Threat-model ceiling | Sonnet default + conditional Opus upgrade | ~4x on 85-90% of invocations | Medium (silent failure on complex models) |
| Opus scope boundary | Hold current boundary, resist expansion | 5x per non-Opus analytical task | Low (human review catches architecture gaps) |

**Dependencies on other domains:**
- Architect: Validate that the conditional upgrade trigger for threat-model is implementable within the current frontmatter schema (`conditions` block in model config)
- Advocate: Confirm that Haiku coordinator routing does not degrade the user experience for security practitioners who expect premium handling
- Guardian: Assess whether the "silent failure" risk on Sonnet threat models requires a mandatory Opus spot-check cadence
