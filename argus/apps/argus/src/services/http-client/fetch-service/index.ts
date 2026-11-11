/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

export { FetchBridgeService, FetchBridgeLive } from "./service";
export {
  RESERVED_PROTOCOLS,
  DIRECT_CLIENT_ID,
  parseBridgeUrl,
  shouldInterceptUrl,
  extractUrlString,
  createFetchBridgeQueue,
  type ParsedBridgeUrl,
  type QueuedRequest,
  type BridgeExecutor,
} from "./interceptor";
