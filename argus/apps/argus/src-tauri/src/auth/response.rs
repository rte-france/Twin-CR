/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

pub const HTML_RESPONSE: &str = r#"<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Argus Authentication</title>
  <style>
    body {
      margin: 0;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #0f172a;
      color: #e2e8f0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    .card {
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 12px;
      padding: 32px 40px;
      max-width: 420px;
      text-align: center;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
    }
    .badge {
      display: inline-block;
      padding: 4px 10px;
      border-radius: 9999px;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      background: #0369a1;
      color: #e0f2fe;
      margin-bottom: 16px;
    }
    h1 { font-size: 20px; margin: 0 0 12px; color: #f8fafc; }
    p { font-size: 14px; line-height: 1.5; color: #94a3b8; margin: 0 0 20px; }
    .hint { font-size: 12px; color: #64748b; }
  </style>
</head>
<body>
  <div class="card">
    <span class="badge">macOS Dev Mode</span>
    <h1>Authentication Successful</h1>
    <p>You are now connected to Argus. You can safely close this browser window and return to the application.</p>
    <div class="hint">Window will try to close automatically...</div>
  </div>
  <script>
    setTimeout(() => { window.close(); }, 1200);
  </script>
</body>
</html>"#;
