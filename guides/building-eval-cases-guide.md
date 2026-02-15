# Building Eval Cases for `page-component-mapper`

## What an Eval Case Actually Is

An eval case is just three things:

1. **An input** — what you give the skill (a route path like `/dashboard/settings`)
2. **Expectations** — what the skill should find (specific files, components, relationships)
3. **Grading criteria** — how you decide if the output was good enough

That's it. You don't need a framework to start. You need a few real routes from your project and the patience to manually verify what the mapper *should* find for each one.

---

## How to Pick Your First Eval Routes

You want 5-7 routes that cover different levels of complexity. Walk through your `app/` directory and pick one route from each of these categories:

### Tier 1: Simple Page (1-2 eval cases)
A page with minimal component nesting. Maybe a static or mostly-static page.
- Few imported components (3-8)
- No complex layouts wrapping it
- Straightforward server or client components (not a mix)
- **Why it matters**: Baseline sanity check. If the mapper can't handle this, nothing else will work.

### Tier 2: Standard Interactive Page (2-3 eval cases)
A typical feature page with forms, state, and a mix of server/client components.
- 8-20 imported components
- Mix of `"use client"` and server components
- Uses hooks, context providers, maybe a form library
- Has shared/reusable components from a `components/ui` or similar directory
- **Why it matters**: This is the bread-and-butter case. Most of your actual QA work will target pages like this.

### Tier 3: Complex Page (1-2 eval cases)
A page with nested layouts, parallel routes, heavy component composition, or dynamic imports.
- Deep component trees (components importing components importing components)
- Barrel exports (`index.ts` files re-exporting multiple components)
- Dynamic imports (`next/dynamic` or `React.lazy`)
- Layout nesting (multiple `layout.tsx` files in the route hierarchy)
- **Why it matters**: Stress test. Reveals whether the mapper handles real-world complexity or falls apart.

---

## Building a Case: Step-by-Step

Here's the process for a single eval case. Do this manually for your first few — the point is to create a ground truth that you *know* is correct.

### Step 1: Pick the route

Choose a route from your project. For this walkthrough, imagine you picked `/dashboard/settings`.

### Step 2: Trace the component tree yourself

Open your editor and manually trace the imports:

1. Find the entry file: `app/dashboard/settings/page.tsx`
2. Check for layouts: `app/dashboard/settings/layout.tsx`, `app/dashboard/layout.tsx`, `app/layout.tsx`
3. Open `page.tsx`, list every component it imports
4. For each imported component, open that file and list what *it* imports
5. Keep going until you hit leaf components (components that don't import other custom components)

Write this down. This is your ground truth.

### Step 3: Annotate each component

For each component you found, note:
- Its file path
- Server or client component (`"use client"` present or not)
- Its props type/interface name
- Key hooks it uses
- Whether it's project-specific or from a shared/ui library
- Its direct child components (custom ones, not HTML elements)

### Step 4: Write the expectations

Turn your annotations into checkable expectations. Be specific.

### Step 5: Define what "good enough" looks like

Not every detail matters equally. Prioritize:
- **Must get right**: File paths, server/client classification, direct parent-child relationships
- **Should get right**: Props interfaces, hooks used, context dependencies
- **Nice to have**: Transitive dependencies, detailed type information

---

## Eval Case Template

Use this structure for each case. Create these as individual files.

```
eval-cases/
├── evals.json              # Index of all eval cases
├── cases/
│   ├── 01-simple-page.md
│   ├── 02-settings-page.md
│   ├── 03-form-heavy-page.md
│   ├── 04-nested-layout-page.md
│   └── 05-dynamic-imports-page.md
```

### evals.json

```json
{
  "skill": "page-component-mapper",
  "cases": [
    {
      "id": "01-simple-page",
      "name": "Simple static page with minimal components",
      "tier": 1,
      "input": {
        "route": "/about"
      },
      "file": "cases/01-simple-page.md"
    },
    {
      "id": "02-settings-page",
      "name": "Interactive settings page with forms and mixed server/client components",
      "tier": 2,
      "input": {
        "route": "/dashboard/settings"
      },
      "file": "cases/02-settings-page.md"
    }
  ]
}
```

### Individual Case File (example: `cases/02-settings-page.md`)

```markdown
# Eval Case: Settings Page

## Input
Route: `/dashboard/settings`

## Context
This page has a tabbed settings interface with profile, notification,
and billing sections. It sits inside the dashboard layout which provides
a sidebar and header. The profile tab includes an avatar upload component
that uses client-side state. The billing section uses server components
for fetching plan data.

## Expected Component Map

### Entry Files
- `app/dashboard/settings/page.tsx` (server component)
- `app/dashboard/settings/layout.tsx` (server component) [if exists]
- `app/dashboard/layout.tsx` (client component — wraps with sidebar)
- `app/layout.tsx` (server component — root layout)

### Components the Mapper Must Find

| Component | File Path | Server/Client | Key Detail |
|-----------|-----------|---------------|------------|
| DashboardSidebar | `components/dashboard/sidebar.tsx` | client | Uses usePathname() for active link |
| DashboardHeader | `components/dashboard/header.tsx` | client | Consumes UserContext |
| SettingsTabs | `components/settings/settings-tabs.tsx` | client | Uses useState for active tab |
| ProfileForm | `components/settings/profile-form.tsx` | client | Uses react-hook-form + zod |
| AvatarUpload | `components/settings/avatar-upload.tsx` | client | Uses useState for preview, useRef for file input |
| NotificationPreferences | `components/settings/notification-prefs.tsx` | client | Uses useMutation from TanStack Query |
| BillingOverview | `components/settings/billing-overview.tsx` | server | Fetches plan data via async function |
| PlanCard | `components/ui/plan-card.tsx` | server | Shared UI component |
| Button | `components/ui/button.tsx` | client | From shadcn/ui |
| Input | `components/ui/input.tsx` | client | From shadcn/ui |
| Tabs, TabsList, TabsTrigger, TabsContent | `components/ui/tabs.tsx` | client | From shadcn/ui (Radix) |

### Relationships the Mapper Must Capture
- `page.tsx` → renders SettingsTabs, BillingOverview
- `SettingsTabs` → renders ProfileForm, NotificationPreferences (conditionally by tab)
- `ProfileForm` → renders AvatarUpload, Input, Button
- `BillingOverview` → renders PlanCard
- `DashboardSidebar` and `DashboardHeader` come from `app/dashboard/layout.tsx`, not from `page.tsx`

### Server/Client Boundaries
- The mapper must identify that `BillingOverview` is a server component rendered
  inside a page that also renders client components — this is a valid pattern
  but the boundary matters for debugging
- `DashboardSidebar` is client because it uses `usePathname`, even though the
  dashboard layout itself could be server — the mapper must trace this correctly

### Context / Provider Dependencies
- `DashboardHeader` consumes `UserContext` (provided in root layout or a parent layout)
- `NotificationPreferences` uses TanStack Query (QueryClientProvider must be in a parent)

## Grading Rubric

### Must Pass (fail the eval if any of these are wrong)
- [ ] All entry files correctly identified (page.tsx + all layout.tsx in the route hierarchy)
- [ ] Every component in the "Must Find" table is present with correct file path
- [ ] Server/client classification is correct for every component
- [ ] Parent-child relationships match the "Relationships" section

### Should Pass (deductions but not a failure)
- [ ] Props interfaces identified for form components (ProfileForm, AvatarUpload)
- [ ] Hooks correctly listed for client components
- [ ] Shared/UI components flagged as reusable
- [ ] Context dependencies noted

### Bonus (nice to have)
- [ ] Barrel export chains resolved (if components/ui uses index.ts)
- [ ] Conditional rendering noted (SettingsTabs renders children based on state)
- [ ] External library attribution (shadcn/ui, Radix, react-hook-form)
```

---

## How to Actually Build These From Your Project

Here's the practical workflow. Do this in your editor, not with Claude Code — you want
human-verified ground truth.

### Round 1: Build 3 cases (about 30-60 min)

1. Open your `app/` directory. Pick one simple route, one medium route, one complex route.

2. For each route, open `page.tsx` in your editor. Trace every import. Open each
   imported file. Trace its imports. Build the tree on paper or in a scratch file.
   This is tedious but it only needs to happen once per eval case, and it's the
   only way to get a reliable ground truth.

3. For each component, check:
   - Does the file start with `"use client"`? → client component
   - No directive? → server component (in App Router, this is the default)
   - What's the props type? (look for `interface Props`, `type Props`, or inline types)
   - What hooks does it call? (search for `use` at the start of function calls)

4. Write it up using the template above. Don't worry about being exhaustive on the
   first pass — get the structure right, then fill in details.

### Round 2: Run the skill and compare (15-30 min per case)

1. Invoke the page-component-mapper skill against each of your eval routes
2. Compare its output against your ground truth, component by component
3. Mark each grading criterion as pass/fail
4. Note WHERE it went wrong — missing a component entirely is different from
   getting the server/client classification wrong

### Round 3: Categorize failures and update the skill

Common failure patterns you'll likely see:

| Failure | What it means | How to fix the skill |
|---------|---------------|----------------------|
| Missed components from layout.tsx | Skill didn't walk up the layout hierarchy | Add explicit step: "resolve all layout.tsx files from the route to the root" |
| Wrong server/client classification | Didn't check for `"use client"` or inferred incorrectly | Add step: "read the first 5 lines of each file, check for use client directive" |
| Missed barrel export components | Stopped at the `index.ts` instead of following re-exports | Add step: "if import resolves to index.ts, follow each named export to its source file" |
| Missed dynamic imports | Only followed static `import` statements | Add step: "search for next/dynamic and React.lazy calls, trace their import paths" |
| Missed aliased imports | Didn't resolve `@/components/...` to actual paths | Add step: "read tsconfig.json paths, resolve aliases before tracing" |
| Confused shared vs project components | No clear heuristic for what's "shared" | Add step: "components under /ui, /shared, or /common directories are shared" |

Update the SKILL.md procedure to address the specific failures you observe.
Then re-run the evals and confirm the fixes work without regressing the passing cases.

---

## When You're Ready to Expand

After your first 3 cases are solid and the skill handles them well:

- Add 2-3 more cases targeting patterns the first round didn't cover
  (parallel routes, route groups, intercepting routes, pages with suspense boundaries)
- Add an adversarial case: a page where the component structure is intentionally
  confusing (deep nesting, many re-exports, mixed dynamic and static imports)
- Consider adding a performance expectation: "the mapper should not read more than
  N files to map this page" — this keeps token usage in check

The goal isn't to build 50 eval cases. 5-7 well-constructed cases with clear
expectations will catch the vast majority of issues and give you confidence
that the skill works reliably across your project's actual patterns.
