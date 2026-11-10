/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { ManagedRuntime, Layer, Logger, LogLevel } from "effect";

import { ArcGisLayer } from "@/features/herge-viewer/services";
import { GmClientLive } from "@/services/game-master/service";
import { ScadaClientLive } from "@/services/scada/service";
import { AppModeLive } from "@/services/app-mode";
import { DslClientLive } from "@/services/dsl";
import { WindowManagerLive } from "@/services/window-manager";
import { WindowBootstrapperLive } from "@/services/window-bootstrap";
import { TimeClientLive } from "@/services/time/service";
import { DslLayer } from "@/features/dsl-editor/services";
import { ChartServiceLive } from "@/services/chart";
import { MappingServiceLive } from "@/services/mapping";
import { LobbyClientLive } from "@/services/lobby";
import { HergeClientLive } from "@/services/herge";
import { ExtensionLive, ExtensionRendererLive } from "@/services/extensions";
import { BackendLive } from "@/services/backend";
import { ConfigServiceLive } from "@/services/config";
import { FileSystemLive } from "@/services/file-system";
import { EventRegistryLive } from "@/services/events";
import { KeymapSystemLive } from "@/services/keymaps";

import {
  HttpClientLayer,
  HttpClientRegistryLive,
  FetchBridgeLive,
} from "@/services/http-client";

const HttpServicesLayer = Layer.mergeAll(
  HttpClientLayer,
  FetchBridgeLive,
).pipe(Layer.provide(HttpClientRegistryLive));

const BaseServicesLayer = Layer.mergeAll(
  ConfigServiceLive,
  FileSystemLive,
  ExtensionLive,
  ExtensionRendererLive,
  GmClientLive,
  ScadaClientLive,
  DslClientLive,
  WindowManagerLive,
  WindowBootstrapperLive,
  ChartServiceLive,
  LobbyClientLive,
  HergeClientLive,
  HttpClientRegistryLive,
  HttpServicesLayer,
  EventRegistryLive,
  KeymapSystemLive,
);

const ResolvedAppModeLayer = Layer.provide(AppModeLive, BaseServicesLayer);
const CoreServicesLayer = Layer.merge(BaseServicesLayer, ResolvedAppModeLayer);
const ResolvedBackendLayer = Layer.provide(BackendLive, CoreServicesLayer);

const CoreDependantLayers = Layer.mergeAll(
  Layer.provide(TimeClientLive, CoreServicesLayer),
  Layer.provide(DslLayer, CoreServicesLayer),
  Layer.provide(MappingServiceLive, CoreServicesLayer),
);

const ResolvedArcGisLayer = Layer.provide(ArcGisLayer, BaseServicesLayer);

export const AppLayer = Layer.mergeAll(
  CoreServicesLayer,
  CoreDependantLayers,
  ResolvedArcGisLayer,
  ResolvedBackendLayer,
).pipe(
  Layer.provide(Logger.minimumLogLevel(LogLevel.Debug)),
  Layer.provide(Logger.pretty),
);

export const systemRuntime = ManagedRuntime.make(AppLayer);
