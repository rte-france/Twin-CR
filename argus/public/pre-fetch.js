/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

(function () {
  const originalFetch = window.fetch;
  let fetchBridgeInstance = null;
  const fetchRequestQueue = [];

  // Native schemes that must never be handled by the bridge
  const NATIVE_SCHEMES = new Set([
    "ipc:",
    "tauri:",
    "asset:",
    "blob:",
    "data:",
    "about:",
    "file:",
  ]);

  // Escaped regex for custom scheme aliases (e.g. clientId://endpoint/path)
  const ALIAS_URL = /^[a-zA-Z0-9_-]+:\/\/[a-zA-Z0-9_-]+/;

  function extractUrlString(input) {
    if (typeof input === "string") return input;
    if (input instanceof URL) return input.toString();
    if (input && typeof input.url === "string") return input.url;
    return null;
  }

  function shouldBridge(rawUrl) {
    if (!rawUrl) return false;

    let parsedUrl;
    try {
      parsedUrl = new URL(rawUrl, window.location.href);
    } catch {
      return false;
    }

    if (parsedUrl.protocol === "http:" || parsedUrl.protocol === "https:") {
      return parsedUrl.origin !== window.location.origin;
    }

    if (NATIVE_SCHEMES.has(parsedUrl.protocol)) {
      return false;
    }

    return ALIAS_URL.test(rawUrl);
  }

  window.addEventListener("argus:bridge-ready", function (event) {
    fetchBridgeInstance = event.detail;

    while (fetchRequestQueue.length > 0) {
      const { input, init, resolve, reject } = fetchRequestQueue.shift();
      fetchBridgeInstance.execute(input, init).then(resolve).catch(reject);
    }
  });

  window.fetch = async function (input, init) {
    const rawUrl = extractUrlString(input);

    if (shouldBridge(rawUrl)) {
      if (fetchBridgeInstance) {
        return fetchBridgeInstance.execute(input, init);
      }

      return new Promise((resolve, reject) => {
        fetchRequestQueue.push({ input, init, resolve, reject });
      });
    }

    return originalFetch(input, init);
  };
})();
