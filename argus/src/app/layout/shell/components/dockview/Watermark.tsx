/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { IWatermarkPanelProps } from "dockview";

export const Watermark = (_props: IWatermarkPanelProps) => {
  return (
    <div
      class="relative flex flex-col items-center justify-center h-full w-full overflow-hidden select-none"
      style={{
        "background-color": "var(--bg)",
        "background-image":
          "radial-gradient(color-mix(in srgb, var(--sidebar-active), transparent 88%) 1.5px, var(--bg) 1.5px)",
        "background-size": "30px 30px",
      }}
    >
      <div
        class="absolute inset-0"
        style={{
          background: "radial-gradient(circle, transparent 10%, var(--bg) 85%)",
        }}
      />

      <div class="relative z-10 flex flex-col items-center p-6 text-center">
        <div class="mb-12 group relative">
          <div
            class="absolute inset-0 blur-3xl rounded-full scale-150 group-hover:opacity-40 transition-opacity duration-1000"
            style={{
              background: "var(--title-color)",
              opacity: "0.12",
            }}
          />

          <div
            class="relative w-64 transition-all duration-700 ease-in-out group-hover:scale-105"
            style={{
              color: "var(--title-color)",
              filter:
                "drop-shadow(0 4px 20px color-mix(in srgb, var(--title-color), transparent 80%))",
            }}
          >
            <svg
              viewBox="0 0 99 21"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              class="w-full h-auto"
            >
              <g fill="currentColor">
                <path d="M0 0.566895V6.36689H5.90288V20.5002H13.1986V6.36689H23.4125L22.0861 2.23356L21.8208 1.36689L25.8002 4.30023L25.9329 4.36689L26.1318 4.50023H26.1982L27.3257 3.63356L30.4429 1.36689L30.244 2.03356L28.8512 6.36689H37.1417V0.566895H0Z" />
                <path d="M31.1725 8.16676L31.1062 8.5001L30.9736 9.16676L30.9072 9.5001L29.846 13.9668L27.7237 10.0334L27.591 9.83343L27.392 9.5001L26.9278 8.63343V8.5001V8.43343L26.7951 8.23343V8.16676V8.1001H25.2033L25.137 8.23343L25.0707 8.5001L24.5401 9.5001L24.4738 9.63343L22.3514 13.8334L21.2239 9.5001L21.1575 9.16676L21.0249 8.56676L20.9586 8.23343H14.923L19.2341 20.5001H23.7442L26.0655 15.6334L28.3869 20.5001H32.897L37.0754 8.16676H31.1725Z" />
                <path d="M44.3711 8.1665H38.7998V20.4998H44.3711V8.1665Z" />
                <path d="M44.3711 0.566895H38.7998V6.36689H44.3711V0.566895Z" />
                <path d="M69.1765 15.1669H77.0691V20.5002H62.0134V0.566895H76.9364V5.90023H69.1765V8.10023H76.1405V12.9669H69.1765V15.1669Z" />
                <path d="M96.0379 18.2333C94.1808 19.7667 91.7268 20.5 88.7422 20.5C85.6913 20.5 83.2373 19.7667 81.3802 18.2333C79.5231 16.7 78.5945 14.7 78.5945 12.1667V0.5H86.1555V12.2333C86.1555 12.9 86.4208 13.5 86.8851 13.9667C87.3494 14.4333 87.9463 14.6333 88.7422 14.6333C89.5381 14.6333 90.135 14.4333 90.5993 13.9667C91.0636 13.5 91.3288 12.9667 91.3288 12.2333V0.5H98.8235V12.1667C98.8235 14.7 97.895 16.7 96.0379 18.2333Z" />
                <path d="M58.1666 7.9667C56.9064 6.90003 55.182 6.3667 53.0596 6.3667C50.9372 6.3667 49.2791 6.90003 47.9526 7.9667C46.6924 9.03336 46.0292 10.5 46.0292 12.2334V20.5H51.2688H51.6004V13.7V13.5667C51.6004 13.0334 51.7331 12.6334 51.9321 12.3667C52.131 12.1 52.4626 11.9667 52.8606 11.9667C52.9269 11.9667 52.9269 11.9667 52.9932 11.9667C53.0596 11.9667 53.0596 11.9667 53.1259 11.9667C53.5238 11.9667 53.8555 12.1 54.0544 12.3667C54.2534 12.6334 54.3861 13.0334 54.3861 13.5667V13.7V20.5H54.7177H59.9573V12.2334C60.09 10.4334 59.493 9.03336 58.1666 7.9667Z" />
              </g>
            </svg>
          </div>
        </div>

        <div class="max-w-md space-y-6">
          <div class="space-y-1">
            <h2
              class="text-4xl font-bold tracking-tighter uppercase italic"
              style={{
                color: "var(--title-color)",
                "font-family": "var(--title-font)",
              }}
            >
              French Pilot
            </h2>
          </div>

          <div
            class="h-px w-32 mx-auto"
            style={{
              background:
                "linear-gradient(90deg, transparent, var(--border), transparent)",
            }}
          />

          <p
            class="text-lg leading-relaxed"
            style={{
              color: "var(--fg)",
              "font-family": "var(--font)",
            }}
          >
            Your workspace is empty.
          </p>
          <p class="text-sm opacity-60">Add equipment to begin monitoring.</p>
        </div>
      </div>
    </div>
  );
};
