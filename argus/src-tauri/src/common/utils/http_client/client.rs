/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use serde::{de::DeserializeOwned, Serialize};
use std::marker::PhantomData;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::{mpsc, oneshot, watch};

use crate::common::utils::http_client::HealthStrategy;

use super::actor;
use super::command::Command;
use super::error::{Error, Result};
use super::status::ServerStatus;
use super::task::Task;

mod private {
    pub trait Sealed {}
}
pub trait ClientState: private::Sealed {}

#[derive(Debug)]
pub struct Unconfigured;
#[derive(Debug)]
pub struct Disconnected;
#[derive(Debug)]
pub struct Connected {
    pub status: watch::Receiver<ServerStatus>,
    pub(crate) sender: mpsc::Sender<Command>,
}

// Type-safe pattern
impl private::Sealed for Unconfigured {}
impl ClientState for Unconfigured {}
impl private::Sealed for Disconnected {}
impl ClientState for Disconnected {}
impl private::Sealed for Connected {}
impl ClientState for Connected {}

#[derive(Debug)]
pub struct Client<S: ClientState> {
    pub(crate) url: Option<String>,
    pub(crate) state: S,
}

pub trait HasUrlExt {
    fn url(&self) -> &str;
}

impl Default for Client<Unconfigured> {
    fn default() -> Self {
        Self {
            url: None,
            state: Unconfigured,
        }
    }
}

impl Client<Unconfigured> {
    pub fn with_url(url: impl Into<String>) -> Client<Disconnected> {
        Client {
            url: Some(url.into()),
            state: Disconnected,
        }
    }
}

impl HasUrlExt for Client<Disconnected> {
    fn url(&self) -> &str {
        self.url
            .as_ref()
            .expect("URL must be set in Disconnected state")
    }
}

impl Client<Disconnected> {
    pub async fn connect_with_strategy(
        self,
        strategy: Arc<dyn HealthStrategy>,
    ) -> Result<Client<Connected>> {
        let client = reqwest::Client::builder()
            .pool_max_idle_per_host(100)
            .pool_idle_timeout(Duration::from_secs(90))
            .timeout(Duration::from_secs(60))
            .no_proxy()
            .build()
            .map_err(|e| Error::from_reqwest(e, self.url().to_string()))?;

        let (status_tx, status) = watch::channel(ServerStatus::Connecting);
        let (sender, cmd_rx) = mpsc::channel::<Command>(1024);

        let base_url = self.url().to_string();
        tokio::spawn(async move {
            actor::run_scada_actor(client, base_url, status_tx, cmd_rx, strategy).await;
        });

        Ok(Client {
            url: self.url,
            state: Connected { sender, status },
        })
    }
}

impl HasUrlExt for Client<Connected> {
    fn url(&self) -> &str {
        self.url
            .as_ref()
            .expect("URL must be set in Connected state")
    }
}

pub struct TypedSseReceiver<T> {
    pub req_id: String,
    raw_rx: mpsc::Receiver<Result<bytes::Bytes>>,
    _marker: PhantomData<T>,
}

impl<T: DeserializeOwned> TypedSseReceiver<T> {
    pub async fn recv(&mut self) -> Option<Result<T>> {
        match self.raw_rx.recv().await {
            Some(Ok(bytes)) => {
                let parsed =
                    serde_json::from_slice::<T>(&bytes).map_err(|e| Error::DataFormatError {
                        reason: e.to_string(),
                    });
                Some(parsed)
            }
            Some(Err(e)) => Some(Err(e)),
            None => None,
        }
    }
}

impl Client<Connected> {
    pub fn get_current_status(&self) -> ServerStatus {
        *self.state.status.borrow()
    }

    pub async fn cancel_request(&self, req_id: String) -> Result<()> {
        self.state
            .sender
            .send(Command::Cancel { req_id })
            .await
            .map_err(|_| Error::ActorClosed)
    }

    /// Helper trait to avoid duplicating the send logic
    async fn send_cmd(
        &self,
        req_id: String,
        cmd_builder: impl FnOnce(String, oneshot::Sender<Result<(u16, bytes::Bytes)>>) -> Command,
    ) -> Result<oneshot::Receiver<Result<(u16, bytes::Bytes)>>> {
        let (tx, rx) = oneshot::channel();
        self.state
            .sender
            .send(cmd_builder(req_id.clone(), tx))
            .await
            .map_err(|_| Error::ActorClosed)?;
        Ok(rx)
    }

    pub async fn get(
        &self,
        req_id: String,
        endpoint: impl Into<String>,
    ) -> Result<oneshot::Receiver<Result<(u16, bytes::Bytes)>>> {
        self.send_cmd(req_id, |id, tx| Command::Get {
            req_id: id,
            endpoint: endpoint.into(),
            responder: tx,
        })
        .await
    }

    pub async fn delete(
        &self,
        req_id: String,
        endpoint: impl Into<String>,
    ) -> Result<oneshot::Receiver<Result<(u16, bytes::Bytes)>>> {
        self.send_cmd(req_id, |id, tx| Command::Delete {
            req_id: id,
            endpoint: endpoint.into(),
            responder: tx,
        })
        .await
    }

    pub async fn post<B: Serialize>(
        &self,
        req_id: String,
        endpoint: impl Into<String>,
        body: &B,
    ) -> Result<oneshot::Receiver<Result<(u16, bytes::Bytes)>>> {
        let body_bytes = serde_json::to_vec(body).map_err(|e| Error::DataFormatError {
            reason: e.to_string(),
        })?;
        self.send_cmd(req_id, |id, tx| Command::Post {
            req_id: id,
            endpoint: endpoint.into(),
            body: bytes::Bytes::from(body_bytes),
            responder: tx,
        })
        .await
    }

    pub async fn put<B: Serialize>(
        &self,
        req_id: String,
        endpoint: impl Into<String>,
        body: &B,
    ) -> Result<oneshot::Receiver<Result<(u16, bytes::Bytes)>>> {
        let body_bytes = serde_json::to_vec(body).map_err(|e| Error::DataFormatError {
            reason: e.to_string(),
        })?;
        self.send_cmd(req_id, |id, tx| Command::Put {
            req_id: id,
            endpoint: endpoint.into(),
            body: bytes::Bytes::from(body_bytes),
            responder: tx,
        })
        .await
    }

    pub async fn put_multipart(
        &self,
        req_id: String,
        endpoint: impl Into<String>,
        form: reqwest::multipart::Form,
    ) -> Result<oneshot::Receiver<Result<(u16, bytes::Bytes)>>> {
        self.send_cmd(req_id, |id, tx| Command::PutMultipart {
            req_id: id,
            endpoint: endpoint.into(),
            form,
            responder: tx,
        })
        .await
    }

    pub async fn post_multipart(
        &self,
        req_id: String,
        endpoint: impl Into<String>,
        form: reqwest::multipart::Form,
    ) -> Result<oneshot::Receiver<Result<(u16, bytes::Bytes)>>> {
        self.send_cmd(req_id, |id, tx| Command::PostMultipart {
            req_id: id,
            endpoint: endpoint.into(),
            form,
            responder: tx,
        })
        .await
    }

    pub async fn sse(
        &self,
        req_id: String,
        endpoint: impl Into<String>,
    ) -> Result<mpsc::Receiver<Result<bytes::Bytes>>> {
        let (tx, rx) = mpsc::channel(32);
        let cmd = Command::Sse {
            req_id: req_id.clone(),
            endpoint: endpoint.into(),
            event_sender: tx,
        };
        self.state
            .sender
            .send(cmd)
            .await
            .map_err(|_| Error::ActorClosed)?;
        Ok(rx)
    }

    pub fn disconnect(self) -> Client<Disconnected> {
        Client {
            url: self.url,
            state: Disconnected,
        }
    }

    pub fn parse_standard_json<T: DeserializeOwned>(
        status: u16,
        bytes: &[u8],
        endpoint: impl Into<String>,
    ) -> Result<T> {
        if !(200..300).contains(&status) {
            return Err(Error::HttpError {
                status,
                endpoint: endpoint.into(),
                message: "Request failed".into(),
            });
        }
        serde_json::from_slice(bytes).map_err(|e| Error::DataFormatError {
            reason: e.to_string(),
        })
    }

    pub fn parse_with_api_error<T: DeserializeOwned>(
        status: u16,
        bytes: &[u8],
        endpoint: impl Into<String>,
    ) -> Result<T> {
        if !(200..300).contains(&status) {
            let body_val: serde_json::Value = serde_json::from_slice(bytes).unwrap_or_else(
                |_| serde_json::json!({ "raw": String::from_utf8_lossy(bytes).into_owned() }),
            );
            return Err(Error::ApiError {
                status,
                endpoint: endpoint.into(),
                body: body_val,
            });
        }
        serde_json::from_slice(bytes).map_err(|e| Error::DataFormatError {
            reason: e.to_string(),
        })
    }

    pub async fn get_active_tasks(&self) -> Result<Vec<Task>> {
        let (tx, rx) = oneshot::channel();
        self.state
            .sender
            .send(Command::GetTasks { responder: tx })
            .await
            .map_err(|_| Error::ActorClosed)?;
        rx.await.map_err(|_| Error::ActorClosed)
    }

    pub async fn wait_for_response<T: DeserializeOwned>(
        rx: oneshot::Receiver<Result<(u16, bytes::Bytes)>>,
        endpoint: impl Into<String>,
    ) -> Result<T> {
        let endpoint_str = endpoint.into();
        let actor_res = rx.await.map_err(|_| Error::ActorClosed)?;
        let (status, bytes) = actor_res?;
        Self::parse_standard_json(status, &bytes, endpoint_str)
    }

    pub async fn wait_for_raw_response(
        rx: oneshot::Receiver<Result<(u16, bytes::Bytes)>>,
        endpoint: impl Into<String>,
    ) -> Result<Vec<u8>> {
        let endpoint_str = endpoint.into();
        let actor_res = rx.await.map_err(|_| Error::ActorClosed)?;
        let (status, bytes) = actor_res?;

        if !(200..300).contains(&status) {
            return Err(Error::HttpError {
                status,
                endpoint: endpoint_str,
                message: "Request failed".into(),
            });
        }

        Ok(bytes.to_vec())
    }

    pub async fn listen_sse_typed<T: DeserializeOwned>(
        &self,
        req_id: String,
        endpoint: impl Into<String>,
    ) -> Result<TypedSseReceiver<T>> {
        let raw_rx = self.sse(req_id.clone(), endpoint).await?;
        Ok(TypedSseReceiver {
            req_id,
            raw_rx,
            _marker: PhantomData,
        })
    }
}
