# Tauri + Solid + Typescript

This template should help get you started developing with Tauri, Solid and Typescript in Vite.

## Recommended IDE Setup

- [VS Code](https://code.visualstudio.com/) + [Tauri](https://marketplace.visualstudio.com/items?itemName=tauri-apps.tauri-vscode) + [rust-analyzer](https://marketplace.visualstudio.com/items?itemName=rust-lang.rust-analyzer)

## Setup variables

Argus reads a config file to set up some variables needed at startup. A default config file is provided : src-tauri/config.json. Its content is copied in <user directory>/.config/com.twincr.argus/config.json.

It contains URLs for keycloak, session_manager and lobby :
```
{
  "keycloak_url": "https://localhost:8443",
  "keycloak_realm": "twineu",
  "keycloak_client_id": "session-manager-client",
  "session_manager_url": "http://localhost:8090",
  "lobby_url": "http://localhost:8080",
  "environment": "development",
  "api_url": "http://localhost:3000",
  "api_token": "",
  "oauth_dev_port": 8005
}
```

The config.json file is created automatically at startup. You can modify its content to fit your needs. In this case, you need to restart the application.

Argus needs Keycloak served over HTTPS. Follow the setup in
[keycloak/README.md](../keycloak/README.md) first — generating the certificate,
trusting it, and mapping the `keycloak` hostname — then the default
`keycloak_url` works whether Argus runs natively or in docker compose.

`session_manager_url` does differ by mode: `http://localhost:8090` natively,
`http://session-manager:8090` inside docker compose (profile `argus`).

The HERGE GIS viewer reads the URL of its ArcGIS REST services from the settings
saved by its configuration panel. When none is saved yet, it uses the `HERGE_URL`
environment variable, then `http://localhost:6080/arcgis/rest/services/HERGE`.
