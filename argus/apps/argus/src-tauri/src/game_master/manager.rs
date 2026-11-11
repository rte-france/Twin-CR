/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use std::sync::Arc;
use tauri::{AppHandle, Manager};

use crate::{common::utils::server_manager::manager::ServerManager, database::manager::DbManager};

const DEFAULT_URL: &str = "http://localhost:8083";

#[derive(sqlx::FromRow, serde::Serialize, serde::Deserialize)]
pub struct GmConfig {
    pub url: String,
    pub last_sync: i64,
}

pub struct GmManager(pub Arc<ServerManager>);

impl GmManager {
    pub async fn new(app_handle: AppHandle) -> Self {
        let db = app_handle.state::<DbManager>();
        let server = ServerManager::new("GmClient", "gm");

        log::info!("Initializing GmManager...");

        let config_result = db
            .fetch_optional::<GmConfig>(
                "SELECT value->>'url' as url, value->>'last_sync' as last_sync
                         FROM settings WHERE key = 'gm_url'",
            )
            .await;

        let url_to_use = match config_result {
            Ok(Some(config)) => {
                log::info!("Configuration loaded from database: {}", config.url);
                config.url
            }
            Ok(None) => {
                log::warn!(
                    "No configuration found in DB, using default: {}",
                    DEFAULT_URL
                );
                DEFAULT_URL.to_string()
            }
            Err(e) => {
                log::error!(
                    "Database error during init: {:?}. Falling back to default.",
                    e
                );
                DEFAULT_URL.to_string()
            }
        };

        server.configure(url_to_use);

        if let Err(e) = server.connect(app_handle.clone()).await {
            log::error!("Failed to auto-connect GameMaster: {:?}", e);
        }

        Self(server)
    }
}

// pub trait GmClientExt {
//     async fn get_dynawo_timeline(&self, req_id: String, min: i64, max: i64) -> Result<Value>;
// }

// impl GmClientExt for Client<Connected> {
//     async fn get_dynawo_timeline(&self, req_id: String, min: i64, max: i64) -> Result<Value> {
//         let endpoint = format!("/history-dynawo-timeline/?min={}&max={}", min, max);
//         let rx = self.get(req_id, &endpoint).await?;

//         Self::wait_for_response(rx, endpoint).await?
//     }
// }
