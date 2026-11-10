---
name: bulletproof-solid
description: Enforces a Bulletproof-React-style architecture adapted for SolidJS — feature-based folder structure, TypeScript strict typing, Solid Query (or createResource) for server state, solid-js/store for client state, schema-validated forms, MSW-backed testing, and defensive/data-driven coding at every API and reactivity boundary. Use this skill whenever creating, reviewing, or refactoring any file under src/ in this SolidJS project (components, features, stores, api), whenever the user asks for a new feature, component, form, or data-fetching hook, and whenever code touches authentication, authorization, or user-submitted data. Forbids cross-feature imports, React mental models, and unguarded async/resource access.
---

# Bulletproof Solid Guidelines

This project applies the **Bulletproof React** architecture philosophy (feature-based structure, strict typing, defensive API layer, rigorous testing) to **SolidJS**. Do not import React patterns — Solid's reactivity model is fundamentally different (components run once; reactivity is fine-grained via signals, not re-renders). Every rule below assumes Solid primitives.

## 1. Project Structure (non-negotiable)

```
src/
├── app/          # routes, providers, router setup
├── components/   # shared UI components
├── config/       # global config, env vars
├── features/     # feature-based modules
├── hooks/        # shared "primitives" (Solid calls custom hooks "primitives", e.g. useX)
├── lib/          # preconfigured libraries (solid-query client, auth, api client)
├── testing/      # test utilities, mocks
├── types/        # shared TS types
└── utils/        # shared utility functions
```

Each feature is self-contained:
```
src/features/<feature>/
├── api/          # fetchers + Solid Query hooks (or createResource wrappers) for this feature
├── components/   # feature-specific components
├── hooks/        # feature-specific primitives
├── stores/       # feature-specific state (solid-js/store)
├── types/        # feature-specific types
└── utils/        # feature-specific utilities
```

**Architecture rules — enforce on every file you touch:**
- **No cross-feature imports.** `features/discussions` never imports from `features/comments` directly. Shared logic goes up to `src/components`, `src/hooks`, `src/lib`, or `src/utils`.
- **Unidirectional flow**: `shared → features → app`. A shared module never imports from a feature or `app/`.
- **Colocation**: keep code close to where it's used; only promote to `shared` once genuinely reused across features.

## 2. TypeScript & Style

- **Strict mode always on** — never weaken `tsconfig` to silence an error; fix the type.
- **Type-first**: define the type/Zod schema before writing implementation logic.
- **Absolute imports** via `@/` — no `../../../` chains crossing feature boundaries.
- **Naming**: `kebab-case.tsx` for files/folders, `PascalCase` for components, `camelCase` for functions/variables, primitives prefixed `use-` (`use-discussions.ts`).
- No `any` — anything unknown at a boundary (API response, `JSON.parse`, route params) must be validated with Zod, not cast.

## 3. Core SolidJS Reactivity Rules (mandatory foundation)

- **Components run once.** The function body executes at creation only — reactive reads must live inside JSX, `createEffect`, or `createMemo`.
- **Signals are functions.** Always call them: `count()`, never pass the bare reference.
- **Never destructure props.** `const { name } = props` breaks reactivity — use `props.name`, or `splitProps`/`mergeProps` for slicing/defaults.
- **Functional updates** whenever the new value depends on the old: `setCount(c => c + 1)`, `setState("items", items => [...items, next])`.
- **Never mutate a store directly** (`state.items.push(x)`) — always go through the setter or `produce`.
- Use `<Show>`/`<Switch>` for conditionals, `<For>` (reference-keyed) or `<Index>` (index-keyed) for lists — never a bare JS ternary/`.map()` in JSX, which discards fine-grained reactivity.
- Always `onCleanup` anything opened in `onMount`/`createEffect` (listeners, timers, subscriptions, `AbortController`s).

## 4. State Management — pick the right layer

| State kind | Tool | Notes |
|---|---|---|
| Simple local state | `createSignal` | Independent, single-component |
| Complex local state | `createStore` (local) | Multiple related sub-fields |
| Global client state (modals, theme, notifications) | `createStore` in `src/lib/stores` or a dedicated feature `stores/` file | Keep minimal — don't globalize state used by only one feature |
| Server state (anything from an API) | **Solid Query** (`@tanstack/solid-query`) or `createResource` | Never store server data in a plain `createSignal` set from a manual `fetch().then()` |
| Form state | Signals/store + Zod resolver, or `@modular-forms/solid` | Validate with the same schema client- and server-side |

**Default to the narrowest scope.** Local signal → lift to a shared store only if genuinely cross-component/feature. Server data never bypasses Solid Query/`createResource`.

## 5. API Layer (defensive by construction)

Every endpoint gets three pieces, colocated in `features/<feature>/api/`:
1. **Types & Zod schema** for request and response.
2. **Fetcher function** using the configured API client (`src/lib/api-client`) — never a raw inline `fetch` in a component.
3. **A Solid Query hook (preferred for caching/invalidation) or a `createResource` wrapper.**

```typescript
// features/discussions/api/get-discussions.ts
import { z } from "zod";
import { api } from "@/lib/api-client";
import { createQuery } from "@tanstack/solid-query";

const DiscussionSchema = z.object({
  id: z.string(),
  title: z.string(),
  teamId: z.string(),
});
const DiscussionsResponseSchema = z.array(DiscussionSchema);
export type Discussion = z.infer<typeof DiscussionSchema>;

export const getDiscussions = async (
  params: GetDiscussionsParams
): Promise<Discussion[]> => {
  const res = await api.get("/discussions", { params });
  return DiscussionsResponseSchema.parse(res.data); // validate at the boundary
};

export const useDiscussions = (params: () => GetDiscussionsParams) =>
  createQuery(() => ({
    queryKey: ["discussions", params()],
    queryFn: () => getDiscussions(params()),
  }));
```

If Solid Query isn't in the project, fall back to `createResource` — same validation discipline applies:

```typescript
// features/discussions/api/use-discussion.ts
import { createResource } from "solid-js";

export function useDiscussion(id: () => string) {
  return createResource(id, async (discussionId) => {
    const res = await api.get(`/discussions/${discussionId}`);
    return DiscussionSchema.parse(res.data);
  });
}
```

**Rules:**
- Validate every response with Zod inside the fetcher — components downstream trust the shape, they don't re-guard with speculative `?.` chains.
- Query keys are structured arrays (`["discussions", params]`), never bare strings.
- Never inline a fetch call with an ad hoc `createResource` in a component for anything reused more than once — wrap it in a named primitive in `api/`.

## 6. Defensive, Data-Driven Rendering (mandatory)

- **Every component consuming async/server data must handle loading, error, and empty states explicitly**, wrapped correctly:
  ```tsx
  <Suspense fallback={<Spinner />}>
    <ErrorBoundary fallback={(err) => <ErrorMessage error={err} />}>
      <Show when={data()} fallback={<EmptyState />}>
        {(d) => <DiscussionList discussions={d()} />}
      </Show>
    </ErrorBoundary>
  </Suspense>
  ```
  The callback form of `<Show>` gives a narrowed, non-null accessor — prefer it over repeated `data()!`.
- **`<ErrorBoundary>` at the feature level**, not just the app root — a broken discussion thread shouldn't blank the whole page. Pair with an error tracker (Sentry or equivalent) in production.
- **Sanitize all user-submitted content before rendering** — DOMPurify for HTML, never `innerHTML="{unsanitized}"` on untrusted input.
- **List rendering**: guard the source (`<For each={items() ?? []}>`), and use `<Index>` instead of `<For>` for primitive/positional data (e.g. form inputs) rather than keying by array index manually.
- **Forms**: validate with the same Zod schema on submit client-side, and always expect server-side re-validation too — client checks are UX only, never the security boundary.

## 7. Auth & Authorization

- JWTs in **HttpOnly cookies** preferred over `localStorage`; if `localStorage` is used, treat it as XSS-exposed and minimize what's stored there.
- Client-side role checks (RBAC/PBAC) are for **UX only** (hiding buttons, disabling actions) — every permission must be re-validated server-side. Never treat a client-side check as a security control.
- Handle 401s via a single API client interceptor with automatic token refresh — don't scatter manual refresh logic per feature.

## 8. Testing

- **Integration tests are the primary layer** (feature workflows), using Vitest + `@solidjs/testing-library`.
- Use **MSW** to mock at the network boundary with real HTTP semantics — never mock `fetch` directly.
- **Test behavior and outcomes**, not implementation details (avoid asserting on internal signal calls).
- E2E (Playwright) reserved for critical user journeys (auth, core workflows), not exhaustive coverage.

## 9. New File Checklist (apply on every file you create)

**New component:**
1. `kebab-case.tsx` filename, `PascalCase` component name, typed `Props` interface (no `any`), never destructured.
2. `<Show>`/`<Switch>`/`<For>`/`<Index>` for all conditionals/lists, with `?? []` guards on list sources.
3. If it renders resource/query data: `<Suspense>` + `<ErrorBoundary>` + `<Show>` narrowing (Section 6) — no exceptions.
4. `onCleanup` for anything opened in `onMount`/`createEffect`.
5. Sanitize any HTML/user content before render.

**New API primitive:**
1. Zod schema for the response, parsed inside the fetcher.
2. Fetcher separated from the query/resource hook.
3. Structured query key if using Solid Query.

**New store file:**
1. Confirm the state is genuinely cross-feature/global before promoting it out of a component — otherwise keep it a local signal.
2. Typed state shape, no `any`.
3. All mutations through the setter/`produce`, never direct property assignment.
4. Export the store + setter, never a mutable raw reference alone.

**New form:**
1. Zod schema shared between client validation and (ideally) the API request type.
2. Client validation is UX-only — assume and handle server-side validation errors too.
3. Disable/guard the submit action while a mutation is in flight; show explicit error state on failure.

## 10. Anti-Patterns to Strictly Avoid

1. Cross-feature imports (`features/a` importing from `features/b`).
2. React mental models: expecting re-renders, using array index as a stable `<For>` key, computing derived values once in the component body instead of `createMemo`.
3. Destructuring props, or spreading `{ ...defaults, ...props }` instead of `mergeProps`.
4. Storing server data in a plain `createSignal` fed by a manual `fetch().then()` instead of Solid Query/`createResource`.
5. Rendering resource/query data without checking loading/error/empty first, or without `<Suspense>`/`<ErrorBoundary>`.
6. Trusting an unvalidated API response shape (no Zod parse at the fetcher boundary).
7. Mutating a store directly instead of through its setter/`produce`.
8. Non-functional updates (`setCount(count() + 1)`) where the new value depends on the old — race-prone under batching.
9. `any` types on props, API responses, or store state.
10. Relying on client-side role checks as the actual authorization boundary.
11. `innerHTML`/unsanitized rendering of user-submitted content.
12. Mocking `fetch` directly in tests instead of using MSW at the network layer.
13. Bare string query keys instead of structured arrays.
