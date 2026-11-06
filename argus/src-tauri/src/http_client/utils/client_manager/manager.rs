/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use arc_swap::ArcSwap;
use std::sync::Arc;
use tauri::{Emitter, Manager};

use crate::{
    config::manager::ConfigManager,
    http_client::{
        types::AllowedEndpoint,
        utils::{
            client_manager::ClientState,
            http_client::{Client, Connected, Disconnected, HasUrlExt},
        },
    },
};

use super::error::{Error, Result};

pub struct ClientManager {
    pub name: String,
    pub event_prefix: String,
    pub client: ArcSwap<ClientState>,
    pub endpoints: ArcSwap<Vec<AllowedEndpoint>>,
}

impl ClientManager {
    pub fn new(name: &str) -> Arc<Self> {
        let prefix = name.to_lowercase();
        Arc::new(Self {
            name: name.to_string(),
            event_prefix: prefix,
            client: ArcSwap::from_pointee(ClientState::Unconfigured),
            endpoints: ArcSwap::from_pointee(Vec::new()),
        })
    }

    #[cfg(test)]
    pub fn new_with_prefix(name: &str, event_prefix: &str) -> Arc<Self> {
        Arc::new(Self {
            name: name.to_string(),
            event_prefix: event_prefix.to_string(),
            client: ArcSwap::from_pointee(ClientState::Unconfigured),
            endpoints: ArcSwap::from_pointee(Vec::new()),
        })
    }

    pub fn get_connected(client_arc: &Arc<ClientState>) -> Result<Arc<Client<Connected>>> {
        match &**client_arc {
            ClientState::Connected(c) => Ok(Arc::new(c.clone())),
            _ => Err(Error::NotConnected),
        }
    }

    #[cfg(test)]
    pub fn configure(&self, url: impl Into<String>) {
        let url_str = url.into();
        let endpoints = vec![AllowedEndpoint {
            endpoint: "/".to_string(),
            base_url: url_str.clone(),
        }];
        self.endpoints.store(Arc::new(endpoints));

        let new_client = Client::with_url(url_str);
        self.client
            .store(Arc::new(ClientState::Disconnected(new_client)));

        log::info!(
            target: "ClientManager",
            "Backend '{}' configured with URL, ready for connection.",
            self.name
        );
    }

    pub fn configure_endpoints(&self, endpoints: Vec<AllowedEndpoint>) {
        self.endpoints.store(Arc::new(endpoints.clone()));

        let primary_url = endpoints
            .first()
            .map(|e| e.base_url.clone())
            .unwrap_or_default();

        let new_client = Client::with_url(primary_url);
        self.client
            .store(Arc::new(ClientState::Disconnected(new_client)));

        log::info!(
            target: "ClientManager",
            "Backend '{}' endpoints configured, ready for connection.",
            self.name
        );
    }

    pub async fn connect(&self, app_handle: tauri::AppHandle) -> Result<()> {
        let current_arc = self.client.load();

        if let ClientState::Disconnected(ref client) = **current_arc {
            let url = client.url().to_string();
            let temp_client = Client::with_url(&url);

            self.start_connect(url, temp_client, app_handle).await
        } else {
            Err(Error::InvalidState(
                "System must be configured with endpoints/URL before connecting.".into(),
            ))
        }
    }

    async fn start_connect(
        &self,
        url: String,
        temp_client: Client<Disconnected>,
        app_handle: tauri::AppHandle,
    ) -> Result<()> {
        let (proxy, no_proxy) = app_handle
            .try_state::<ConfigManager>()
            .map(|config| {
                let settings = config.settings.load().load();
                (settings.proxy.clone(), settings.no_proxy.clone())
            })
            .unwrap_or((None, None));

        match temp_client
            .connect(self.name.clone(), app_handle.clone(), proxy, no_proxy)
            .await
        {
            Ok(connected) => {
                log::info!(target:"ClientManager", "Starting connection to backend '{}' at {}", self.name, url);

                let event_name = format!("{}-status-update", self.event_prefix);
                let _ = app_handle.emit(&event_name, "Connected");

                let new_state = Arc::new(ClientState::Connected(connected));
                self.client.store(new_state);

                Ok(())
            }
            Err(e) => {
                log::warn!(target: "ClientManager", "Failed to connect to backend '{}': {:?}", self.name, e);
                Err(e.into())
            }
        }
    }

    pub async fn reconnect(&self, app_handle: tauri::AppHandle) -> Result<()> {
        let current_state = self.client.load();

        let url = match &**current_state {
            ClientState::Connected(c) => c.url().to_string(),
            ClientState::Disconnected(c) => c.url().to_string(),
            ClientState::Unconfigured => {
                return Err(Error::InvalidState(
                    "Cannot reconnect an unconfigured client.".into(),
                ));
            }
        };

        log::info!(
            target: "ClientManager",
            "Reconnecting backend '{}' to {} with new proxy settings...",
            self.name,
            url
        );

        let disconnected_client = Client::with_url(&url);
        self.client
            .store(Arc::new(ClientState::Disconnected(disconnected_client)));

        self.connect(app_handle).await
    }
}
