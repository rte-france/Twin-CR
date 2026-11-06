/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use arc_swap::{ArcSwap, Guard};
use log::{info, warn};
use std::sync::Arc;
use tauri::Emitter;

use crate::common::utils::{
    http_client::{
        Client, Connected, Disconnected, HasUrlExt, HealthStrategy, StandardHealthCheck,
    },
    server_manager::state::ServerState,
};

use super::error::{Error, Result};

pub struct ServerManager {
    pub name: String,
    pub event_prefix: String,
    pub client: ArcSwap<ServerState>,
}

impl ServerManager {
    pub fn new(name: &str, event_prefix: &str) -> Arc<Self> {
        Arc::new(Self {
            name: name.to_string(),
            event_prefix: event_prefix.to_string(),
            client: ArcSwap::from_pointee(ServerState::Unconfigured),
        })
    }

    pub fn get_connected(client_arc: &Arc<ServerState>) -> Result<&Client<Connected>> {
        match &**client_arc {
            ServerState::Connected(c) => Ok(c),
            _ => Err(Error::NotConnected),
        }
    }

    pub fn configure(&self, url: impl Into<String>) {
        let new_client = Client::with_url(url);
        self.client
            .store(Arc::new(ServerState::Disconnected(new_client)));
        info!(
            "Backend '{}' URL configured, ready for connection.",
            self.name
        );
    }

    pub async fn connect(&self, app_handle: tauri::AppHandle) -> Result<()> {
        let strategy = Arc::new(StandardHealthCheck::new("/health"));
        self.connect_with_strategy(strategy, app_handle).await
    }

    pub async fn connect_with_strategy(
        &self,
        strategy: Arc<dyn HealthStrategy>,
        app_handle: tauri::AppHandle,
    ) -> Result<()> {
        let current_arc = self.client.load();

        if let ServerState::Disconnected(ref client) = **current_arc {
            let url = client.url().to_string();
            let temp_client = Client::with_url(&url);

            self.start_connect(url, temp_client, strategy, app_handle)
                .await
        } else {
            Err(Error::InvalidState(
                "System must be configured with a URL before connecting.".into(),
            ))
        }
    }

    async fn start_connect(
        &self,
        url: String,
        temp_client: Client<Disconnected>,
        strategy: Arc<dyn HealthStrategy>,
        app_handle: tauri::AppHandle,
    ) -> Result<()> {
        match temp_client.connect_with_strategy(strategy).await {
            Ok(connected) => {
                info!("Starting connection to backend '{}' at {}", self.name, url);

                let mut status_rx = connected.state.status.clone();
                let handle = app_handle.clone();
                let event_name = format!("{}-status-update", self.event_prefix);

                tokio::spawn(async move {
                    let _ = handle.emit(&event_name, *status_rx.borrow());

                    while status_rx.changed().await.is_ok() {
                        let new_status = *status_rx.borrow();
                        let _ = handle.emit(&event_name, new_status);
                    }
                });

                let new_state = Arc::new(ServerState::Connected(connected));

                self.client.store(new_state);

                Ok(())
            }
            Err(e) => {
                warn!("Failed to connect to backend '{}': {:?}", self.name, e);
                Err(e.into())
            }
        }
    }
}
