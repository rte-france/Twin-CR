/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use tokio::sync::mpsc;
use tokio::sync::oneshot;

use super::error::Result;
use super::task::Task;

pub(crate) enum Command {
    Get {
        req_id: String,
        endpoint: String,
        responder: oneshot::Sender<Result<(u16, bytes::Bytes)>>,
    },
    Post {
        req_id: String,
        endpoint: String,
        body: bytes::Bytes,
        responder: oneshot::Sender<Result<(u16, bytes::Bytes)>>,
    },
    Put {
        req_id: String,
        endpoint: String,
        body: bytes::Bytes,
        responder: oneshot::Sender<Result<(u16, bytes::Bytes)>>,
    },
    PutMultipart {
        req_id: String,
        endpoint: String,
        form: reqwest::multipart::Form,
        responder: oneshot::Sender<Result<(u16, bytes::Bytes)>>,
    },
    Delete {
        req_id: String,
        endpoint: String,
        responder: oneshot::Sender<Result<(u16, bytes::Bytes)>>,
    },
    PostMultipart {
        req_id: String,
        endpoint: String,
        form: reqwest::multipart::Form,
        responder: oneshot::Sender<Result<(u16, bytes::Bytes)>>,
    },
    Sse {
        req_id: String,
        endpoint: String,
        event_sender: mpsc::Sender<Result<bytes::Bytes>>,
    },
    GetTasks {
        responder: oneshot::Sender<Vec<Task>>,
    },
    Cancel {
        req_id: String,
    },
}
