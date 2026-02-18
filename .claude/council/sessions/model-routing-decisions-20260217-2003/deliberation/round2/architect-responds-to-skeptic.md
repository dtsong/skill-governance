# Architect Response to Skeptic -- Debate 3: Opus Scope Boundary

## Their position

Skeptic proposes a `security_adjacent` tag that injects a lightweight security checklist into non-security skills (architecture, API design, data modeling) when they touch auth, authz, encryption, or input validation domains. This keeps those skills at Sonnet but patches the "security-shaped hole" by appending security considerations to the specialist's context. No tier change needed.

## My response: Modify

## Reasoning

Skeptic's `security_adjacent` tag and my cognitive-operations boundary are **complementary solutions to different problems**, not competing ones. They operate at different layers of the routing architecture:

1. **My proposal (cognitive-operations boundary)** answers: "When should we pay for Opus?" It redefines the `reasoning` task type around cognitive properties -- chain depth, branching factor, consequence of error -- so that routing decisions are domain-agnostic. This is a change to the `task_types` table in `model-routing.yaml` (lines 27-36).

2. **Skeptic's proposal (security_adjacent tag)** answers: "How do we ensure non-security skills don't ignore security concerns?" It is a context-augmentation mechanism that appends checklist items to a specialist's prompt. This is a change to skill frontmatter and coordinator dispatch logic.

These are orthogonal. One governs model selection; the other governs prompt composition. They can coexist without conflict.

However, I have three architectural concerns with the `security_adjacent` tag as proposed:

**Concern 1: It is a domain-specific patch to a general problem.** The Swiss cheese observation -- that a skill has blind spots outside its domain -- is not unique to security. An architecture skill might miss performance implications. A data modeling skill might miss UX implications. If we add `security_adjacent`, the pattern demands `performance_adjacent`, `accessibility_adjacent`, and so on. Each new tag adds a cross-cutting concern to the coordinator dispatch logic, and the coordinator prompt grows linearly with the number of adjacency domains. This is the wrong shape. The general solution is a "cross-concern checklist injection" mechanism where any skill can declare which cross-cutting checklists are relevant, and the coordinator appends them. Security is just one instance.

**Concern 2: Checklist injection inflates context without guaranteeing attention.** Appending a security checklist to a Sonnet-tier architecture review does not mean the model will actually reason about those items. A checklist that says "check for mTLS vs shared API keys" only works if the model understands why mTLS matters in the specific context. Sonnet will dutifully mention the checklist items but may not catch the subtle cases -- those are exactly the high-branching-factor adversarial reasoning tasks that my cognitive-operations boundary routes to Opus. The checklist creates a false sense of coverage: "we checked for security" when we actually just appended keywords.

**Concern 3: It conflates routing logic with prompt engineering.** The routing config (`model-routing.yaml`) should govern model selection and budget behavior. Prompt augmentation -- injecting checklists, appending instructions -- belongs in the skill's own prompt template or the coordinator's dispatch logic, not in the routing spec. Mixing these concerns makes the routing config harder to reason about and test.

## What I would change

1. **Generalize the mechanism.** Replace `security_adjacent: true` with a `cross_concerns: [security, performance, ...]` array in skill frontmatter. The coordinator loads the relevant checklist file(s) from a shared `cross-concerns/` directory. This keeps the routing config clean and the concern injection extensible.

2. **Pair it with the cognitive-operations boundary.** If the cognitive-operations reframe is adopted (as Oracle and I both propose), the `reasoning` task type description becomes: "Tasks requiring adversarial reasoning, formal constraint satisfaction, or long-chain causal reasoning (5+ steps) regardless of domain." Skills tagged with `cross_concerns: [security]` that also meet this cognitive threshold still escalate to Opus. The checklist handles the 90% case (remind the model to think about security); the cognitive boundary handles the 10% case (the model actually needs deeper reasoning to catch the subtle issue).

3. **Add a "coverage disclaimer" to checklist-augmented output.** When a non-security skill runs with an injected security checklist, its output should include a note: "Security considerations were evaluated via checklist augmentation, not dedicated adversarial analysis. For high-value targets, request a dedicated security review." This addresses the false-confidence problem Skeptic correctly identified in Debate 2.

## Does the cognitive-operations reframe make the tag redundant?

No. Even with a cognitive-operations boundary for Opus, the `security_adjacent` / `cross_concerns` mechanism still serves a purpose. The cognitive boundary only helps when a task is routed to Opus -- it does not help when a Sonnet-tier architecture review simply never considers security at all. The checklist injection ensures that security (or any cross-cutting concern) is at least surfaced in the prompt, even for tasks that do not meet the Opus cognitive threshold. The two mechanisms work together:

- **Cross-concern checklist** = "remember to think about this"
- **Cognitive-operations boundary** = "you need a more capable model to think about this well"

The checklist is necessary but not sufficient. The cognitive boundary is sufficient but not always triggered. Together, they provide defense in depth.

## Dependencies

- **Tuner:** The `cross_concerns` mechanism needs a reference file format and token budget allocation. Each injected checklist consumes context tokens; this must be accounted for in the 5,000-token simultaneous context ceiling.
- **Skeptic:** Align on whether the generalized `cross_concerns` mechanism addresses the original concern, or whether security specifically needs special treatment beyond what a generic mechanism provides.
