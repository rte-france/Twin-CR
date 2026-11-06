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

const DEFAULT_URL: &str = "http://localhost:8082";

#[derive(sqlx::FromRow, serde::Serialize, serde::Deserialize)]
pub struct ScadaConfig {
    pub url: String,
    pub last_sync: i64,
}

pub struct ScadaManager(pub Arc<ServerManager>);

impl ScadaManager {
    pub async fn new(app_handle: AppHandle) -> Self {
        let db = app_handle.state::<DbManager>();
        let server = ServerManager::new("ScadaClient", "scada");

        log::info!("Initializing ScadaManager...");

        let config_result = db
            .fetch_optional::<ScadaConfig>(
                "SELECT value->>'url' as url, value->>'last_sync' as last_sync
                         FROM settings WHERE key = 'scada_url'",
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
            log::error!("Failed to auto-connect Scada: {:?}", e);
        }

        Self(server)
    }
}
