/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import type { ResettableMock } from "../../mock/types";

interface RouteResponse {
  status: number;
  headers: Record<string, string>;
  body: string;
}

export class MockHttpClient implements ResettableMock {
  private routes = new Map<string, RouteResponse>();
  private sseRoutes = new Map<string, string[]>();
  public lastRequest: { method: string; args: any } | null = null;
  public requests: Array<{ method: string; args: any }> = [];

  setRoute(method: string, endpoint: string, response: RouteResponse) {
    this.routes.set(`${method.toUpperCase()}:${endpoint}`, response);
  }

  setSSERoute(endpoint: string, events: string[]) {
    this.sseRoutes.set(endpoint, events);
  }

  reset() {
    this.routes.clear();
    this.sseRoutes.clear();
    this.lastRequest = null;
    this.requests = [];
  }

  handleStandardRequest(method: string, args: any) {
    this.lastRequest = { method, args };
    this.requests.push({ method, args });
    const routeKey = `${method.toUpperCase()}:${args.endpoint}`;
    const mockRes = this.routes.get(routeKey) ?? {
      status: 404,
      headers: {},
      body: "Not Found in Mock Server",
    };

    const { onChunk } = args;

    if (onChunk) {
      const encoder = new TextEncoder();
      const bodyBytes = encoder.encode(mockRes.body);

      if (typeof onChunk.onmessage === "function") {
        setTimeout(() => {
          if (bodyBytes.length > 0) {
            onChunk.onmessage(bodyBytes);
          }
          onChunk.onmessage({ type: "end" });
        }, 0);
      } else {
        const eventCallbackId = `_${onChunk}`;
        const emitter = (window as any)[eventCallbackId];
        if (emitter) {
          setTimeout(() => {
            if (bodyBytes.length > 0) emitter(bodyBytes);
            emitter({ type: "end" });
          }, 0);
        }
      }
    }

    return {
      status: mockRes.status,
      headers: mockRes.headers,
    };
  }

  handleSSE(args: any) {
    this.lastRequest = { method: "SSE", args };
    this.requests.push({ method: "SSE", args });

    const events = this.sseRoutes.get(args.endpoint) ?? [
      '{"data": "connected"}',
      '{"data": "chunk 1"}',
    ];

    const { onEvent } = args;
    if (onEvent && typeof onEvent.onmessage === "function") {
      events.forEach((evt, idx) => {
        setTimeout(() => onEvent.onmessage(evt), 5 * (idx + 1));
      });
      setTimeout(() => onEvent.onmessage("[CLOSE]"), 5 * (events.length + 1));
      return null;
    }

    const eventCallbackId = `_${onEvent}`;
    const eventEmitter = (window as any)[eventCallbackId];

    if (eventEmitter) {
      events.forEach((evt, idx) => {
        setTimeout(() => eventEmitter(`${evt}\n\n`), 5 * (idx + 1));
      });
      setTimeout(() => eventEmitter("[CLOSE]"), 5 * (events.length + 1));
    }
    return null; // Result<()> in Rust
  }

  handleMultipartStream(args: any) {
    this.lastRequest = { method: "POST_MULTIPART", args };
    this.requests.push({ method: "POST_MULTIPART", args });

    const manifest = args?.manifest;
    const method = (manifest?.method ?? "POST").toUpperCase();
    const endpoint = manifest?.endpoint ?? "";
    const routeKey = `${method}:${endpoint}`;

    const mockRes = this.routes.get(routeKey) ?? {
      status: 200,
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ uploaded: true }),
    };

    return {
      status: mockRes.status,
      headers: mockRes.headers,
      body: mockRes.body,
    };
  }
}

export const mockClient = new MockHttpClient();
