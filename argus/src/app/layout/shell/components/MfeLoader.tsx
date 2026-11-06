/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, createEffect, onCleanup, Show } from "solid-js";
import { Effect, Scope, Exit } from "effect";
import { ExtensionRenderer } from "@/services/extensions";
import { systemRuntime } from "@/config/runtime";

export const MfeLoader = (props: any) => {
  let containerRef!: HTMLDivElement;

  const [mfeInstance, setMfeInstance] = createSignal<any>(null);
  const [isReady, setIsReady] = createSignal(false);
  const [error, setError] = createSignal<string | null>(null);

  createEffect(() => {
    const manifest = props.manifest;
    if (!manifest) return;

    setIsReady(false);
    setError(null);
    setMfeInstance(null);

    const scope = Effect.runSync(Scope.make());

    const program = Effect.gen(function* () {
      const renderer = yield* ExtensionRenderer;

      if (containerRef) containerRef.innerHTML = "";

      const el = yield* renderer.loadAndRender(
        containerRef,
        manifest,
        props.componentProps,
      );

      setMfeInstance(el);
      setIsReady(true);
    }).pipe(
      Effect.provideService(Scope.Scope, scope),
      Effect.catchAll((err) => Effect.sync(() => setError(err.message))),
    );

    systemRuntime.runFork(program);

    onCleanup(() => {
      Effect.runFork(Scope.close(scope, Exit.void));
    });
  });

  createEffect(() => {
    const newProps = props.componentProps;
    const instance = mfeInstance();

    if (isReady() && instance) {
      if ("params" in instance) {
        instance.params = newProps;
      } else {
        instance.mfeProps = newProps;
      }
    }
  });

  return (
    <div class="w-full h-full relative">
      <div ref={containerRef} class="w-full h-full" />

      <Show when={error()}>
        <div class="absolute inset-0 bg-red-900/30 text-red-400 p-4 flex items-center justify-center text-center text-xs font-mono z-10">
          {error()}
        </div>
      </Show>

      <Show when={!isReady() && !error()}>
        <div class="absolute inset-0 flex items-center justify-center bg-bg z-10">
          <div class="w-4 h-4 border-2 border-primary/30 border-t-primary animate-spin rounded-full" />
        </div>
      </Show>
    </div>
  );
};
