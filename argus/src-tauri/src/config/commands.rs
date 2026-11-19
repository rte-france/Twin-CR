/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use tauri::{AppHandle, Emitter, Manager};

use super::error::Result;
use super::manager::ConfigManager;
use super::settings::types::Settings;

fn json_merge(target: &mut serde_json::Value, patch: serde_json::Value) {
    match (target, patch) {
        (serde_json::Value::Object(target_map), serde_json::Value::Object(patch_map)) => {
            for (key, val) in patch_map {
                if val.is_null() {
                    target_map.remove(&key);
                } else {
                    json_merge(
                        target_map.entry(key).or_insert(serde_json::Value::Null),
                        val,
                    );
                }
            }
        }
        (target, patch) => *target = patch,
    }
}

#[tauri::command]
pub fn get_settings(app_handle: AppHandle) -> Result<Settings> {
    let config = app_handle.state::<ConfigManager>();
    Ok(config.settings.load().load())
}

#[tauri::command]
pub fn patch_settings(app_handle: AppHandle, patch: serde_json::Value) -> Result<Settings> {
    let config = app_handle.state::<ConfigManager>();
    let settings_manager = config.settings.load();
    let current = settings_manager.load();

    let mut current_json = serde_json::to_value(&current)?;
    json_merge(&mut current_json, patch);

    let updated: Settings = serde_json::from_value(current_json)?;
    settings_manager.save(&updated)?;

    let _ = app_handle.emit("settings-changed", &updated);

    Ok(updated)
}
