/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

(function () {
  let fsBridgeInstance = null;
  const fsRequestQueue = [];

  window.addEventListener("argus:fs-bridge-ready", function (event) {
    fsBridgeInstance = event.detail;

    while (fsRequestQueue.length > 0) {
      const { method, args, resolve, reject } = fsRequestQueue.shift();
      fsBridgeInstance.execute(method, args).then(resolve).catch(reject);
    }
  });

  window.showOpenFilePicker = function (options) {
    if (fsBridgeInstance) {
      return fsBridgeInstance.execute("showOpenFilePicker", [options]);
    }
    return new Promise((resolve, reject) => {
      fsRequestQueue.push({ method: "showOpenFilePicker", args: [options], resolve, reject });
    });
  };

  window.showDirectoryPicker = function (options) {
    if (fsBridgeInstance) {
      return fsBridgeInstance.execute("showDirectoryPicker", [options]);
    }
    return new Promise((resolve, reject) => {
      fsRequestQueue.push({ method: "showDirectoryPicker", args: [options], resolve, reject });
    });
  };
})();
