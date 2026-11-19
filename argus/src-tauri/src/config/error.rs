use serde::Serialize;
use thiserror::Error;

#[derive(Debug, Error, Serialize)]
#[serde(tag = "_tag", content = "message")]
pub enum Error {
    #[error("Serialization Error: {0}")]
    Json(String),
    #[error(transparent)]
    Settings(#[from] super::settings::error::Error),
}

impl From<serde_json::Error> for Error {
    fn from(err: serde_json::Error) -> Self {
        Self::Json(err.to_string())
    }
}

pub type Result<T> = std::result::Result<T, Error>;
