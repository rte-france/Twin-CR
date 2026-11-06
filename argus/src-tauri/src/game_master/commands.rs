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
use tauri::{Emitter, State};

use crate::common::utils::http_client::{Client, Connected, HasUrlExt, Task};
use crate::common::utils::server_manager::{ServerManager, ServerState};
use crate::database::manager::DbManager;

use super::error::{Error, Result};
use super::manager::GmManager;

#[tauri::command]
pub async fn set_gm_url(
    app_handle: tauri::AppHandle,
    db_state: tauri::State<'_, DbManager>,
    gm_state: State<'_, GmManager>,
    url: String,
) -> Result<()> {
    let config_json = serde_json::json!({
        "url": url,
        "last_sync": chrono::Utc::now().timestamp()
    })
    .to_string();

    let query = "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value";

    db_state
        .execute_with_args(query, &["gm_url", &config_json])
        .await?;

    gm_state.0.configure(url.clone());
    gm_state.0.connect(app_handle).await?;

    Ok(())
}

#[tauri::command]
pub async fn get_gm_url(gm_state: State<'_, GmManager>) -> Result<String> {
    let current_client = gm_state.0.client.load();

    match &**current_client {
        ServerState::Connected(c) => Ok(c.url().to_string()),
        ServerState::Disconnected(c) => Ok(c.url().to_string()),
        ServerState::Unconfigured => Err(Error::InvalidState(
            "GameMaster URL is not configured".into(),
        )),
    }
}

#[tauri::command]
pub async fn get_gm_status(gm_state: State<'_, GmManager>) -> Result<String> {
    let current_client = gm_state.0.client.load();

    match &**current_client {
        ServerState::Connected(c) => Ok(format!("{:?}", c.get_current_status())),
        ServerState::Disconnected(_) => Ok("Disconnected".into()),
        ServerState::Unconfigured => Ok("Unconfigured".into()),
    }
}

#[tauri::command]
pub async fn connect_gm(
    gm_state: State<'_, GmManager>,
    app_handle: tauri::AppHandle,
) -> Result<()> {
    gm_state.0.connect(app_handle).await?;
    Ok(())
}

#[tauri::command]
pub async fn disconnect_gm(
    gm_state: State<'_, GmManager>,
    app_handle: tauri::AppHandle,
) -> Result<()> {
    let current_client = gm_state.0.client.load();
    let url = match &**current_client {
        ServerState::Connected(c) => c.url().to_string(),
        ServerState::Disconnected(c) => c.url().to_string(),
        ServerState::Unconfigured => return Ok(()),
    };

    gm_state.0.configure(url);

    let event_name = format!("{}-status-update", gm_state.0.event_prefix);
    let _ = app_handle.emit(&event_name, "Disconnected");

    Ok(())
}

#[tauri::command]
pub async fn get_gm_endpoint(
    gm_state: State<'_, GmManager>,
    req_id: String,
    endpoint: String,
) -> Result<Value> {
    let current_client = gm_state.0.client.load();
    let client = ServerManager::get_connected(&current_client)?;

    let rx = client.get(req_id, &endpoint).await?;

    let response = Client::<Connected>::wait_for_response(rx, endpoint).await?;

    Ok(response)
}

#[tauri::command]
pub async fn get_gm_tasks(gm_state: State<'_, GmManager>) -> Result<Vec<Task>> {
    let current_client = gm_state.0.client.load();
    let client = ServerManager::get_connected(&current_client)?;
    let response = client.get_active_tasks().await?;
    Ok(response)
}

#[tauri::command]
pub async fn cancel_gm_task(gm_state: State<'_, GmManager>, req_id: String) -> Result<()> {
    let current_client = gm_state.0.client.load();
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
pub async fn start_gm_sse(
    gm_state: tauri::State<'_, GmManager>,
    req_id: String,
    endpoint: String,
    on_event: Channel<SseMessage>,
) -> Result<()> {
    let current_client = gm_state.0.client.load();
    let client = ServerManager::get_connected(&current_client)?;

    let mut rx = client.sse(req_id.clone(), endpoint).await?;

    tokio::spawn(async move {
        let mut buffer: Vec<u8> = Vec::new();

        loop {
            match rx.recv().await {
                Some(Ok(bytes)) => {
                    buffer.extend_from_slice(&bytes);

                    while let Some(pos) = buffer.windows(2).position(|w| w == b"\n\n") {
                        let frame_bytes = buffer[..pos].to_vec();

                        buffer.drain(..pos + 2);
                        if let Ok(text) = String::from_utf8(frame_bytes) {
                            for line in text.lines() {
                                if line.starts_with("data: ") {
                                    let json_str = &line[6..];
                                    if let Ok(json_val) =
                                        serde_json::from_str::<serde_json::Value>(json_str)
                                    {
                                        let _ = on_event.send(SseMessage::Chunk(json_val));
                                    }
                                }
                            }
                        }
                    }
                }
                Some(Err(e)) => {
                    eprintln!("Erreur de lecture du flux SSE côté backend: {:?}", e);
                    break;
                }
                None => {
                    println!("Flux SSE backend terminé par le serveur distant.");
                    break;
                }
            }
        }

        let _ = on_event.send(SseMessage::Closed);
    });

    Ok(())
}

#[tauri::command]
pub async fn post_gm_endpoint(
    gm_state: State<'_, GmManager>,
    req_id: String,
    endpoint: String,
    body: String,
) -> Result<Value> {
    let current_client = gm_state.0.client.load();
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
