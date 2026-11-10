# Guide: Effect Service File Structure

This guide defines the **mandatory file layout and conventions** for any Effect-based service in this repository. Apply it whenever creating a new service under `features/<feature>/services/<service-name>/`, or whenever asked to "create an Effect service."

## Folder Layout

Every service lives in its own folder, colocated under its feature:

```
features/<feature>/services/<service-name>/
├── api.ts       # HttpApi definition (endpoints, groups) — only if the service wraps an HTTP API
├── domain.ts     # Schema.Struct / Schema.Class definitions + derived types
├── errors.ts      # Data.TaggedError classes + a union error type
├── index.ts       # Barrel file — re-exports the public surface only
├── live.ts        # Layer implementation (Layer.scoped / Layer.effect)
├── service.ts      # Context.Tag service interface definition
└── types.ts        # Extra shared types not tied to a schema (optional)
```

Do not merge these responsibilities into fewer files, even for a small service — the split is what keeps services consistent, greppable, and easy to test in isolation. Only omit `api.ts` when the service has no HTTP surface, and only omit `types.ts` when there's nothing to put in it.

## File-by-File Conventions

### `domain.ts` — schemas and derived types

- Every schema is a top-level `export const XSchema = Schema.Struct({...})` (or `Schema.Class` for schemas that also need runtime behavior/identity).
- Optional fields use `Schema.optional(...)` for simple optionality, or `Schema.optionalWith(schema, { exact: true, default: () => ... })` when a default value is needed.
- Derive the TypeScript type from the schema — never hand-write a parallel `interface`:
  ```ts
  export type QueryFeaturesSchema = typeof QueryFeaturesSchema.Type;
  ```
  (Naming: the type and the schema constant share the same name — this is intentional and matches the codebase's existing style. TypeScript resolves the two namespaces separately.)
- Prefer `Schema.Class` over a plain `Schema.Struct` when the shape represents a first-class domain entity with an identity (e.g. `Board`), not just a wire-format payload:
  ```ts
  export class Board extends Schema.Class<Board>("BoardSchema")({
    boardId: Schema.String,
    attributes: Schema.partial(BoardAttributesSchema),
    elements: Schema.optional(Schema.Array(ElementSchema)),
  }) {}
  ```
- URL params, path params, and request payload schemas are defined here too (`XUrlParamsSchema`), even though they're only consumed by `api.ts` — keep all schema definitions centralized in `domain.ts`.

### `errors.ts` — typed error hierarchy

- Every failure mode is a `Data.TaggedError` class, one per distinct failure cause:
  ```ts
  import { Data } from "effect";

  export class ArcGisParseError extends Data.TaggedError("ArcGisParseError")<{
    message: string;
  }> {}

  export class ArcGisCacheError extends Data.TaggedError("ArcGisCacheError")<{
    message: string;
  }> {}
  ```
- Export a union type covering every error the service's public methods can produce:
  ```ts
  export type ArcGisError = ArcGisParseError | ArcGisCacheError;
  ```
- Every public method on the service interface (`service.ts`) must type its `Effect.Effect<A, E>` error channel using this union — never a bare `unknown` or `Error`.
- Prefer `Schema.TaggedErrorClass` instead of `Data.TaggedError` when the error itself needs to be schema-encoded (e.g. crosses an HTTP API boundary) — see the root `effect-ts` SKILL.md error-handling principles.

### `service.ts` — the service interface (`Context.Tag`)

- Define the service as a `Context.Tag` with an inline interface describing only the methods callers need — no implementation details leak here:
  ```ts
  import { Context, Effect } from "effect";

  export class ArcGisService extends Context.Tag("ArcGisService")<
    ArcGisService,
    {
      readonly fetchLegend: (
        serviceId: string,
      ) => Effect.Effect<readonly LegendLayer[], ArcGisError>;
      // ...one method per capability, fully typed error channel
    }
  >() {}
  ```
- Every method returns `Effect.Effect<Success, Error>` — never a bare `Promise` or a thrown exception.
- Do not export trivial one-line wrapper methods that just forward to a single call — only expose genuinely useful capabilities (matches the root skill's dependency-injection principle).

### `live.ts` — the implementation `Layer`

- Implemented as `Layer.scoped(ServiceTag, Effect.gen(function* () { ... }))` whenever the service manages a resource needing cleanup (caches, subscriptions, object URLs); use `Layer.effect` only when there is nothing to release.
- Acquire/release resources explicitly with `Effect.acquireRelease` inside the layer body, not with ad hoc `useEffect`-style cleanup:
  ```ts
  yield* Effect.acquireRelease(Effect.void, () =>
    Effect.gen(function* () {
      const cache = yield* Ref.get(imageCache);
      cache.forEach((url) => URL.revokeObjectURL(url));
    }),
  );
  ```
- Local mutable state (caches, counters) goes through `Ref`, never a closed-over `let`.
- If the service wraps an external system (pub/sub, native browser events), bridge into Effect's world with `Queue`/`PubSub`/`Stream`, and fork long-running loops with `Effect.forkScoped` rather than blocking the layer's construction:
  ```ts
  yield* Effect.forkScoped(
    pipe(processEvents(inputQueue, hub), Effect.annotateLogs("target", "BUS")),
  );
  ```
- If the service calls an HTTP API defined in `api.ts`, derive the client once at layer construction with `HttpApiClient.make(TheApi, { baseUrl })`, and centralize error normalization in one local helper reused by every method:
  ```ts
  const catchApiErrors = Effect.catchAll((e: unknown) =>
    Effect.fail(new ArcGisParseError({ message: String(e) })),
  );
  // ...
  fetchLegend: (serviceId) =>
    Effect.gen(function* () {
      const data = yield* client.MapServer.legend({ path: { serviceId }, urlParams: { f: "json" } });
      return data.layers;
    }).pipe(catchApiErrors),
  ```
- Tag the layer with a span for observability: `.pipe(Layer.withSpan("XLive.Initialize"))`.
- Return the object literal matching the `service.ts` interface exactly — one method per capability, implemented with `Effect.gen` (or `Effect.fn` per the root skill's preference for reusable business-logic functions).

### `api.ts` — HTTP API definition (only if applicable)

- Follows `@effect/platform`'s `HttpApi` / `HttpApiGroup` / `HttpApiEndpoint` pattern exactly as documented in `guide-http-platform.md`.
- Path/URL params and success schemas always reference the schemas exported from `domain.ts` — never redefine a schema inline in `api.ts`.
  ```ts
  export class ArcGisApi extends HttpApi.make("ArcGisApi").add(
    HttpApiGroup.make("MapServer").add(
      HttpApiEndpoint.get("legend", "/:serviceId/MapServer/legend")
        .setPath(Schema.Struct({ serviceId: Schema.String }))
        .setUrlParams(LegendUrlParamsSchema)
        .addSuccess(LegendResponseSchema),
    ),
  ) {}
  ```
- Binary/non-JSON responses use `HttpApiSchema.withEncoding` with the correct `kind`/`contentType` (e.g. `Uint8ArrayFromSelf` + `image/png` for exported map tiles) — never assume JSON encoding for every endpoint.

### `index.ts` — barrel export

- Re-export only the public surface, nothing internal:
  ```ts
  export * from "./service";
  export * from "./error"; // note: match actual filename, e.g. "./errors" if pluralized
  ```
- Do not re-export `live.ts` from the barrel if the convention in this codebase is to provide layers explicitly at the composition root — check existing sibling services before deciding; be consistent with what's already there.
- Do not re-export `domain.ts`/`api.ts` wholesale unless consumers outside the service genuinely need those schemas directly.

### `types.ts` — non-schema shared types (optional)

- Only for types that aren't derived from a `Schema` (e.g. plain type aliases like `type Url = string` used internally for readability). If a type can be schema-derived, it belongs in `domain.ts` instead.

## New Service Checklist

When asked to create a new Effect service, do the following in order:
1. Create the folder `features/<feature>/services/<service-name>/`.
2. Write `domain.ts` first — every schema the service will consume or produce, with `export type X = typeof X.Type` for each.
3. Write `errors.ts` — one `Data.TaggedError` per failure mode, plus the union type.
4. Write `api.ts` if the service wraps an HTTP API, referencing `domain.ts` schemas only.
5. Write `service.ts` — the `Context.Tag` interface, every method's error channel typed with the `errors.ts` union.
6. Write `live.ts` — the `Layer.scoped`/`Layer.effect` implementation, with resource cleanup, caching via `Ref`, and a `Layer.withSpan` name.
7. Write `index.ts` — barrel exporting only the public surface.
8. Only add `types.ts` if something genuinely doesn't belong in `domain.ts`.

Cross-check every new file against the root `effect-ts` SKILL.md TypeScript preferences (no `any`, no `as`, no `namespace`) before considering the service done.
