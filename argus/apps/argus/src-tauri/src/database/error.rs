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
    #[error("Database Connection Error: {0}")]
    Connection(String),

    #[error("SQL Query Execution Failed: {0}")]
    QueryExecution(String),

    #[error("Database Migration Failed: {0}")]
    Migration(String),

    #[error("Failed to create app directory: {0}")]
    DirectoryCreation(String),

    #[error("Database query was aborted by user")]
    Aborted,
}

impl From<std::io::Error> for Error {
    fn from(err: std::io::Error) -> Self {
        Self::DirectoryCreation(err.to_string())
    }
}

impl From<sqlx::Error> for Error {
    fn from(err: sqlx::Error) -> Self {
        Self::QueryExecution(err.to_string())
    }
}

impl From<sqlx::migrate::MigrateError> for Error {
    fn from(err: sqlx::migrate::MigrateError) -> Self {
        Self::Migration(err.to_string())
    }
}

pub type Result<T> = std::result::Result<T, Error>;
