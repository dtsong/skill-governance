# Claude Code Prompt: Generate Eval Cases for `page-component-mapper`

## Objective

Analyze my Next.js App Router project and generate draft eval cases for the `page-component-mapper` skill. You will trace real routes in the codebase, build ground-truth component maps, and output structured eval case files that I can review, correct, and use for skill evaluation.

**Important**: You are generating the *answer key*, not running the skill. Be thorough and precise — I'll be reviewing your output against the actual code, but I need you to do the heavy lifting of tracing imports and annotating components.

---

## Step 1: Survey the Project

Before generating any eval cases, gather project context:

1. Read `package.json` — note the UI libraries, form libraries, state management, and testing frameworks in use
2. Read `tsconfig.json` — note path aliases (especially `@/`, `~/`, or custom paths) so you can resolve imports correctly
3. Read `next.config.ts` (or `.js` / `.mjs`) — note any relevant configuration
4. Read `tailwind.config.ts` (if it exists) — note if Tailwind is in use
5. Scan the `app/` directory structure (2-3 levels deep) to see all available routes
6. Scan the top-level `components/` directory structure to understand the component organization pattern (flat, grouped by feature, ui/shared separation, etc.)
7. Check if there's a `components/ui/` directory with barrel exports (`index.ts`)

Output a brief project summary with:
- Framework version and key libraries
- Path alias mappings
- Component organization pattern
- Styling approach
- Number of routes found

---

## Step 2: Select Routes for Eval Cases

From the routes you found, select **5-7 routes** that provide good coverage. You need:

- **1-2 simple routes** (few components, minimal nesting, mostly server components)
- **2-3 medium routes** (interactive pages with forms, mixed server/client, state management)
- **1-2 complex routes** (nested layouts, dynamic imports, deep component trees, parallel or intercepting routes if present)

For each selected route, explain in one sentence *why* you picked it and what complexity dimension it tests.

**Present your route selections to me before proceeding.** I may want to swap routes or add specific ones I know are problematic.

---

## Step 3: Trace Each Route

For each selected route, perform a complete component trace. Follow this exact procedure:

### 3a. Resolve entry files

Starting from the route path, identify:
- The `page.tsx` file for this route
- Every `layout.tsx` in the route hierarchy (from the route up to the root `app/layout.tsx`)
- Any `loading.tsx`, `error.tsx`, `not-found.tsx`, or `template.tsx` files at this route level
- Any route group or parallel route segments in the path

### 3b. Trace all component imports (recursive)

For each entry file, read the file and extract every component import. Then for each imported component:

1. **Resolve the import path** — follow path aliases, resolve barrel exports (`index.ts`), handle relative paths
2. **Read the component file** and record:
   - Full file path relative to project root
   - First 3 lines — check for `"use client"` directive
   - The props type/interface (look for `interface Props`, `type Props`, inline parameter types, or the component's generic parameter)
   - Every hook call (`useState`, `useEffect`, `useRef`, `useCallback`, `useMemo`, `useContext`, `usePathname`, `useRouter`, `useSearchParams`, `useFormState`, custom hooks)
   - Every context it consumes (`useContext(SomeContext)`) or provides (`<SomeContext.Provider>`)
   - Child components it renders (custom components, not HTML elements or external library primitives)
3. **Recurse** into each child component and repeat
4. **Track dynamic imports** — search for `dynamic(` from `next/dynamic` and `lazy(` from React, trace those import paths too
5. **Stop recursion** at:
   - Leaf components (no custom child components)
   - Third-party library components (from node_modules) — note them but don't trace into them
   - Components you've already traced (avoid circular loops, just note the reference)

### 3c. Build the relationship map

From your trace, construct:
- A parent → children mapping for every component
- Which components come from `page.tsx` vs which come from `layout.tsx` files
- Where server/client boundaries exist (a server component rendering a client component, or vice versa)

### 3d. Identify potential tricky spots

Flag anything that might trip up the mapper skill:
- Barrel exports that re-export from multiple files
- Conditional rendering (components only rendered based on state/props)
- Components imported but potentially not rendered (used in callbacks, passed as props)
- Aliased imports that don't match the component name
- Components spread across multiple files (styles in separate file, types in separate file)
- Higher-order components or render props patterns

---

## Step 4: Generate Eval Case Files

For each route, produce an eval case file using this exact format:

```markdown
# Eval Case: [Descriptive Name]

## Metadata
- **Case ID**: [NN]-[kebab-case-name]
- **Tier**: [1 = simple, 2 = medium, 3 = complex]
- **Route**: [route path]
- **Why this route**: [one sentence on what complexity dimension this tests]
- **Estimated components**: [total count]

## Input

```json
{
  "route": "[route path]"
}
```

## Project Context Relevant to This Route
[2-3 sentences noting anything about the project setup that's relevant
to this specific route — e.g., "this route sits inside a route group
that uses a specialized layout" or "this page uses dynamic imports
for code splitting the settings tabs"]

## Expected Entry Files

| File | Type | Server/Client |
|------|------|---------------|
| `app/.../page.tsx` | Page | server/client |
| `app/.../layout.tsx` | Layout | server/client |
| ... | ... | ... |

## Expected Component Map

| # | Component Name | File Path | Server/Client | Props Type | Key Hooks | Key Context | Children |
|---|---------------|-----------|---------------|------------|-----------|-------------|----------|
| 1 | ComponentName | `path/to/file.tsx` | client | `PropsInterface` | useState, useEffect | UserContext | ChildA, ChildB |
| 2 | ... | ... | ... | ... | ... | ... | ... |

## Expected Relationships

```
page.tsx
├── ComponentA
│   ├── ComponentB
│   │   └── ComponentC (shared/ui)
│   └── ComponentD
└── ComponentE
    └── ComponentF

layout.tsx (app/dashboard/layout.tsx)
├── Sidebar
└── Header
    └── UserMenu

layout.tsx (app/layout.tsx)
├── ThemeProvider (client wrapper)
└── QueryClientProvider (client wrapper)
```

## Server/Client Boundaries
- [List each boundary crossing point and why it matters]

## Tricky Spots
- [List anything the mapper might get wrong, with explanation]

## Grading Rubric

### Must Pass (eval fails if any are wrong)
- [ ] All entry files identified (page.tsx + complete layout chain)
- [ ] [Specific component] found at [specific path]
- [ ] [Specific component] correctly classified as [server/client]
- [ ] [Specific parent-child relationship] captured
- [ ] [List 5-10 critical expectations specific to this route]

### Should Pass (partial credit)
- [ ] Props interface for [component] identified as [type name]
- [ ] [Hook] usage in [component] detected
- [ ] [Context dependency] noted
- [ ] [List 3-5 secondary expectations]

### Bonus
- [ ] [Barrel export resolution, conditional rendering detection, etc.]
- [ ] [List 2-3 nice-to-have expectations]

## Raw Trace Log
[Include the actual import chains you followed so I can verify your work.
Format as:]

`app/.../page.tsx` imports:
  → `@/components/feature/ComponentA` → resolves to `components/feature/component-a.tsx`
  → `@/components/ui/Button` → resolves to `components/ui/button.tsx` (via `components/ui/index.ts`)
  → `./local-helper` → resolves to `app/.../local-helper.tsx`

`components/feature/component-a.tsx` imports:
  → `@/components/ui/Input` → resolves to `components/ui/input.tsx`
  → `../shared/SomeUtil` → resolves to `components/shared/some-util.tsx`
  ...
```

---

## Step 5: Generate the evals.json Index

After generating all individual case files, create an `evals.json` that indexes them:

```json
{
  "skill": "page-component-mapper",
  "project_context": {
    "framework": "Next.js [version]",
    "styling": "[approach]",
    "key_libraries": ["list", "of", "libraries"],
    "path_aliases": { "@/": "src/" },
    "component_organization": "[description of pattern]"
  },
  "cases": [
    {
      "id": "01-case-name",
      "name": "Human-readable description",
      "tier": 1,
      "route": "/route/path",
      "expected_component_count": 8,
      "key_challenges": ["barrel exports", "dynamic import"],
      "file": "cases/01-case-name.md"
    }
  ]
}
```

---

## Step 6: Self-Audit

After generating all cases, do a quick self-audit:

1. **Coverage check**: Do the selected routes collectively exercise these scenarios?
   - [ ] Server components
   - [ ] Client components
   - [ ] Mixed server/client on the same page
   - [ ] Layout-injected components
   - [ ] Shared/UI library components
   - [ ] Barrel exports
   - [ ] Path alias resolution
   - [ ] At least one hook from each category (state, effect, ref, context, router)
   - [ ] Dynamic imports (if present in the project)

2. **Completeness check**: For each case, did you:
   - [ ] Trace every import chain to its leaf?
   - [ ] Check every file for `"use client"`?
   - [ ] Include the raw trace log?
   - [ ] Write specific, checkable grading criteria (not vague)?

3. **Gap report**: List any scenarios that exist in the project but aren't covered by the selected routes. Suggest which additional route would cover each gap.

---

## Output Location

Write all generated files to:

```
.claude/skills/frontend-qa/eval-cases/page-component-mapper/
├── evals.json
├── project-summary.md
├── cases/
│   ├── 01-[name].md
│   ├── 02-[name].md
│   ├── 03-[name].md
│   ├── 04-[name].md
│   ├── 05-[name].md
│   ├── 06-[name].md  (if applicable)
│   └── 07-[name].md  (if applicable)
└── coverage-audit.md
```

---

## Critical Reminders

- **Resolve every import path fully.** Don't guess. Read `tsconfig.json` paths, follow `index.ts` re-exports, handle relative paths. If you can't resolve a path, flag it explicitly.
- **Read every file you trace.** Don't infer what a component does from its name. Open the file, check for `"use client"`, read the hooks, read the JSX.
- **Include the raw trace log.** This is how I verify your work without re-doing the entire trace myself. If I can see the chain you followed, I can spot-check specific links rather than re-tracing from scratch.
- **Be honest about uncertainty.** If a component's behavior is ambiguous (e.g., it's conditionally rendered and you're not sure which branch is typical), say so. An eval case with noted uncertainties is more valuable than one that looks confident but is wrong.
- **Pause after Step 2.** Present your route selections before tracing. This saves significant work if I want different routes.
