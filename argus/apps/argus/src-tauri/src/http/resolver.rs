/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use async_trait::async_trait;
use std::sync::Arc;

use crate::http_client::types::AllowedEndpoint;

#[async_trait]
pub(crate) trait EndpointResolver: Send + Sync {
    async fn resolve_endpoints(&self, client_id: &str) -> Result<Vec<AllowedEndpoint>, String>;
}

pub type ArcEndpointResolver = Arc<dyn EndpointResolver>;
