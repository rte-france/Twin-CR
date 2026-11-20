/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use arc_swap::ArcSwap;
use tauri::AppHandle;

use super::error::Result;
use super::settings::manager::SettingsManager;

pub struct ConfigManager {
    pub settings: ArcSwap<SettingsManager>,
}

impl ConfigManager {
    pub fn new(app_handle: AppHandle) -> Result<Self> {
        Ok(Self {
            settings: ArcSwap::from_pointee(SettingsManager::new(&app_handle)?),
        })
    }

    pub fn load(&self) {
        let settings = self.settings.load();
        settings.load();
    }
}
