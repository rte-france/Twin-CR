/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

export {
  HttpClientRegistry,
  HttpClientRegistryLive,
} from "./http-service/registry";
export { HttpClientLayer, makeHttpClientLayer } from "./http-service";
export { makeHttpCache, type HttpCacheConfig } from "./http-service/cache";
export {
  makeEndpointUri,
  executeSSERequest,
  executeStandardRequest,
  fetchManifestsFromRust,
} from "./http-service/utils";
export {
  ExtensionNotFoundError,
  TauriInvokeError,
} from "./http-service/errors";

export {
  FetchBridgeService,
  FetchBridgeLive,
  RESERVED_PROTOCOLS,
  DIRECT_CLIENT_ID,
  parseBridgeUrl,
  shouldInterceptUrl,
  extractUrlString,
  createFetchBridgeQueue,
  type ParsedBridgeUrl,
  type QueuedRequest,
  type BridgeExecutor,
} from "./fetch-service";
