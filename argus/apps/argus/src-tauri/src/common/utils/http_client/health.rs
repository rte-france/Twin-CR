/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use async_trait::async_trait;
use log::{error, warn};
use reqwest::Client;

use super::actor;
use super::status::ServerStatus;

#[async_trait]
pub trait HealthStrategy: Send + Sync + 'static {
    async fn check(&self, client: &Client, base_url: &str) -> ServerStatus;
}

pub struct StandardHealthCheck {
    pub endpoint: String,
}

impl StandardHealthCheck {
    pub fn new(endpoint: impl Into<String>) -> Self {
        Self {
            endpoint: endpoint.into(),
        }
    }
}

#[async_trait]
impl HealthStrategy for StandardHealthCheck {
    async fn check(&self, client: &Client, base_url: &str) -> ServerStatus {
        let url = actor::build_api_url(base_url, &self.endpoint);

        match client.get(&url).send().await {
            Ok(res) if res.status().is_success() => ServerStatus::Healthy,
            Ok(res) => {
                warn!("Server reported degraded state: {}", res.status());
                ServerStatus::Degraded(res.status().as_u16())
            }
            Err(e) => {
                error!("Network communication failure: {}", e);
                ServerStatus::Disconnected
            }
        }
    }
}
