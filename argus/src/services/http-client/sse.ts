/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Data, Effect, Option, Stream } from "effect";

export class BackendRequestError extends Data.TaggedError(
  "BackendRequestError",
)<{
  readonly url: string;
  readonly cause: unknown;
}> {}

/**
 * The `data` of each event of `stream`, a W3C server-sent events body.
 * Multi-line data is joined with "\n"; events without data, comments and
 * other fields (id, event, retry) are skipped.
 */
export const sseData = <E>(
  stream: Stream.Stream<Uint8Array, E>,
): Stream.Stream<string, E> =>
  stream.pipe(
    Stream.decodeText(),
    Stream.splitLines,
    Stream.mapAccum([] as string[], (data, line): [string[], Option.Option<string>] => {
      if (line === "") {
        return [[], data.length > 0 ? Option.some(data.join("\n")) : Option.none()];
      }
      if (line === "data" || line.startsWith("data:")) {
        return [[...data, line.slice(5).replace(/^ /, "")], Option.none()];
      }
      return [data, Option.none()];
    }),
    Stream.filterMap((data) => data),
  );

/**
 * The events of the server-sent events endpoint `url`, each parsed as JSON.
 *
 * Goes through `window.fetch`, hence the Argus HTTP client: the Rust side
 * reconnects (with Last-Event-ID) on network errors, so this stream only
 * fails or ends when the server rejects the request or the stream is cancelled.
 * Interrupting the stream aborts the request.
 */
export const sseJsonStream = <T>(url: string): Stream.Stream<T, BackendRequestError> =>
  Stream.unwrapScoped(
    Effect.gen(function* () {
      const controller = new AbortController();
      yield* Effect.addFinalizer(() => Effect.sync(() => controller.abort()));

      const response = yield* Effect.tryPromise({
        try: () =>
          fetch(url, {
            headers: { Accept: "text/event-stream" },
            signal: controller.signal,
          }),
        catch: (cause) => new BackendRequestError({ url, cause }),
      });
      const body = response.body;
      if (!response.ok || !body) {
        return yield* Effect.fail(
          new BackendRequestError({ url, cause: `HTTP status ${response.status}` }),
        );
      }

      return sseData(
        Stream.fromReadableStream({
          evaluate: () => body,
          onError: (cause) => new BackendRequestError({ url, cause }),
        }),
      ).pipe(
        Stream.mapEffect((data) =>
          Effect.try({
            try: () => JSON.parse(data) as T,
            catch: (cause) => new BackendRequestError({ url, cause }),
          }),
        ),
      );
    }),
  );

/** A backend reached through the Argus HTTP client, with the API of `GmClient` and `ScadaClient`. */
export interface BackendClient {
  /** GET `endpoint` (e.g. "/history/topic?min=0&max=10") and parse the body as JSON. */
  readonly get: <T = any>(
    endpoint: string,
  ) => Effect.Effect<T, BackendRequestError>;
  /** The events of the server-sent events `endpoint` (e.g. "/time"), each parsed as JSON. */
  readonly sseStream: <T = any>(
    endpoint: string,
  ) => Stream.Stream<T, BackendRequestError>;
}

/**
 * The backend at `baseUrl`, with the same API as `GmClient` and `ScadaClient`
 * (endpoints relative to the backend) but through the Argus HTTP client
 * (window.fetch). `baseUrl` is evaluated on each request, so a backend
 * configured or moved later is picked up, e.g. on a retry.
 */
export const makeBackendClient = (
  baseUrl: Effect.Effect<string, unknown>,
): BackendClient => {
  const urlOf = (endpoint: string) =>
    baseUrl.pipe(
      Effect.map((base) => base.replace(/\/+$/, "") + endpoint),
      Effect.mapError(
        (cause) => new BackendRequestError({ url: endpoint, cause }),
      ),
    );

  return {
    get: <T = any>(endpoint: string) =>
      urlOf(endpoint).pipe(
        Effect.flatMap((url) =>
          Effect.tryPromise({
            try: async () => {
              const response = await fetch(url);
              if (!response.ok) throw new Error(`HTTP ${response.status}`);
              return (await response.json()) as T;
            },
            catch: (cause) => new BackendRequestError({ url, cause }),
          }),
        ),
      ),
    sseStream: <T = any>(endpoint: string) =>
      Stream.unwrap(
        urlOf(endpoint).pipe(Effect.map((url) => sseJsonStream<T>(url))),
      ),
  };
};
