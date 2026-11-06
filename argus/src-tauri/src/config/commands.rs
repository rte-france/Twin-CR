/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use std::collections::HashMap;
use tauri::{AppHandle, Manager, State};

use crate::config::app_config::AppConfig;

use super::error::Result;
use super::manager::ConfigManager;

#[tauri::command]
pub fn get_config(config: State<AppConfig>) -> AppConfig {
    config.inner().clone()
}

#[allow(unused)]
#[tauri::command]
pub async fn set_endpoint_override(
    app_handle: AppHandle,
    plugin_id: String,
    endpoint: String,
    new_base_url: String,
) -> Result<()> {
    let config = app_handle.state::<ConfigManager>();
    let vault_manager = config.vault.load();
    let mut current_vault = vault_manager.load();

    let plugin_overrides = current_vault
        .endpoint_overrides
        .entry(plugin_id)
        .or_insert_with(HashMap::new);

    plugin_overrides.insert(endpoint, new_base_url);

    vault_manager.save(&current_vault)?;

    Ok(())
}
