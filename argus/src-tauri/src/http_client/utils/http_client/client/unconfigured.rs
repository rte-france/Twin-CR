/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use super::disconnected::Disconnected;
use super::private::Sealed;
use super::{Client, ClientState};

#[derive(Debug, Clone)]
pub struct Unconfigured;

// Type-safe pattern
impl Sealed for Unconfigured {}
impl ClientState for Unconfigured {}

// By default Client is unconfigured
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
