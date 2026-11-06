/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use sqlx::types::chrono;

use crate::common::utils::http_client::{Client, Connected};
use crate::common::utils::server_manager::ServerManager;
use crate::database::manager::DbManager;

use super::error::{Error, Result};
use super::manager::HergeManager;

#[tauri::command]
pub async fn set_herge_url(
    app_handle: tauri::AppHandle,
    herge_state: tauri::State<'_, HergeManager>,
    db_state: tauri::State<'_, DbManager>,
    new_url: String,
) -> Result<()> {
    let json_value = serde_json::json!({
        "url": new_url,
        "last_sync": chrono::Utc::now().timestamp()
    })
    .to_string();
    let query = "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value;";

    db_state
        .execute_with_args(query, &["herge_url", &json_value])
        .await?;

    herge_state.0.configure(&new_url);
    herge_state.0.connect(app_handle).await?;

    Ok(())
}

#[tauri::command]
pub async fn fetch_request(
    state: tauri::State<'_, HergeManager>,
    url: String,
    req_id: String,
) -> Result<tauri::ipc::Response> {
    let current_client = state.0.client.load();
    let client = ServerManager::get_connected(&current_client)?;

    let rx = client.get(req_id, &url).await.map_err(Error::HttpClient)?;
    let bytes: Vec<u8> = Client::<Connected>::wait_for_raw_response(rx, url)
        .await
        .map_err(Error::HttpClient)?;

    Ok(tauri::ipc::Response::new(bytes))
}

#[tauri::command]
pub async fn cancel_request(state: tauri::State<'_, HergeManager>, req_id: String) -> Result<()> {
    let current_client = state.0.client.load();
    let client = ServerManager::get_connected(&current_client)?;
    client
        .cancel_request(req_id)
        .await
        .map_err(Error::HttpClient)?;
    Ok(())
}
