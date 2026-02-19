# Skeptic Position -- Model Routing Decisions

## Debate 1: SOC Coordinator Tier (Sonnet vs Haiku)

**Core concern: Misrouting in security is a silent failure mode with compounding downstream impact.**

The spec is explicit: "Coordinators only route, haiku is sufficient" (Degradation Cascade Step 1, `model-routing.yaml` line 8-10). Every other coordinator defaults to Haiku. The SOC coordinator is the exception, running at Sonnet (5x cost). The question is whether security routing classification is genuinely harder than other domains. I argue it is, but not by enough to justify Sonnet permanently. The failure mode here is subtle: a request like "review our session handling" could route to a generic code review skill instead of the session-fixation specialist. With Haiku, that misclassification risk is real because security domain boundaries are ambiguous -- "authentication" overlaps with "API design," "input handling" overlaps with "data transformation." However, I need evidence before accepting the cost. **What would convince me the current Sonnet routing is safe to keep:** a routing accuracy eval comparing Haiku vs Sonnet on 30+ ambiguous security classification prompts, with pass/fail on correct specialist selection. If Haiku scores above 90% on ambiguous cases, downgrade it. If it drops below 80%, keep Sonnet. Without that data, we are paying 5x on vibes. **Severity: Medium.** The coordinator runs cheaply regardless (low token count per invocation), so the absolute cost difference is small even at 5x. The risk is real but bounded.

## Debate 2: Threat Model Skill Ceiling (Sonnet vs Opus)

**Core concern: A threat model that misses attack vectors is worse than no threat model, because it creates false confidence.**

This is the highest-stakes routing decision in the entire config. STRIDE analysis and attack tree construction are exactly the "adversarial security analysis" and "vulnerability chain synthesis" that the spec reserves for Opus (`model-routing.yaml` lines 35-36). Yet `threat-model-skill` is routed to Sonnet with `reasoning_demand: high`. That is a contradiction in the spec's own logic. The failure mode is not "slightly worse output" -- it is missing entire threat categories. Sonnet will competently enumerate the obvious vectors (SQL injection, XSS, CSRF) but is more likely to miss second-order chains: "attacker exploits SSRF to reach internal metadata service, pivots to IAM credential theft, escalates to cross-tenant data access." Those multi-hop chains require exactly the deep adversarial reasoning Opus provides. A threat model that covers 80% of vectors gives the team 100% confidence, which means the missed 20% gets zero mitigation. **Non-negotiable:** if the threat-model skill stays at Sonnet, it must include an explicit caveat in its output: "This analysis was performed at the Sonnet tier and may not capture multi-stage attack chains. For high-value targets, re-run at Opus." Alternatively, use the Cascade Execution Pattern (spec Section 6.1): Sonnet does the initial STRIDE pass, then Opus reviews only the high-impact findings for missed chains. This limits Opus usage to the verification step rather than the full analysis. **Severity: High.** Security analysis that creates false confidence is actively harmful.

## Debate 3: Opus Scope Boundary (Security Implications in Non-Security Tasks)

**Core concern: The boundary between "security task" and "task with security implications" is porous, and routing ignores the latter category entirely.**

The current routing draws a bright line: explicit security tasks go to Sonnet/Opus, everything else goes to Sonnet or below. But consider: an architecture review skill running at Sonnet evaluates a proposed microservice decomposition. It competently assesses coupling, scalability, and API design. It does not flag that the proposed service-to-service auth uses shared API keys instead of mTLS, because it is not thinking adversarially -- that is not its routing mandate. The architecture is "correct" but insecure. This is the Swiss cheese model in action: the architecture skill has a security-shaped hole, and the security skill never sees the architecture proposal because nobody classified it as a "security task." The failure mode is organizational, not technical -- it is the same reason security reviews happen too late in real engineering orgs. **Mitigation:** I do not think routing everything to Opus is the answer (cost would be prohibitive). Instead, the spec needs a "security touchpoint" mechanism: for any skill tagged with `security_adjacent: true` (architecture, API design, data modeling, infrastructure), the coordinator should append a lightweight security checklist to the specialist's context. This keeps the skill at Sonnet but ensures it checks for auth, authz, encryption-at-rest, and input validation even when the primary task is not security-focused. **Severity: Medium.** This is a real gap but mitigable without tier changes.

## Summary of Positions

| Debate | Recommendation | Severity |
|--------|---------------|----------|
| SOC coordinator tier | Conditional: keep Sonnet only if eval data shows Haiku accuracy drops below 80% on ambiguous routing. Otherwise downgrade. | Medium |
| Threat model ceiling | Escalate: either route to Opus, use Cascade pattern (Sonnet + Opus verification pass), or add mandatory confidence caveat to Sonnet-tier output. | High |
| Opus scope boundary | Augment: add `security_adjacent` tag and lightweight security checklist injection for non-security skills that touch security-relevant domains. | Medium |

## Dependencies on Other Domains

- **Architect:** Need their view on whether the Cascade pattern for threat modeling adds unacceptable latency or complexity to the skill execution flow.
- **Craftsman:** Need eval framework support for routing accuracy benchmarks (Debate 1) and tier-comparison evals (Debate 2).
- **Strategist:** Need cost modeling for Opus threat-model runs vs the risk cost of missed vulnerabilities. The 25x multiplier looks expensive until you price a security incident.
