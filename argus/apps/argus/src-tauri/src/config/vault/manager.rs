/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use notify::{Event, EventKind, RecursiveMode, Watcher};
use std::path::{Path, PathBuf};
use tauri::{AppHandle, Manager};
use tokio::sync::watch;

use super::error::Result;
use super::types::Vault;

pub struct VaultManager {
    filepath: PathBuf,
    pub rx: watch::Receiver<Vault>,
}

impl VaultManager {
    pub fn new(app_handle: &AppHandle) -> Result<Self> {
        let config_dir = app_handle
            .path()
            .app_config_dir()
            .expect("Failed to get app config dir");

        std::fs::create_dir_all(&config_dir)?;
        let filepath = config_dir.join("vault.json");

        let initial_vault = Self::load_file(&filepath);
        let (tx, rx) = watch::channel(initial_vault);

        let watch_path = filepath.clone();
        let mut watcher = notify::recommended_watcher(move |res: notify::Result<Event>| {
            if let Ok(event) = res {
                if matches!(event.kind, EventKind::Modify(_) | EventKind::Create(_)) {
                    log::info!(target: "Vault", "vault.json modified, reloading...");
                    let new_vault = Self::load_file(&watch_path);
                    let _ = tx.send(new_vault);
                }
            }
        })
        .expect("Failed to create watcher");

        watcher
            .watch(config_dir.as_path(), RecursiveMode::NonRecursive)
            .expect("Failed to watch vault directory");

        app_handle.manage(watcher);

        log::info!(target: "Vault", "Vault directory initialized at: {:?}", config_dir);

        Ok(Self { filepath, rx })
    }

    fn load_file(filepath: &Path) -> Vault {
        match std::fs::read_to_string(filepath) {
            Ok(content) => match serde_json::from_str(&content) {
                Ok(vault) => vault,
                Err(e) => {
                    log::warn!(target: "Vault", "vault.json is corrupted ({}), falling back to default values", e);
                    Vault::default()
                }
            },
            Err(_) => {
                log::info!(target: "Vault", "vault.json not found. Generating default.");
                let default_vault = Vault::default();
                if let Ok(content) = serde_json::to_string_pretty(&default_vault) {
                    let _ = std::fs::write(filepath, content);
                }
                default_vault
            }
        }
    }

    pub fn load(&self) -> Vault {
        self.rx.borrow().clone()
    }

    pub fn save(&self, vault: &Vault) -> Result<()> {
        let content = serde_json::to_string_pretty(vault)?;
        std::fs::write(&self.filepath, content)?;
        log::debug!(target: "Vault", "Vault saved to {:?}", self.filepath);
        Ok(())
    }
}
