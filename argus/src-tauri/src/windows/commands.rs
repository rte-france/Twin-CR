/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use super::manager::WindowManager;

#[tauri::command]
pub async fn create_parent_window(
    wm: tauri::State<'_, WindowManager>,
    title: String,
    route: String,
) -> Result<(), String> {
    wm.create_parent(&title, &route).await
}

#[tauri::command]
pub async fn create_child_window(
    wm: tauri::State<'_, WindowManager>,
    parent_label: String,
    title: String,
    route: String,
) -> Result<(), String> {
    wm.create_child(&parent_label, &title, &route).await
}
