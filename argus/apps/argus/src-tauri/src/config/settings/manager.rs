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
use super::types::Settings;

pub struct SettingsManager {
    filepath: PathBuf,
    pub rx: watch::Receiver<Settings>,
}

impl SettingsManager {
    pub fn new(app_handle: &AppHandle) -> Result<Self> {
        let config_dir = app_handle
            .path()
            .app_config_dir()
            .expect("failed to get app config dir");

        std::fs::create_dir_all(&config_dir)?;
        let filepath = config_dir.join("settings.json");

        let initial_settings = Self::load_file(&filepath);
        let (tx, rx) = watch::channel(initial_settings);

        let watch_path = filepath.clone();
        let mut watcher = notify::recommended_watcher(move |res: notify::Result<Event>| {
            if let Ok(event) = res {
                if matches!(event.kind, EventKind::Modify(_) | EventKind::Create(_)) {
                    log::info!(target: "Settings", "settings.json modified, reloading...");
                    let new_settings = Self::load_file(&watch_path);
                    let _ = tx.send(new_settings);
                }
            }
        })
        .expect("Failed to create watcher");

        watcher
            .watch(config_dir.as_path(), RecursiveMode::NonRecursive)
            .expect("Failed to watch config directory");

        app_handle.manage(watcher);

        log::info!(target: "Settings", "Configuration directory initialized at: {:?}", config_dir);

        Ok(Self { filepath, rx })
    }

    fn load_file(filepath: &Path) -> Settings {
        match std::fs::read_to_string(filepath) {
            Ok(content) => match serde_json::from_str(&content) {
                Ok(settings) => settings,
                Err(e) => {
                    log::warn!(target: "Settings", "settings.json is corrupted ({}), falling back to default values", e);
                    Settings::default()
                }
            },
            Err(_) => {
                log::info!(target: "Settings", "settings.json not found. Automatically generating it with default values...");
                let default_settings = Settings::default();
                if let Ok(content) = serde_json::to_string_pretty(&default_settings) {
                    let _ = std::fs::write(filepath, content);
                }
                default_settings
            }
        }
    }

    pub fn load(&self) -> Settings {
        self.rx.borrow().clone()
    }

    #[allow(unused)]
    pub fn save(&self, settings: &Settings) -> Result<()> {
        let content = serde_json::to_string_pretty(settings)?;
        std::fs::write(&self.filepath, content)?;

        log::debug!(target: "Settings", "Settings successfully saved to {:?}", self.filepath);

        Ok(())
    }
}
