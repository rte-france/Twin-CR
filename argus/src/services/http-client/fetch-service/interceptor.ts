/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

export const RESERVED_PROTOCOLS = ["ipc://", "tauri://"] as const;

export const DIRECT_CLIENT_ID = "direct";

export const NULL_BODY_STATUSES = [204, 205, 304];

export interface ParsedBridgeUrl {
  clientId: string;
  actualUrl: string;
}

/**
 * Single source of truth to parse any candidate URL for the fetch bridge.
 * Returns { clientId, actualUrl } if valid, or null if it cannot / should not be intercepted.
 */
export const parseBridgeUrl = (url: string): ParsedBridgeUrl | null => {
  if (!url || typeof url !== "string") return null;

  for (const proto of RESERVED_PROTOCOLS) {
    if (url.startsWith(proto)) return null;
  }

  // Direct standard http/https URLs
  if (url.startsWith("http://") || url.startsWith("https://")) {
    return {
      clientId: DIRECT_CLIENT_ID,
      actualUrl: url,
    };
  }

  // Standard format RFC 3986: clientId://endpoint/path
  const standardMatch = url.match(
    /^([a-zA-Z0-9_-]+):\/\/([a-zA-Z0-9_-]+)(.*)$/,
  );
  if (standardMatch) {
    const clientId = standardMatch[1];
    if (clientId !== "http" && clientId !== "https") {
      const endpoint = standardMatch[2];
      const rawPath = standardMatch[3] || "";
      const path = rawPath.replace(/^\/+/, "");
      return {
        clientId,
        actualUrl: `${endpoint}://${path}`,
      };
    }
  }

  // Extension format: clientId:endpoint://path
  const extMatch = url.match(/^([a-zA-Z0-9_-]+):(.+)$/);
  if (extMatch && extMatch[1] !== "http" && extMatch[1] !== "https") {
    if (url.includes("://")) {
      return {
        clientId: extMatch[1],
        actualUrl: extMatch[2],
      };
    }
  }

  return null;
};

export interface QueuedRequest {
  input: RequestInfo | URL;
  init?: RequestInit;
  resolve: (value: Response | PromiseLike<Response>) => void;
  reject: (reason?: any) => void;
}

export interface BridgeExecutor {
  execute: (input: RequestInfo, init?: RequestInit) => Promise<Response>;
}

export const extractUrlString = (input: RequestInfo | URL): string => {
  if (typeof input === "string") return input;
  if (input instanceof URL) return input.toString();
  if (typeof input === "object" && input !== null && "url" in input) {
    return (input as Request).url;
  }
  return "";
};

export const shouldInterceptUrl = (url: string): boolean => {
  return parseBridgeUrl(url) !== null;
};

export const createFetchBridgeQueue = (executor?: BridgeExecutor) => {
  let currentExecutor: BridgeExecutor | null = executor || null;
  const queue: QueuedRequest[] = [];

  const setExecutor = (exec: BridgeExecutor) => {
    currentExecutor = exec;
    flush();
  };

  const flush = () => {
    if (!currentExecutor) return;
    while (queue.length > 0) {
      const item = queue.shift()!;
      currentExecutor
        .execute(item.input as RequestInfo, item.init)
        .then(item.resolve)
        .catch(item.reject);
    }
  };

  const handle = (
    input: RequestInfo | URL,
    init?: RequestInit,
  ): Promise<Response> => {
    if (currentExecutor) {
      return currentExecutor.execute(input as RequestInfo, init);
    }
    return new Promise<Response>((resolve, reject) => {
      queue.push({ input, init, resolve, reject });
    });
  };

  return {
    get pendingCount() {
      return queue.length;
    },
    get isReady() {
      return currentExecutor !== null;
    },
    setExecutor,
    handle,
    flush,
  };
};
