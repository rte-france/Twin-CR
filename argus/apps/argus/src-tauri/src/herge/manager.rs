/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use std::sync::Arc;
use tauri::{AppHandle, Manager};

use crate::{
    common::utils::server_manager::manager::ServerManager, database::manager::DbManager,
    herge::types::HergeConfig,
};

pub struct HergeManager(pub Arc<ServerManager>);

/// Environment variable holding the URL of the HERGE ArcGIS REST services,
/// used when no URL is stored in the settings table.
const URL_ENV_VAR: &str = "HERGE_URL";
/// Fallback when neither the settings table nor `HERGE_URL` provide a URL.
const DEFAULT_URL: &str = "http://localhost:6080/arcgis/rest/services/HERGE";

fn default_url() -> String {
    std::env::var(URL_ENV_VAR)
        .ok()
        .filter(|url| !url.is_empty())
        .unwrap_or_else(|| DEFAULT_URL.to_string())
}

impl HergeManager {
    pub async fn new(app_handle: AppHandle) -> Self {
        let db = app_handle.state::<DbManager>();
        let server = ServerManager::new("Herge", "herge");

        log::info!("Initializing HergeManager...");

        let config_result = db
            .fetch_optional::<HergeConfig>(
                "SELECT value->>'url' as url, value->>'last_sync' as last_sync
                         FROM settings WHERE key = 'herge_url'",
            )
            .await;

        let url_to_use = match config_result {
            Ok(Some(config)) => {
                log::info!("Configuration loaded from database: {}", config.url);
                config.url
            }
            Ok(None) => {
                let url = default_url();
                log::warn!("No configuration found in DB, using default: {}", url);
                url
            }
            Err(e) => {
                log::error!(
                    "Database error during init: {:?}. Falling back to default.",
                    e
                );
                default_url()
            }
        };

        server.configure(url_to_use);

        if let Err(e) = server.connect(app_handle).await {
            log::error!("Failed to auto-connect Herge: {:?}", e);
        }

        Self(server)
    }
}
