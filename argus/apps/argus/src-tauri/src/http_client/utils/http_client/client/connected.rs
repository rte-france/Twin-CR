/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use std::collections::HashMap;
use tokio::sync::{mpsc, oneshot};

use crate::http_client::types::{HttpResponse, TauriHttpResponse};

use super::super::command::Command;
use super::super::error::{Error, Result};
use super::private::Sealed;
use super::{Client, ClientState, HasUrlExt};

#[cfg(test)]
use super::super::task::Task;

#[derive(Debug, Clone)]
pub struct Connected {
    pub sender: mpsc::Sender<Command>,
}

impl Sealed for Connected {}
impl ClientState for Connected {}

impl HasUrlExt for Client<Connected> {
    fn url(&self) -> &str {
        self.url
            .as_ref()
            .expect("URL must be set in Connected state")
    }
}

macro_rules! impl_http_method {
    ($name:ident, $cmd:ident) => {
        pub async fn $name(
            &self,
            req_id: String,
            endpoint: impl Into<String>,
            headers: HashMap<String, String>,
        ) -> Result<oneshot::Receiver<Result<HttpResponse>>> {
            self.send_cmd(req_id, |id, tx| Command::$cmd {
                req_id: id,
                endpoint: endpoint.into(),
                headers,
                responder: tx,
            })
            .await
        }
    };
}

macro_rules! impl_http_method_with_body {
    ($name:ident, $cmd:ident) => {
        pub async fn $name(
            &self,
            req_id: String,
            endpoint: impl Into<String>,
            headers: HashMap<String, String>,
            body: impl Into<bytes::Bytes>,
        ) -> Result<oneshot::Receiver<Result<HttpResponse>>> {
            self.send_cmd(req_id, |id, tx| Command::$cmd {
                req_id: id,
                endpoint: endpoint.into(),
                headers,
                body: body.into(),
                responder: tx,
            })
            .await
        }
    };
}

impl Client<Connected> {
    async fn send_cmd<F>(
        &self,
        req_id: String,
        cmd_builder: F,
    ) -> Result<oneshot::Receiver<Result<HttpResponse>>>
    where
        F: FnOnce(String, oneshot::Sender<Result<HttpResponse>>) -> Command,
    {
        let (tx, rx) = oneshot::channel();

        self.state
            .sender
            .send(cmd_builder(req_id, tx))
            .await
            .map_err(|_| Error::ActorClosed)?;

        Ok(rx)
    }

    impl_http_method!(get, Get);
    impl_http_method!(delete, Delete);
    impl_http_method!(head, Head);
    impl_http_method!(options, Options);
    impl_http_method!(trace, Trace);

    impl_http_method_with_body!(post, Post);
    impl_http_method_with_body!(put, Put);
    impl_http_method_with_body!(patch, Patch);

    pub async fn sse(
        &self,
        req_id: String,
        endpoint: impl Into<String>,
        headers: HashMap<String, String>,
    ) -> Result<mpsc::Receiver<Result<bytes::Bytes>>> {
        let (tx, rx) = mpsc::channel(32);
        self.state
            .sender
            .send(Command::Sse {
                req_id,
                endpoint: endpoint.into(),
                headers,
                event_sender: tx,
            })
            .await
            .map_err(|_| Error::ActorClosed)?;
        Ok(rx)
    }

    pub async fn cancel_request(&self, req_id: String) -> Result<()> {
        self.state
            .sender
            .send(Command::Cancel { req_id })
            .await
            .map_err(|_| Error::ActorClosed)
    }

    pub async fn register_cancel(&self, req_id: &str) -> Result<oneshot::Receiver<()>> {
        let (tx, rx) = oneshot::channel();
        self.state
            .sender
            .send(Command::RegisterCancel {
                req_id: req_id.to_string(),
                cancel_rx_sender: tx,
            })
            .await
            .map_err(|_| Error::ActorClosed)?;
        rx.await.map_err(|_| Error::ActorClosed)
    }

    #[cfg(test)]
    pub async fn get_active_tasks(&self) -> Result<Vec<Task>> {
        let (tx, rx) = oneshot::channel();
        self.state
            .sender
            .send(Command::GetTasks { responder: tx })
            .await
            .map_err(|_| Error::ActorClosed)?;
        rx.await.map_err(|_| Error::ActorClosed)
    }

    pub async fn wait_for_response(
        rx: oneshot::Receiver<Result<HttpResponse>>,
    ) -> Result<TauriHttpResponse> {
        let http_response = rx.await.map_err(|_| Error::ActorClosed)??;

        let status = http_response.status;
        let headers = http_response.headers;
        let mut body_rx = http_response.body_rx;

        let mut body = Vec::new();
        while let Some(chunk_result) = body_rx.recv().await {
            let chunk = chunk_result?;
            body.extend_from_slice(&chunk);
        }

        Ok(TauriHttpResponse {
            status,
            headers,
            body,
        })
    }
}
