/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use crate::common::utils::http_client::{Client, Connected, Disconnected};

pub enum ServerState {
    Unconfigured,
    Disconnected(Client<Disconnected>),
    Connected(Client<Connected>),
}
