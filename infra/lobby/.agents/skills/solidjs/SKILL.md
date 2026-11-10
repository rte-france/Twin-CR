---
name: solidjs-expert
description: Expert SolidJS development guide enforcing fine-grained reactivity, correct primitive usage (signals, effects, memos, stores, resources), strict anti-patterns, and defensive/data-driven coding practices. Use this skill whenever writing, reviewing, or refactoring any .tsx/.jsx/.ts file in a SolidJS project, whenever the user mentions SolidJS, createSignal, createStore, createResource, or asks for components/UI in this codebase, and whenever code needs to handle async data, forms, or lists. Forbids React mental models (useState/useEffect-style thinking, key-by-index lists, prop destructuring) and forbids unguarded access to async or external data.
---

# SolidJS Expert Guidelines

This project uses **SolidJS**. All code must follow fine-grained reactivity principles and defensive, data-driven patterns. Never apply React mental models — Solid's execution model is fundamentally different (components run once; reactivity lives in signals/effects, not re-renders).

## 1. Core Principles

- **Components run once.** The component function body executes only at creation time. Anything reading a signal must be inside a tracking scope (JSX expression, `createEffect`, `createMemo`) — not a plain `const` computed in the component body from a signal read once.
- **No Virtual DOM.** Solid compiles JSX to real DOM operations. Don't write code assuming re-renders (e.g. relying on a whole subtree remounting to "reset" state).
- **Signals are functions.** Always call them: `count()`. Passing the reference (`count`) instead of invoking it is the single most common bug.
- **Reactivity is opt-in via tracking scopes.** A signal read outside JSX, `createEffect`, or `createMemo` is a plain, one-time snapshot — it will not update.

## 2. Reactivity Primitives

```ts
const [count, setCount] = createSignal(0);
console.log(count());        // read (tracked if inside a scope)
setCount(1);                 // write
setCount(prev => prev + 1);  // functional update — REQUIRED when new value depends on old value
```

- **`createEffect`**: side effects that depend on signals. Runs after the initial render and on every dependency change. Never mutate unrelated state inside an effect without a clear reason — prefer `createMemo` for derived values.
- **`createMemo`**: for derived values, especially expensive ones or ones read in multiple places. Memoized values are also signals — call them: `doubled()`.
- **`createStore`**: for nested objects/arrays needing fine-grained updates.
  ```ts
  import { createStore, produce } from "solid-js/store";
  const [state, setState] = createStore({ user: { name: "John" } });
  setState("user", "name", "Jane");         // path-based setter (preferred)
  setState(produce(s => { s.user.name = "Jane"; })); // for batched mutations
  ```
- **`createResource`**: the canonical primitive for async/data-driven work (fetches, API calls). Never hand-roll `createSignal` + manual `fetch().then(setSignal)` for async data — `createResource` gives you loading/error state and cancellation handling for free.
  ```ts
  const [data, { refetch, mutate }] = createResource(sourceSignal, fetcher);
  ```

## 3. Control Flow Components

Always use Solid's built-ins instead of plain JS array methods or ternaries in JSX — they preserve fine-grained reactivity instead of tearing down/rebuilding DOM.

| Component | Use for |
|---|---|
| `<Show when={...} fallback={...}>` | Conditional rendering |
| `<For each={list()}>` | Reference-keyed lists (objects, records with identity) — `item` is a value, `index` is a signal |
| `<Index each={list()}>` | Index-keyed lists (primitives, form inputs bound by position) — `item` is a signal, `index` is a value |
| `<Switch>` / `<Match>` | Multi-branch conditionals (replaces if/else-if chains) |
| `<Suspense fallback={...}>` | Wraps async boundaries (used with `createResource`/lazy components) |
| `<ErrorBoundary fallback={...}>` | Catches render/render-triggered errors — **mandatory** around any subtree that reads `createResource` data or does untrusted rendering |

## 4. Props Handling

- **Never destructure props.** Destructuring reads the value once at call time and breaks reactivity.
  - ❌ `const { name } = props;`
  - ✅ `props.name` (read fresh, every time, inside a tracking scope)
- Use `splitProps(props, ["a", "b"])` to divide props while preserving reactivity, and `mergeProps(defaults, props)` to apply defaults — never `{ ...defaults, ...props }` spread, which also breaks reactivity.
- Treat all props as **untrusted external data**: validate/guard before use (see Section 6).

## 5. Lifecycle & Refs

- `onMount`: runs once after the initial render — use for DOM measurements, subscriptions, third-party library init.
- `onCleanup`: always pair with anything that needs teardown (listeners, timers, subscriptions, `AbortController`s). Every `onMount`/`createEffect` that opens a resource should have a matching `onCleanup` that closes it.
- Refs: `let inputRef: HTMLInputElement | undefined; <input ref={inputRef} />`. Guard usage — `inputRef` is `undefined` until after mount, so never access it synchronously in the component body; use it inside `onMount` or event handlers.

## 6. Defensive, Data-Driven Coding (project standard)

This project treats **all external data as untrusted**: API responses, route params, localStorage, `props`, form input. Code must not assume shape or presence.

- **Never trust `createResource` data blindly.** Always branch on `resource.loading`, `resource.error`, and a null/undefined resource value before touching `resource()` fields:
  ```tsx
  <Suspense fallback={<Spinner />}>
    <ErrorBoundary fallback={(err) => <ErrorMessage error={err} />}>
      <Show when={data()} fallback={<EmptyState />}>
        {(d) => <UserCard user={d()} />}
      </Show>
    </ErrorBoundary>
  </Suspense>
  ```
  Note the callback form of `<Show>` (`{(d) => ...}`) — it gives a **narrowed, non-null** accessor instead of re-checking `data()!` everywhere.
- **Validate/parse at the boundary, not deep in the tree.** Parse API responses with a schema validator (e.g. `zod`) at the fetcher used by `createResource`, so components downstream can trust the shape. Don't scatter `?.` chains through every consumer as a substitute for real validation.
- **Guard array/list data before `<For>`/`<Index>`.** Default to `[]`, never assume the source is an array: `<For each={items() ?? []}>`.
- **Fail loud in dev, fail safe in prod.** Prefer explicit fallback UI (`<Show>`/`<ErrorBoundary>`) over silent `undefined` renders. Log unexpected shapes; don't let a malformed field crash the whole tree — scope `<ErrorBoundary>` around the smallest reasonable subtree, not just the app root.
- **Functional updates for derived writes.** Any `setSignal`/`setState` call whose new value depends on the old value must use the callback form (`setCount(c => c + 1)`, `setState("items", items => [...items, next])`), never a stale outer read — this avoids races when updates are batched.
- **Abort/cleanup async work.** For manual async work outside `createResource` (rare — prefer `createResource`), use `AbortController` and clean it up in `onCleanup` so in-flight requests don't write to disposed signals.
- **Never mutate store data outside a setter.** `state.items.push(x)` bypasses reactivity and hides bugs — always go through `setState`/`produce`.
- **Type everything.** No `any` on props, resource fetchers, or store shapes. Define an interface/type for props and for each store shape; let the compiler catch shape drift before runtime does.

## 7. Anti-Patterns to Strictly Avoid

1. Destructuring props (breaks fine-grained reactivity).
2. Reading a signal outside a tracking scope, expecting it to stay live.
3. Forgetting to call a signal getter — passing `count` instead of `count()`.
4. Side effects during render — always wrap in `createEffect` or `onMount`, never call them inline in the component body.
5. Using `<For>` for index-keyed primitive/input lists, or `<Index>` for reference-keyed object lists — pick the one matching the data's identity semantics.
6. Hand-rolled async state (`createSignal` + `fetch().then(setX)`) instead of `createResource` — loses loading/error/cancellation handling.
7. Rendering `resource()` data without checking `loading`/`error`/nullish first, or without a `<Suspense>`/`<ErrorBoundary>` wrapper.
8. Mutating store objects/arrays directly instead of through the store's setter.
9. Non-functional updates (`setCount(count() + 1)`) where the new value depends on the old — race-prone under batching.
10. Treating props, route params, or API payloads as trusted without validation or guards.
