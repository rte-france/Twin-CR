/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use serde::Serialize;
use thiserror::Error;

#[derive(Debug, Serialize, Error)]
#[serde(tag = "_tag", content = "message")]
pub enum Error {
    #[error(transparent)]
    ServerManager(#[from] crate::common::utils::server_manager::Error),

    #[error("HTTP error: {0}")]
    HttpClient(crate::common::utils::http_client::Error),

    #[error("Database error: {0}")]
    Database(#[from] crate::database::Error),
}

pub type Result<T> = std::result::Result<T, Error>;
