/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { mockClient } from "./MockHttpClient";
import { get_available_extensions } from "./MockExtension";

export * from "./MockHttpClient";
export * from "./MockExtension";

export const httpClientHandlers: Record<string, (args: any) => any> = {
  get: (args) => mockClient.handleStandardRequest("GET", args),
  post: (args) => mockClient.handleStandardRequest("POST", args),
  post_multipart_stream: (args) => mockClient.handleMultipartStream(args),
  put: (args) => mockClient.handleStandardRequest("PUT", args),
  patch: (args) => mockClient.handleStandardRequest("PATCH", args),
  delete: (args) => mockClient.handleStandardRequest("DELETE", args),
  head: (args) => mockClient.handleStandardRequest("HEAD", args),
  options: (args) => mockClient.handleStandardRequest("OPTIONS", args),
  trace: (args) => mockClient.handleStandardRequest("TRACE", args),
  sse: (args) => mockClient.handleSSE(args),
  cancel_http_request: () => null,
  active_ping: () => null,

  get_available_extensions,
};
