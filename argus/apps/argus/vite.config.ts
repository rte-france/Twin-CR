/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { defineConfig } from "vite";
import { fileURLToPath } from "node:url";
import solid from "vite-plugin-solid";
import tailwindcss from "@tailwindcss/vite";
import pkg from './package.json' with { type: 'json' }

const host = process.env.TAURI_DEV_HOST;

export default defineConfig(({}) => ({
  plugins: [
    tailwindcss(),
    solid(),
  ],

  define: {
    'import.meta.env.APP_VERSION': JSON.stringify(pkg.version),
  },

  clearScreen: false,

  server: {
    port: 1420,
    strictPort: true,
    host: host || false,
    hmr: host
      ? {
          protocol: "ws",
          host,
          port: 1421,
        }
      : undefined,
    watch: {
      ignored: ["**/src-tauri/**"],
    },
  },

  build: {
    target: "esnext",
    minify: "esbuild",
    assetsInlineLimit: 0,
  },

  optimizeDeps: {
    include: ["solid-js", "solid-js/web", "react", "react-dom"],
  },

  esbuild: {
    target: "ESNext",
  },

  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
}));
