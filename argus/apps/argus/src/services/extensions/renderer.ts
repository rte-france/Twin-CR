/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Context, Effect, Layer, Scope, Schedule } from "effect";
import { convertFileSrc } from "@tauri-apps/api/core";

const loadedScripts = new Set<string>();

export interface RendererService {
  readonly render: (
    container: HTMLElement,
    tagName: string,
    props?: Record<string, any>,
  ) => Effect.Effect<HTMLElement, never, Scope.Scope>;

  readonly loadAndRender: (
    container: HTMLElement,
    manifest: { entryUrl?: string; isLocalFile?: boolean; elementTag: string },
    props?: Record<string, any>,
  ) => Effect.Effect<HTMLElement, Error, Scope.Scope>;
}

export class ExtensionRenderer extends Context.Tag("ExtensionRenderer")<
  ExtensionRenderer,
  RendererService
>() {}

export const ExtensionRendererLive = Layer.succeed(
  ExtensionRenderer,
  ExtensionRenderer.of({
    render: (container, tagName, props) =>
      Effect.acquireRelease(
        Effect.sync(() => {
          const el = document.createElement(tagName);
          el.className = "w-full h-full block";
          if (props) (el as any).mfeProps = props;
          container.appendChild(el);
          return el;
        }),
        (el) =>
          Effect.sync(() => {
            if (container.contains(el)) container.removeChild(el);
          }),
      ),

    loadAndRender: function (container, manifest, props) {
      const self = this;

      return Effect.gen(function* () {
        const { entryUrl, isLocalFile, elementTag } = manifest;

        if (entryUrl) {
          const url = isLocalFile ? convertFileSrc(entryUrl) : entryUrl;

          if (
            !loadedScripts.has(url) &&
            !document.querySelector(`script[src="${url}"]`)
          ) {
            yield* Effect.async<void, Error>((resume) => {
              const script = document.createElement("script");
              script.src = url;
              script.type = "module";
              script.async = true;
              script.onload = () => {
                loadedScripts.add(url);
                resume(Effect.void);
              };
              script.onerror = () =>
                resume(Effect.fail(new Error(`Failed to load: ${url}`)));
              document.head.appendChild(script);
            });
          }
        }

        yield* Effect.retry(
          Effect.gen(function* () {
            if (!customElements.get(elementTag)) {
              yield* Effect.fail(
                new Error(`Tag <${elementTag}> not registered`),
              );
            }
          }),
          Schedule.spaced("100 millis").pipe(
            Schedule.intersect(Schedule.recurs(20)),
          ),
        );

        return yield* self.render(container, elementTag, props);
      });
    },
  }),
);
