# Oracle Response to Architect

**Their position:** The combination `preferred: sonnet` + `reasoning_demand: high` is an invalid state because the degradation cascade only downgrades from preferred, never upgrades. `reasoning_demand: high` on a sonnet-preferred skill is functionally identical to `minimum: sonnet` + `reasoning_demand: medium`. The `conditions` block cannot resolve this because the spec's schema only defines `downgrade_to` and `hold_at` actions -- there is no `upgrade_to` action.

**My response:** Modify

**Reasoning:**

Architect is right on the schema question, and I was wrong in my Round 1 position to assume the `conditions` block could trigger an upgrade from sonnet to opus. I re-read the spec carefully:

1. **The degradation cascade (Section 2.3)** is exclusively a downgrade path. Steps 1-5 all move models downward under budget pressure. There is no corresponding "escalation cascade" that moves models upward based on task complexity.

2. **The `conditions` block schema (Section 7.1, lines 567-571)** defines exactly two actions: `downgrade_to` and `hold_at`. Neither is an upgrade action. The example in Section 1.1 (lines 67-71) uses `conditions` on a skill with `preferred: opus` -- the `hold_at: opus` action prevents downgrade, and the `downgrade_to: sonnet` action permits it for known patterns. Both are downward or holding actions relative to the preferred tier.

3. **Coordinator routing tables (Section 4.1)** do include "Upgrade Trigger" columns -- but this is the coordinator making a routing decision at dispatch time, not the budget system upgrading a running skill. The coordinator picks the tier before the specialist loads. This is a different mechanism from the `conditions` block, which operates within the budget-aware degradation system.

This means my Round 1 proposal -- "Sonnet preferred with a conditions block that triggers Opus for multi-hop chains" -- is architecturally invalid under the current spec. There is no mechanism for the budget system to upgrade a sonnet-preferred skill to opus. The `conditions` block can only prevent downgrade or force downgrade relative to the preferred tier.

**Where Architect's analysis leads us:**

For the threat-model skill, we have two valid configurations:

- **Option A: `preferred: opus, minimum: sonnet`** with `conditions: [{when: "known STRIDE pattern, single component", downgrade_to: sonnet}]`. This makes opus the default and allows the conditions block to downgrade to sonnet for simpler cases. The budget system can also downgrade to sonnet in yellow/red zones (Step 4 of cascade). This is the spec-compliant way to achieve what I wanted.

- **Option B: `preferred: sonnet, reasoning_demand: medium`** with the coordinator's routing table handling the upgrade to opus for complex cases. The coordinator sees the request, identifies multi-hop chains or 3+ trust boundaries, and dispatches at opus via the routing table's "Upgrade Trigger" column. This keeps the specialist's own model config honest (sonnet is truly its preferred tier for most runs) and delegates the complexity detection to the coordinator.

**My revised position:** Option A is cleaner because it keeps the model decision in the specialist's own frontmatter where it is auditable and testable. Option B scatters the decision across the coordinator's routing table, which makes it harder to eval -- you have to test the coordinator's classification accuracy separately from the specialist's quality at each tier.

However, Option A reverses my cost argument from Round 1. If `preferred: opus`, the blended cost is no longer ~8x haiku -- it depends on what fraction of invocations hit the `downgrade_to: sonnet` condition. If 80% of threat model requests are single-component STRIDE (downgraded to sonnet), the blended cost is approximately `0.8 * 5x + 0.2 * 25x = 9x haiku`. If only 50% are simple, it is `0.5 * 5x + 0.5 * 25x = 15x haiku`. The cost is higher than my Round 1 estimate but still significantly below a flat 25x.

**Concession:** `preferred: sonnet` + `reasoning_demand: high` is indeed a dead-code state. The frontmatter validator should reject `reasoning_demand: high` when `preferred` is not `opus`, since the only function of `high` in the degradation cascade is to hold at opus in the yellow zone -- which is meaningless if the skill never reaches opus. I support adding this as a validation rule.

**What I maintain:** The skill still needs conditional model behavior -- not every threat model invocation justifies opus cost. The `conditions` block with `downgrade_to` on an opus-preferred skill is the spec-compliant mechanism to achieve this.
