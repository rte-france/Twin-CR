/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use serde_json::Value;
use sqlx::types::chrono;
use tauri::State;

use crate::common::utils::http_client::{Client, Connected, HasUrlExt, Task};
use crate::common::utils::server_manager::{ServerManager, ServerState};
use crate::database::manager::DbManager;

use super::error::{Error, Result};
use super::manager::DslManager;

#[tauri::command]
pub async fn set_dsl_url(
    app_handle: tauri::AppHandle,
    db_state: tauri::State<'_, DbManager>,
    dsl_state: State<'_, DslManager>,
    url: String,
) -> Result<()> {
    let config_json = serde_json::json!({
        "url": url,
        "last_sync": chrono::Utc::now().timestamp()
    })
    .to_string();

    let query = "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value";

    db_state
        .execute_with_args(query, &["dsl_url", config_json.as_str()])
        .await?;

    dsl_state.0.configure(url.clone());
    dsl_state.0.connect(app_handle).await?;

    Ok(())
}

#[tauri::command]
pub async fn get_dsl_url(dsl_state: State<'_, DslManager>) -> Result<String> {
    let current_client = dsl_state.0.client.load();

    match &**current_client {
        ServerState::Connected(c) => Ok(c.url().to_string()),
        ServerState::Disconnected(c) => Ok(c.url().to_string()),
        ServerState::Unconfigured => Err(Error::InvalidState("Dsl URL is not configured".into())),
    }
}

#[tauri::command]
pub async fn get_dsl_status(gm_state: State<'_, DslManager>) -> Result<String> {
    let current_client = gm_state.0.client.load();

    match &**current_client {
        ServerState::Connected(c) => Ok(format!("{:?}", c.get_current_status())),
        ServerState::Disconnected(_) => Ok("Disconnected".into()),
        ServerState::Unconfigured => Ok("Unconfigured".into()),
    }
}

#[tauri::command]
pub async fn connect_dsl(
    dsl_state: State<'_, DslManager>,
    app_handle: tauri::AppHandle,
) -> Result<()> {
    dsl_state.0.connect(app_handle).await?;
    Ok(())
}

#[tauri::command]
pub async fn get_dsl_endpoint(
    dsl_state: State<'_, DslManager>,
    req_id: String,
    endpoint: String,
) -> Result<Value> {
    let current_client = dsl_state.0.client.load();
    let client = ServerManager::get_connected(&current_client)?;

    let rx = client.get(req_id, &endpoint).await?;

    let response = Client::<Connected>::wait_for_response(rx, endpoint).await?;

    Ok(response)
}

#[tauri::command]
pub async fn post_dsl_endpoint(
    dsl_state: State<'_, DslManager>,
    req_id: String,
    endpoint: String,
    body: String,
    source: String,
) -> Result<Value> {
    let current_client = dsl_state.0.client.load();
    let client = ServerManager::get_connected(&current_client)?;

    let payload = serde_json::json!({ "dsl_command": body, "source": source });
    let rx = client.post(req_id, &endpoint, &payload).await?;

    let actor_res = rx.await.map_err(|_| Error::HttpClient {
        message: "Actor channel closed".into(),
    })?;
    let (status, bytes) = actor_res?;

    let response = Client::<Connected>::parse_with_api_error::<Value>(status, &bytes, endpoint)?;

    Ok(response)
}

#[tauri::command]
pub async fn get_dsl_tasks(dsl_state: State<'_, DslManager>) -> Result<Vec<Task>> {
    let current_client = dsl_state.0.client.load();
    let client = ServerManager::get_connected(&current_client)?;

    let response = client.get_active_tasks().await?;

    Ok(response)
}

#[tauri::command]
pub async fn cancel_dsl_task(dsl_state: State<'_, DslManager>, req_id: String) -> Result<()> {
    let current_client = dsl_state.0.client.load();
    let client = ServerManager::get_connected(&current_client)?;

    client.cancel_request(req_id).await?;

    Ok(())
}

#[tauri::command]
pub async fn get_dsl_text_endpoint(
    dsl_state: tauri::State<'_, DslManager>,
    req_id: String,
    endpoint: String,
) -> Result<String> {
    let current_client = dsl_state.0.client.load();
    let client = ServerManager::get_connected(&current_client)?;

    let rx = client.get(req_id, &endpoint).await?;

    let bytes = Client::<Connected>::wait_for_raw_response(rx, endpoint).await?;

    Ok(String::from_utf8_lossy(&bytes).into_owned())
}

#[tauri::command]
pub async fn put_dsl_endpoint(
    dsl_state: State<'_, DslManager>,
    req_id: String,
    endpoint: String,
    body: String,
    source: String,
) -> Result<Value> {
    let current_client = dsl_state.0.client.load();
    let client = ServerManager::get_connected(&current_client)?;

    let payload = serde_json::json!({ "dsl_command": body, "source": source });
    let rx = client.put(req_id, &endpoint, &payload).await?;

    let actor_res = rx.await.map_err(|_| Error::HttpClient {
        message: "Actor channel closed".into(),
    })?;
    let (status, bytes) = actor_res?;

    let response = Client::<Connected>::parse_with_api_error::<Value>(status, &bytes, endpoint)?;

    Ok(response)
}

#[tauri::command]
pub async fn delete_dsl_endpoint(
    dsl_state: State<'_, DslManager>,
    req_id: String,
    endpoint: String,
) -> Result<Value> {
    let current_client = dsl_state.0.client.load();
    let client = ServerManager::get_connected(&current_client)?;

    let rx = client.delete(req_id, &endpoint).await?;

    let actor_res = rx.await.map_err(|_| Error::HttpClient {
        message: "Actor channel closed".into(),
    })?;
    let (status, bytes) = actor_res?;

    let response = Client::<Connected>::parse_with_api_error::<Value>(status, &bytes, endpoint)?;

    Ok(response)
}
