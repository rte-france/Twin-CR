/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { render } from "solid-js/web";
import { App } from "./app";

import { initArgusConfig } from "@/services/config/config";
import { bootstrapFetchBridge } from "@/utils/bootstrapFetchBridge";
import { bootstrapFileSystemBridge } from "@/utils/bootstrapFileSystemBridge";

import "./icons-bundle";
import "./styles/index.css";

async function bootstrap() {
  await initArgusConfig();

  render(() => <App />, document.getElementById("root") as HTMLElement);
}

bootstrap();
bootstrapFetchBridge();
bootstrapFileSystemBridge();
