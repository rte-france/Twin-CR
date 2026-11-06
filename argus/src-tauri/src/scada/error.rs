/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use serde::Serialize;
use serde_json::Value;
use thiserror::Error;

#[derive(Debug, Error, Serialize)]
#[serde(tag = "_tag", content = "message")]
pub enum Error {
    #[error(transparent)]
    ServerManager(#[from] crate::common::utils::server_manager::Error),

    #[error(transparent)]
    DatabaseManager(#[from] crate::database::Error),

    #[error("API Error {status}: {body}")]
    ApiError { status: u16, body: Value },

    #[error("HTTP error: {message}")]
    HttpClient { message: String },

    #[error("Invalid state: {0}")]
    InvalidState(String),
}

impl From<crate::common::utils::http_client::Error> for Error {
    fn from(err: crate::common::utils::http_client::Error) -> Self {
        match err {
            crate::common::utils::http_client::Error::ApiError { status, body, .. } => {
                Error::ApiError { status, body }
            }
            other => Error::HttpClient {
                message: other.to_string(),
            },
        }
    }
}

pub type Result<T> = std::result::Result<T, Error>;
