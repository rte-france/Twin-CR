/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use std::sync::Arc;

use serde_json::Value;
use sqlx::types::chrono;
use tauri::{Emitter, State};

use crate::common::utils::http_client::{Client, Connected, HasUrlExt, StandardHealthCheck, Task};
use crate::common::utils::server_manager::{ServerManager, ServerState};
use crate::database::manager::DbManager;

use super::error::{Error, Result};
use super::manager::LobbyManager;

#[tauri::command]
pub async fn set_lobby_url(
    db_state: tauri::State<'_, DbManager>,
    lobby_state: State<'_, LobbyManager>,
    url: String,
) -> Result<()> {
    let config_json = serde_json::json!({
        "url": url,
        "last_sync": chrono::Utc::now().timestamp()
    })
    .to_string();

    let query = "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value";

    db_state
        .execute_with_args(query, &["lobby_url", config_json.as_str()])
        .await?;

    lobby_state.0.configure(url);

    Ok(())
}

#[tauri::command]
pub async fn get_lobby_url(lobby_state: State<'_, LobbyManager>) -> Result<String> {
    let current_client = lobby_state.0.client.load();

    match &**current_client {
        ServerState::Connected(c) => Ok(c.url().to_string()),
        ServerState::Disconnected(c) => Ok(c.url().to_string()),
        ServerState::Unconfigured => Err(Error::InvalidState("Dsl URL is not configured".into())),
    }
}

#[tauri::command]
pub async fn get_lobby_status(lobby_state: State<'_, LobbyManager>) -> Result<String> {
    let current_client = lobby_state.0.client.load();

    match &**current_client {
        ServerState::Connected(c) => Ok(format!("{:?}", c.get_current_status())),
        ServerState::Disconnected(_) => Ok("Disconnected".into()),
        ServerState::Unconfigured => Ok("Unconfigured".into()),
    }
}

#[tauri::command]
pub async fn connect_lobby(
    lobby_state: State<'_, LobbyManager>,
    app_handle: tauri::AppHandle,
) -> Result<()> {
    let current_client = lobby_state.0.client.load();
    if let ServerState::Connected(c) = &**current_client {
        let url = c.url().to_string();
        lobby_state.0.configure(url);
    }

    let strategy = Arc::new(StandardHealthCheck::new("/status"));

    lobby_state
        .0
        .connect_with_strategy(strategy, app_handle)
        .await?;

    Ok(())
}

#[tauri::command]
pub async fn disconnect_lobby(
    lobby_state: State<'_, LobbyManager>,
    app_handle: tauri::AppHandle,
) -> Result<()> {
    let current_client = lobby_state.0.client.load();
    let url = match &**current_client {
        ServerState::Connected(c) => c.url().to_string(),
        ServerState::Disconnected(c) => c.url().to_string(),
        ServerState::Unconfigured => return Ok(()),
    };

    lobby_state.0.configure(url);

    let event_name = format!("{}-status-update", lobby_state.0.event_prefix);
    let _ = app_handle.emit(&event_name, "Disconnected");

    Ok(())
}

#[tauri::command]
pub async fn get_lobby_endpoint(
    lobby_state: State<'_, LobbyManager>,
    req_id: String,
    endpoint: String,
) -> Result<Value> {
    let current_client = lobby_state.0.client.load();
    let client = ServerManager::get_connected(&current_client)?;

    let rx = client.get(req_id, &endpoint).await?;

    let response = Client::<Connected>::wait_for_response(rx, endpoint).await?;

    Ok(response)
}

#[tauri::command]
pub async fn get_lobby_tasks(lobby_state: State<'_, LobbyManager>) -> Result<Vec<Task>> {
    let current_client = lobby_state.0.client.load();
    let client = ServerManager::get_connected(&current_client)?;

    let response = client.get_active_tasks().await?;

    Ok(response)
}

#[tauri::command]
pub async fn cancel_lobby_task(dsl_state: State<'_, LobbyManager>, req_id: String) -> Result<()> {
    let current_client = dsl_state.0.client.load();
    let client = ServerManager::get_connected(&current_client)?;

    client.cancel_request(req_id).await?;

    Ok(())
}
