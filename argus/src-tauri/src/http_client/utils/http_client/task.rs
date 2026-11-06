/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use serde::Serialize;
use tokio::sync::oneshot;

#[derive(Clone, Serialize)]
pub enum Method {
    GET,
    POST,
    PUT,
    PATCH,
    DELETE,
    HEAD,
    OPTIONS,
    TRACE,
    SSE,
}

#[derive(Clone, Serialize)]
pub struct Task {
    pub req_id: String,
    pub method: Method,
    pub endpoint: String,
}

pub(crate) struct ActiveTask {
    pub task: Task,
    pub cancel_tx: oneshot::Sender<()>,
}
