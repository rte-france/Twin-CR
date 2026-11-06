/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use super::error::Result;
use serde_json::Value;
use tokio::sync::oneshot;

pub enum DbCommand {
    Execute {
        req_id: String,
        query: String,
        responder: oneshot::Sender<Result<u64>>,
    },
    Select {
        req_id: String,
        query: String,
        responder: oneshot::Sender<Result<Vec<Value>>>,
    },
    Cancel {
        req_id: String,
    },
}
