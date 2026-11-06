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
    #[error(transparent)]
    Settings(#[from] super::settings::error::Error),
    #[error(transparent)]
    Vault(#[from] super::vault::error::Error),
}

pub type Result<T> = std::result::Result<T, Error>;
