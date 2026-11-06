/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { Effect, Layer } from "effect";
import axios from "axios";

import { mockClient } from "../mocks/MockHttpClient";

import { FetchBridgeService, FetchBridgeLive } from "@/services/http-client";
import { HttpClientRegistryLive } from "@/services/http-client";

describe("FetchBridge - Real HTTP Client Integration (fetch & axios)", () => {
  const originalFetch = window.fetch;
  let bridge: FetchBridgeService["Type"];

  beforeEach(async () => {
    mockClient.reset();

    // Instantiate FetchBridge wired to TauriHttpClient via mockIPC
    const layer = Layer.provide(FetchBridgeLive, HttpClientRegistryLive);
    bridge = await Effect.runPromise(Effect.provide(FetchBridgeService, layer));

    // Patch global fetch to route custom scheme URLs and standard http/https through bridge
    window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      const url =
        typeof input === "string"
          ? input
          : input instanceof URL
            ? input.toString()
            : (input as Request).url;

      if (
        url.startsWith("http://") ||
        url.startsWith("https://") ||
        url.startsWith("scada://") ||
        url.startsWith("gamemaster://") ||
        url.startsWith("scada:") ||
        url.startsWith("gamemaster:")
      ) {
        return Effect.runPromise(bridge.execute(input as RequestInfo, init));
      }
      return originalFetch(input as any, init);
    };
  });

  afterEach(() => {
    window.fetch = originalFetch;
    mockClient.reset();
  });

  describe("Native fetch() integration", () => {
    it("should perform a GET request with JSON response", async () => {
      mockClient.setRoute("GET", "endpoint://users/1", {
        status: 200,
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ id: 1, name: "Alice" }),
      });

      const res = await window.fetch("scada:endpoint://users/1");
      expect(res.ok).toBe(true);
      expect(res.status).toBe(200);
      expect(res.headers.get("content-type")).toBe("application/json");

      const data = await res.json();
      expect(data).toEqual({ id: 1, name: "Alice" });
    });

    it("should perform a GET request with standard https:// URL bypassing alias check", async () => {
      const mockUrl = "https://mock-direct-server.local/v1/data";
      mockClient.setRoute("GET", mockUrl, {
        status: 200,
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ direct: true }),
      });

      const res = await window.fetch(mockUrl);
      expect(res.ok).toBe(true);
      expect(res.status).toBe(200);

      const data = await res.json();
      expect(data).toEqual({ direct: true });
    });

    it("should stream SSE events end-to-end via window.fetch on direct https:// URL", async () => {
      const mockSseUrl = "https://mock-direct-server.local/events";
      mockClient.setSSERoute(mockSseUrl, [
        '{"event": "mock-connected"}',
        '{"event": "mock-chunk-1"}',
      ]);

      const res = await window.fetch(mockSseUrl, {
        headers: { Accept: "text/event-stream" },
      });

      expect(res.ok).toBe(true);
      expect(res.status).toBe(200);
      expect(res.headers.get("content-type")).toBe("text/event-stream");
      expect(res.body).toBeDefined();

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      const chunks: string[] = [];

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        if (value) {
          chunks.push(decoder.decode(value));
        }
      }

      const fullStream = chunks.join("");
      expect(fullStream).toContain('{"event": "mock-connected"}');
      expect(fullStream).toContain('{"event": "mock-chunk-1"}');
    });

    it("should perform a POST request with JSON string body", async () => {
      mockClient.setRoute("POST", "endpoint://items", {
        status: 201,
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ created: true }),
      });

      const res = await window.fetch("gamemaster:endpoint://items", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ name: "Widget" }),
      });

      expect(res.status).toBe(201);
      const data = await res.json();
      expect(data.created).toBe(true);
    });

    it("should forward headers including Authorization Bearer", async () => {
      mockClient.setRoute("GET", "endpoint://secure/profile", {
        status: 200,
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ authenticated: true }),
      });

      const res = await window.fetch("scada:endpoint://secure/profile", {
        headers: {
          authorization: "Bearer secret-token-123",
          "x-custom-trace": "trace-456",
        },
      });

      expect(res.status).toBe(200);
      const sentHeaders = mockClient.lastRequest?.args.headers;
      expect(sentHeaders["authorization"]).toBe("Bearer secret-token-123");
      expect(sentHeaders["x-custom-trace"]).toBe("trace-456");
    });

    it("should preserve complex and encoded query parameters", async () => {
      const targetQuery = "filter=active&sort=desc&q=name%3DJohn%2B1";
      mockClient.setRoute("GET", `endpoint://search?${targetQuery}`, {
        status: 200,
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ total: 1 }),
      });

      const res = await window.fetch(`scada:endpoint://search?${targetQuery}`);
      expect(res.status).toBe(200);
      expect(mockClient.lastRequest?.args.endpoint).toBe(
        `endpoint://search?${targetQuery}`,
      );
    });

    it("should abort native fetch when AbortController triggers", async () => {
      // Endpoint that never finishes in mock
      const controller = new AbortController();
      controller.abort();

      await expect(
        window.fetch("scada:endpoint://slow", { signal: controller.signal }),
      ).rejects.toThrow();
    });
  });

  describe("Axios integration (fetch adapter)", () => {
    // Axios instance configured to use window.fetch adapter
    const api = axios.create({
      adapter: "fetch",
    });

    it("should perform GET via axios and deserialize JSON data", async () => {
      mockClient.setRoute("GET", "endpoint://sensors", {
        status: 200,
        headers: { "content-type": "application/json" },
        body: JSON.stringify([{ id: "s1", value: 42.5 }]),
      });

      const response = await api.get("scada:endpoint://sensors");
      expect(response.status).toBe(200);
      expect(response.data).toEqual([{ id: "s1", value: 42.5 }]);
    });

    it("should perform POST with payload via axios", async () => {
      mockClient.setRoute("POST", "endpoint://commands", {
        status: 200,
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ acknowledged: true }),
      });

      const response = await api.post("gamemaster:endpoint://commands", {
        action: "START",
      });
      expect(response.status).toBe(200);
      expect(response.data).toEqual({ acknowledged: true });
    });

    it("should handle HTTP 404 error through Axios standard error flow", async () => {
      mockClient.setRoute("GET", "endpoint://missing", {
        status: 404,
        headers: { "content-type": "text/plain" },
        body: "Resource Not Found",
      });

      await expect(api.get("scada:endpoint://missing")).rejects.toMatchObject({
        response: {
          status: 404,
        },
      });
    });

    it("should handle Axios cancellation via AbortController signal", async () => {
      const controller = new AbortController();
      controller.abort();

      await expect(
        api.get("scada:endpoint://cancelled", { signal: controller.signal }),
      ).rejects.toThrow();
    });

    it("should support the standard clientId://endpoint/path URL format natively", async () => {
      mockClient.setRoute("GET", "endpoint://users/42", {
        status: 200,
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ id: 42, role: "admin" }),
      });

      const res = await window.fetch("scada://endpoint/users/42");
      expect(res.ok).toBe(true);
      expect(res.status).toBe(200);
      const data = await res.json();
      expect(data).toEqual({ id: 42, role: "admin" });
    });
  });
});
