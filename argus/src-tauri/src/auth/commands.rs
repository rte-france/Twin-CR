/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use tauri::{AppHandle, Manager};

use crate::config::manager::ConfigManager;
use crate::http_client::utils::http_client::Client;

use super::error::{Error, Result};
#[cfg(all(target_os = "macos", debug_assertions))]
use super::response::HTML_RESPONSE;

const DEFAULT_DEV_OAUTH_PORT: u16 = 8005;
#[cfg(not(all(target_os = "macos", debug_assertions)))]
const PROD_REDIRECT_URI: &str = "twincr://login";

fn resolve_dev_oauth_port() -> u16 {
    dotenvy::dotenv().ok();
    std::env::var("VITE_OAUTH_DEV_PORT")
        .or_else(|_| std::env::var("OAUTH_DEV_PORT"))
        .ok()
        .and_then(|p| p.parse::<u16>().ok())
        .unwrap_or(DEFAULT_DEV_OAUTH_PORT)
}

fn default_redirect_uri() -> String {
    #[cfg(all(target_os = "macos", debug_assertions))]
    {
        format!("http://localhost:{}", resolve_dev_oauth_port())
    }

    #[cfg(not(all(target_os = "macos", debug_assertions)))]
    {
        PROD_REDIRECT_URI.to_string()
    }
}

#[cfg(all(target_os = "macos", debug_assertions))]
#[tauri::command]
pub async fn start_oauth_server(
    app_handle: AppHandle,
    port: Option<u16>,
) -> std::result::Result<u16, String> {
    use tauri::Emitter;

    let target_port = port.unwrap_or_else(resolve_dev_oauth_port);
    log::debug!("Starting OAuth server on port: {target_port}");

    // Release port if an earlier instance is still bound
    let _ = tauri_plugin_oauth::cancel(target_port);

    let mut attempts = 0;
    loop {
        let config = tauri_plugin_oauth::OauthConfig {
            ports: Some(vec![target_port]),
            response: Some(HTML_RESPONSE.into()),
            ..Default::default()
        };

        let handle = app_handle.clone();
        let result = tauri_plugin_oauth::start_with_config(config, move |url| {
            log::info!("OAuth redirect received: {url}");

            if let Some(window) = handle.get_webview_window("main") {
                let _ = window.unminimize();
                let _ = window.show();
                let _ = window.set_focus();
            }

            let _ = handle.emit("deep-link-received", &url);
        });

        match result {
            Err(e) if e.kind() == std::io::ErrorKind::AddrInUse && attempts < 20 => {
                attempts += 1;
                tokio::time::sleep(std::time::Duration::from_millis(50)).await;
            }
            other => return other.map_err(|e| e.to_string()),
        }
    }
}

#[cfg(not(all(target_os = "macos", debug_assertions)))]
#[tauri::command]
pub async fn start_oauth_server(_port: Option<u16>) -> std::result::Result<u16, String> {
    Ok(0)
}

fn get_auth_client(app_handle: &AppHandle, url: &str) -> Result<reqwest::Client> {
    let proxy = app_handle
        .try_state::<ConfigManager>()
        .and_then(|config| config.settings.load().load().proxy.clone());

    Client::with_url(url)
        .build_base_client(proxy, None)
        .map_err(|e| Error::ClientInit(e.to_string()))
}

#[tauri::command]
pub async fn exchange_code(
    app_handle: AppHandle,
    code: String,
    client_id: String,
    token_url: String,
    code_verifier: String,
    redirect_uri: Option<String>,
) -> Result<String> {
    let client = get_auth_client(&app_handle, &token_url)?;
    let redirect_uri = redirect_uri.unwrap_or_else(default_redirect_uri);

    let res = client
        .post(&token_url)
        .header("Accept", "application/json")
        .form(&[
            ("grant_type", "authorization_code"),
            ("client_id", client_id.as_str()),
            ("code", code.as_str()),
            ("redirect_uri", redirect_uri.as_str()),
            ("code_verifier", code_verifier.as_str()),
        ])
        .send()
        .await?;

    if !res.status().is_success() {
        let err = res.text().await.unwrap_or_default();
        return Err(Error::AuthenticationRefused(err));
    }

    res.text()
        .await
        .map_err(|e| Error::ResponseBody(e.to_string()))
}

#[tauri::command]
pub async fn refresh_token(
    app_handle: AppHandle,
    refresh_token: String,
    client_id: String,
    token_url: String,
) -> Result<String> {
    let client = get_auth_client(&app_handle, &token_url)?;

    let res = client
        .post(&token_url)
        .header("Accept", "application/json")
        .form(&[
            ("grant_type", "refresh_token"),
            ("client_id", client_id.as_str()),
            ("refresh_token", refresh_token.as_str()),
        ])
        .send()
        .await?;

    if !res.status().is_success() {
        let err = res.text().await.unwrap_or_default();
        return Err(Error::AuthenticationRefused(err));
    }

    res.text()
        .await
        .map_err(|e| Error::ResponseBody(e.to_string()))
}
