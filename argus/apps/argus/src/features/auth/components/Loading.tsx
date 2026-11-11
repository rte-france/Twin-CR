/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import type { Component } from "solid-js";

export const Loading: Component = () => {
  return (
    <div class="loader-container">
      <style>{`
        .loader-container {
          display: flex;
          align-items: center;
          justify-content: center;
          min-height: 100vh;
          background: radial-gradient(circle at center, #0a1128 0%, #000000 80%);
          position: relative;
          overflow: hidden;
          font-family: system-ui, -apple-system, sans-serif;
        }

        .loader-container::after {
          content: "";
          position: absolute;
          inset: 0;
          background: radial-gradient(circle at center, transparent 30%, rgba(0, 0, 0, 0.8) 100%);
          z-index: 15;
          pointer-events: none;
        }

        .grain-overlay {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          pointer-events: none;
          z-index: 20;
          opacity: 0.35;
          mix-blend-mode: color-dodge;
        }

        .loader-text {
          position: absolute;
          color: #ffffff;
          font-size: 4rem;
          font-weight: 500;
          letter-spacing: -0.03em;
          z-index: 25;
          margin: 0;
        }

        .svg-container {
          width: 800px;
          height: 800px;
          position: absolute;
          max-width: 100vw;
          max-height: 100vh;
          filter: drop-shadow(0 0 20px rgba(0, 85, 255, 0.2));
        }

        .ring {
          fill: none;
          transform-origin: center;
        }

        .ring-1 {
          stroke: url(#blue-grad-1);
          stroke-width: 50;
          stroke-dasharray: 120 150 200 120 300 110;
          animation: spin 14s linear infinite;
        }

        .ring-2 {
          stroke: url(#blue-grad-2);
          stroke-width: 80;
          stroke-dasharray: 250 200 150 300 400 200;
          animation: spin-reverse 20s linear infinite;
        }

        .ring-3 {
          stroke: url(#blue-grad-1);
          stroke-width: 110;
          stroke-dasharray: 450 300 250 400 500 200;
          animation: spin 28s linear infinite;
        }

        @keyframes spin {
          100% { transform: rotate(360deg); }
        }

        @keyframes spin-reverse {
          100% { transform: rotate(-360deg); }
        }
      `}</style>

      <svg class="grain-overlay" xmlns="http://www.w3.org/2000/svg">
        <filter id="noiseFilter">
          <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="3" stitchTiles="stitch" />
        </filter>
        <rect width="100%" height="100%" filter="url(#noiseFilter)" />
      </svg>

      <svg class="svg-container" viewBox="0 0 1000 1000">
        <defs>
          <linearGradient id="blue-grad-1" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#001a4d" />
            <stop offset="30%" stop-color="#0055ff" />
            <stop offset="70%" stop-color="#66aaff" />
            <stop offset="100%" stop-color="#ffffff" />
          </linearGradient>
          <linearGradient id="blue-grad-2" x1="100%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stop-color="#002266" />
            <stop offset="50%" stop-color="#0077ff" />
            <stop offset="100%" stop-color="#b3d4ff" />
          </linearGradient>
        </defs>

        <circle class="ring ring-1" cx="500" cy="500" r="220" />
        <circle class="ring ring-2" cx="500" cy="500" r="320" />
        <circle class="ring ring-3" cx="500" cy="500" r="450" />
      </svg>

      <h1 class="loader-text">Twin-CR</h1>
    </div>
  );
};
