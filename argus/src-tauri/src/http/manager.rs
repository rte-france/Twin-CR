/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use std::collections::HashMap;
use std::sync::Arc;
use tauri::{AppHandle, Manager};
use tokio::sync::RwLock;

use super::resolver::ArcEndpointResolver;
use crate::{
    config::manager::ConfigManager,
    http_client::{types::AllowedEndpoint, utils::client_manager::manager::ClientManager},
};

pub struct HttpManager {
    pub(crate) clients: RwLock<HashMap<String, Arc<ClientManager>>>,
    resolver: Option<ArcEndpointResolver>,
}

impl HttpManager {
    #[cfg(test)]
    pub(crate) fn new() -> Arc<Self> {
        Self::with_resolver(None)
    }

    pub fn with_resolver(resolver: Option<ArcEndpointResolver>) -> Arc<Self> {
        Arc::new(Self {
            clients: RwLock::new(HashMap::new()),
            resolver,
        })
    }

    pub async fn register_client(
        &self,
        name: &str,
        endpoints: Vec<AllowedEndpoint>,
        app_handle: AppHandle,
    ) -> Arc<ClientManager> {
        let client = ClientManager::new(name);
        client.configure_endpoints(endpoints);

        if let Err(e) = client.connect(app_handle).await {
            log::error!(target: "HttpManager", "Failed to auto-connect client '{}': {:?}", name, e);
        }

        self.clients
            .write()
            .await
            .insert(name.to_string(), client.clone());
        client
    }

    pub async fn get_or_resolve_client(
        &self,
        name: &str,
        app_handle: &AppHandle,
    ) -> Result<Arc<ClientManager>, String> {
        if let Some(client) = self.get_client(name).await {
            return Ok(client);
        }

        // Auto-provision direct client without endpoints for direct HTTP/HTTPS firehose
        if name == "direct" {
            let client = self
                .register_client(name, Vec::new(), app_handle.clone())
                .await;
            return Ok(client);
        }

        if let Some(ref resolver) = self.resolver {
            let endpoints = resolver.resolve_endpoints(name).await?;
            let client = self
                .register_client(name, endpoints, app_handle.clone())
                .await;
            return Ok(client);
        }

        Err(format!(
            "HTTP client '{}' not found and no resolver configured",
            name
        ))
    }
    pub async fn get_registered_client_ids(&self) -> Vec<String> {
        let clients_guard = self.clients.read().await;
        clients_guard.keys().cloned().collect()
    }

    pub async fn get_client(&self, name: &str) -> Option<Arc<ClientManager>> {
        self.clients.read().await.get(name).cloned()
    }

    pub fn start_proxy_watcher(self_arc: Arc<Self>, app_handle: AppHandle) {
        let config_manager = app_handle.state::<ConfigManager>();
        let mut settings_rx = config_manager.settings.load().rx.clone();

        tokio::spawn(async move {
            let mut previous_config = {
                let s = settings_rx.borrow();
                (s.proxy.clone(), s.no_proxy.clone())
            };

            while settings_rx.changed().await.is_ok() {
                let new_config = {
                    let s = settings_rx.borrow();
                    (s.proxy.clone(), s.no_proxy.clone())
                };

                if new_config != previous_config {
                    log::info!(target: "HttpManager", "Proxy configuration changed! Triggering reconnect for all clients...");

                    let clients_map = self_arc.clients.read().await;
                    for (name, client) in clients_map.iter() {
                        log::info!(target: "HttpManager", "Reconnecting client: {}", name);
                        if let Err(e) = client.reconnect(app_handle.clone()).await {
                            log::error!(target: "HttpManager", "Failed to reconnect {}: {:?}", name, e);
                        }
                    }

                    previous_config = new_config;
                }
            }
        });
    }
}
