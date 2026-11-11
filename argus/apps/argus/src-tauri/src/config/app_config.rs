/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use directories::ProjectDirs;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

const DEFAULT_CONFIG: &str = include_str!("../../config.json");

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    pub keycloak_url: String,
    pub keycloak_realm: String,
    pub keycloak_client_id: String,
    pub session_manager_url: String,
    pub lobby_url: Option<String>,
    pub environment: String,
    pub api_url: String,
    pub api_token: String,
    pub oauth_dev_port: i32,
}

fn config_path() -> PathBuf {
    let proj_dirs = ProjectDirs::from("com", "twincr", "com.twincr.argus")
        .expect("Could not find config folder");

    proj_dirs.config_dir().join("config.json")
}

pub fn load_config() -> AppConfig {
    let path = config_path();

    if !path.exists() {
        std::fs::create_dir_all(path.parent().unwrap()).unwrap();

        std::fs::write(&path, DEFAULT_CONFIG)
            .unwrap_or_else(|e| panic!("Could not write config file '{}': {}", path.display(), e));
    }

    let content = std::fs::read_to_string(&path)
        .unwrap_or_else(|e| panic!("Could not read config file '{}': {}", path.display(), e));

    // A config.json written by an older Argus lacks the fields added since:
    // take those from the bundled config.json instead of refusing to start.
    let parsed = serde_json::from_str::<serde_json::Value>(&content).and_then(|mut user| {
        let defaults: serde_json::Value =
            serde_json::from_str(DEFAULT_CONFIG).expect("Bundled config.json is not valid JSON");
        if let (Some(user_fields), serde_json::Value::Object(default_fields)) =
            (user.as_object_mut(), defaults)
        {
            for (key, value) in default_fields {
                user_fields.entry(key).or_insert(value);
            }
        }
        serde_json::from_value::<AppConfig>(user)
    });

    match parsed {
        Ok(config) => config,
        Err(error) => {
            panic!(
                "\n\
                ========================================\n\
                INVALID CONFIGURATION\n\
                File : {}\n\
                The config.json file exists but doesn't match AppConfig structure\n\
                Error : {}\n\
                See src-tauri/config.json file\n\
                ========================================\n",
                path.display(),
                error
            );
        }
    }
}
