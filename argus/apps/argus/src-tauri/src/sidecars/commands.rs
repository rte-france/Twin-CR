/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use log::info;
use tauri::State;
use tokio::sync::Mutex;

use super::error::Result;
use super::state::SidecarsState;

#[tauri::command]
pub async fn start_sidecar(state: State<'_, Mutex<SidecarsState>>, sidecar: String) -> Result<()> {
    info!("[tauri] Received command to start sidecar {}.", sidecar);

    state.lock().await.spawn_sidecar(&sidecar.as_str())?;

    info!(
        "[tauri] Sidecar {} spawned and monitoring started.",
        sidecar
    );

    Ok(())
}

#[tauri::command]
pub async fn shutdown_sidecar(
    state: State<'_, Mutex<SidecarsState>>,
    sidecar: String,
) -> Result<()> {
    info!("[tauri] Received command to shutdown sidecar {}.", sidecar);
    state.lock().await.despawn_sidecar(sidecar.as_str())?;
    info!("[tauri] Sidecar {} closed.", sidecar);

    Ok(())
}
