/*
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
*/

import { Layer, Logger, LogLevel } from "effect";
import { ConfigLayer } from "@/services/config";
import { LobbyServiceLive } from "@/features/workspace/services";
import { ProjectServiceLive } from "@/features/project/services";

const SharedLayer = Layer.mergeAll(ConfigLayer);

const FeatureLayers = Layer.mergeAll(LobbyServiceLive, ProjectServiceLive);

function resolveLayer<SharedOut, SharedErr, SharedIn, FeaturesOut, FeaturesErr>(
  shared: Layer.Layer<SharedOut, SharedErr, SharedIn>,
  features: Layer.Layer<FeaturesOut, FeaturesErr, SharedOut>,
) {
  return features.pipe(
    Layer.provideMerge(shared),
    Layer.provide(Logger.minimumLogLevel(LogLevel.Debug)),
    Layer.provide(Logger.pretty),
  );
}

export const AppLayer = resolveLayer(SharedLayer, FeatureLayers);
