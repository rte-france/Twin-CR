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
    #[error("HTTP client initialization failed: {0}")]
    ClientInit(String),

    #[error("Authentication service unreachable: {0}")]
    Network(String),

    #[error("Authentication refused: {0}")]
    AuthenticationRefused(String),

    #[error("Failed to read response body: {0}")]
    ResponseBody(String),
}

impl From<reqwest::Error> for Error {
    fn from(err: reqwest::Error) -> Self {
        let mut details = err.to_string();
        let mut source = std::error::Error::source(&err);
        while let Some(cause) = source {
            details.push_str(&format!(" -> {cause}"));
            source = std::error::Error::source(cause);
        }
        Error::Network(details)
    }
}

pub type Result<T> = std::result::Result<T, Error>;
