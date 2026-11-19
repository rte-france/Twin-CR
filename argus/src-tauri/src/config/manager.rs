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
