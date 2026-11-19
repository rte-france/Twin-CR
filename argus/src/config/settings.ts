import type { SettingSectionDefinition } from "@/types/settings.type";

export const SETTINGS: SettingSectionDefinition[] = [
  {
    id: "network",
    title: "Network & Proxy",
    description:
      "Configure proxy rules and network routing for Argus background workers.",
    fields: [
      {
        key: "proxy",
        label: "HTTP / HTTPS Proxy",
        description:
          "Proxy server URL used by HttpManager (e.g. http://127.0.0.1:8080).",
        type: "string",
        placeholder: "http://proxy.corporate.local:8080",
      },
      {
        key: "no_proxy",
        label: "No Proxy Hosts",
        description:
          "Comma-separated list of hostnames or IPs bypassing the proxy.",
        type: "string[]",
        placeholder: "localhost, 127.0.0.1, .internal",
      },
    ],
  },
  {
    id: "appearance",
    title: "Appearance",
    description: "Theme and general UI density options.",
    fields: [
      {
        key: "theme",
        label: "Theme",
        description: "Application color palette.",
        type: "select",
        options: [
          { label: "System Default", value: "system" },
          { label: "Dark", value: "dark" },
          { label: "Light", value: "light" },
          { label: "One Dark", value: "one-dark" },
          { label: "ISA 101", value: "isa-101" },
        ],
        defaultValue: "system",
      },
      {
        key: "compactMode",
        label: "Compact Layout",
        description:
          "Reduce tab and panel padding for denser multi-panel workflows.",
        type: "boolean",
        defaultValue: false,
      },
    ],
  },
];
