/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use serde::Serialize;
use thiserror::Error;

#[derive(Debug, Error, Serialize)]
#[serde(tag = "_tag", content = "message")]
pub enum Error {
    #[error("Network request failed for {endpoint}: {reason}")]
    NetworkFailure { endpoint: String, reason: String },

    #[error("Data formatting/parsing failed: {reason}")]
    DataFormatError { reason: String },

    #[error("API request failed with status {status}: {body}")]
    ApiError { status: u16, body: String },

    #[error("Serialization failed: {0}")]
    SerializationError(String),

    #[allow(unused)]
    #[error("Http client is not connected")]
    NotConnected,

    #[error("Internal HTTP Actor closed unexpectedly")]
    ActorClosed,
}

impl Error {
    pub fn from_reqwest(err: reqwest::Error, endpoint: impl Into<String>) -> Self {
        Self::NetworkFailure {
            endpoint: endpoint.into(),
            reason: err.to_string(),
        }
    }

    #[allow(unused)]
    pub fn from_serde(err: serde_json::Error) -> Self {
        Self::DataFormatError {
            reason: err.to_string(),
        }
    }
}

pub type Result<T> = std::result::Result<T, Error>;
