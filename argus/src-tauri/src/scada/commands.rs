/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use serde_json::Value;
use sqlx::types::chrono;
use tauri::ipc::Channel;
use tauri::State;

use crate::common::utils::http_client::{Client, Connected, HasUrlExt, Task};
use crate::common::utils::server_manager::{ServerManager, ServerState};
use crate::database::manager::DbManager;

use super::error::{Error, Result};
use super::manager::ScadaManager;

#[tauri::command]
pub async fn set_scada_url(
    app_handle: tauri::AppHandle,
    db_state: tauri::State<'_, DbManager>,
    scada_state: State<'_, ScadaManager>,
    url: String,
) -> Result<()> {
    let config_json = serde_json::json!({
        "url": url,
        "last_sync": chrono::Utc::now().timestamp()
    })
    .to_string();

    let query = "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value";

    db_state
        .execute_with_args(query, &["scada_url", &config_json])
        .await?;

    scada_state.0.configure(url);
    scada_state.0.connect(app_handle).await?;

    Ok(())
}

#[tauri::command]
pub async fn get_scada_url(scada_state: State<'_, ScadaManager>) -> Result<String> {
    let current_client = scada_state.0.client.load();

    match &**current_client {
        ServerState::Connected(c) => Ok(c.url().to_string()),
        ServerState::Disconnected(c) => Ok(c.url().to_string()),
        ServerState::Unconfigured => Err(Error::InvalidState("Scada URL is not configured".into())),
    }
}

#[tauri::command]
pub async fn get_scada_status(scada_state: State<'_, ScadaManager>) -> Result<String> {
    let current_client = scada_state.0.client.load();

    match &**current_client {
        ServerState::Connected(c) => Ok(format!("{:?}", c.get_current_status())),
        ServerState::Disconnected(_) => Ok("Disconnected".into()),
        ServerState::Unconfigured => Ok("Unconfigured".into()),
    }
}

#[tauri::command]
pub async fn connect_scada(
    scada_state: State<'_, ScadaManager>,
    app_handle: tauri::AppHandle,
) -> Result<()> {
    scada_state.0.connect(app_handle).await?;
    Ok(())
}

#[tauri::command]
pub async fn get_scada_endpoint(
    scada_state: State<'_, ScadaManager>,
    req_id: String,
    endpoint: String,
) -> Result<Value> {
    let current_client = scada_state.0.client.load();
    let client = ServerManager::get_connected(&current_client)?;

    let rx = client.get(req_id, &endpoint).await?;

    let response = Client::<Connected>::wait_for_response(rx, endpoint).await?;

    Ok(response)
}

#[tauri::command]
pub async fn get_scada_tasks(scada_state: State<'_, ScadaManager>) -> Result<Vec<Task>> {
    let current_client = scada_state.0.client.load();
    let client = ServerManager::get_connected(&current_client)?;
    let response = client.get_active_tasks().await?;
    Ok(response)
}

#[tauri::command]
pub async fn cancel_scada_task(scada_state: State<'_, ScadaManager>, req_id: String) -> Result<()> {
    let current_client = scada_state.0.client.load();
    let client = ServerManager::get_connected(&current_client)?;
    client.cancel_request(req_id).await?;
    Ok(())
}

#[derive(Clone, serde::Serialize)]
#[serde(tag = "type", content = "data")]
pub enum SseMessage {
    Chunk(Value),
    Closed,
}

#[tauri::command]
pub async fn start_scada_sse(
    scada_state: tauri::State<'_, ScadaManager>,
    req_id: String,
    endpoint: String,
    on_event: Channel<SseMessage>,
) -> Result<()> {
    let current_client = scada_state.0.client.load();
    let client = ServerManager::get_connected(&current_client)?;

    let mut rx = client.sse(req_id.clone(), endpoint).await?;

    tokio::spawn(async move {
        let mut buffer = String::new();

        while let Some(Ok(bytes)) = rx.recv().await {
            if let Ok(text) = String::from_utf8(bytes.to_vec()) {
                buffer.push_str(&text);

                while let Some(pos) = buffer.find("\n\n") {
                    let frame = buffer[..pos].to_string();
                    buffer = buffer[pos + 2..].to_string();

                    for line in frame.lines() {
                        if line.starts_with("data: ") {
                            let json_str = &line[6..];
                            if let Ok(json_val) = serde_json::from_str::<Value>(json_str) {
                                let _ = on_event.send(SseMessage::Chunk(json_val));
                            }
                        }
                    }
                }
            }
        }
        let _ = on_event.send(SseMessage::Closed);
    });

    Ok(())
}

#[tauri::command]
pub async fn post_scada_endpoint(
    scada_state: State<'_, ScadaManager>,
    req_id: String,
    endpoint: String,
    body: String,
) -> Result<Value> {
    let current_client = scada_state.0.client.load();
    let client = ServerManager::get_connected(&current_client)?;

    let body_value: Value = serde_json::from_str(&body).map_err(|e| Error::HttpClient {
        message: e.to_string(),
    })?;
    let rx = client.post(req_id, &endpoint, &body_value).await?;

    let actor_res = rx.await.map_err(|_| Error::HttpClient {
        message: "Actor channel closed".into(),
    })?;
    let (status, bytes) = actor_res?;

    let response = Client::<Connected>::parse_with_api_error::<Value>(status, &bytes, endpoint)?;

    Ok(response)
}
