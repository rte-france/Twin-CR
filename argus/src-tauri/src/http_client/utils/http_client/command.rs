/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use std::collections::HashMap;
use tokio::sync::mpsc;
use tokio::sync::oneshot;

use crate::http_client::types::HttpResponse;

use super::error::Result;
use super::task::Task;

pub enum Command {
    Get {
        req_id: String,
        endpoint: String,
        headers: HashMap<String, String>,
        responder: oneshot::Sender<Result<HttpResponse>>,
    },
    Post {
        req_id: String,
        endpoint: String,
        headers: HashMap<String, String>,
        body: bytes::Bytes,
        responder: oneshot::Sender<Result<HttpResponse>>,
    },
    Put {
        req_id: String,
        endpoint: String,
        headers: HashMap<String, String>,
        body: bytes::Bytes,
        responder: oneshot::Sender<Result<HttpResponse>>,
    },
    Delete {
        req_id: String,
        endpoint: String,
        headers: HashMap<String, String>,
        responder: oneshot::Sender<Result<HttpResponse>>,
    },
    Patch {
        req_id: String,
        endpoint: String,
        headers: HashMap<String, String>,
        body: bytes::Bytes,
        responder: oneshot::Sender<Result<HttpResponse>>,
    },
    Head {
        req_id: String,
        endpoint: String,
        headers: HashMap<String, String>,
        responder: oneshot::Sender<Result<HttpResponse>>,
    },
    Options {
        req_id: String,
        endpoint: String,
        headers: HashMap<String, String>,
        responder: oneshot::Sender<Result<HttpResponse>>,
    },
    Trace {
        req_id: String,
        endpoint: String,
        headers: HashMap<String, String>,
        responder: oneshot::Sender<Result<HttpResponse>>,
    },
    Sse {
        req_id: String,
        endpoint: String,
        headers: HashMap<String, String>,
        event_sender: mpsc::Sender<Result<bytes::Bytes>>,
    },
    #[allow(dead_code)]
    GetTasks {
        responder: oneshot::Sender<Vec<Task>>,
    },
    Cancel {
        req_id: String,
    },
    RegisterCancel {
        req_id: String,
        cancel_rx_sender: oneshot::Sender<oneshot::Receiver<()>>,
    },
}
