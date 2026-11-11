/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

mod connected;
mod disconnected;
mod unconfigured;

pub use connected::Connected;
pub use disconnected::Disconnected;

// Type safe pattern: sealed implementation only in actor crate
mod private {
    pub trait Sealed {}
}
pub trait ClientState: private::Sealed {}

#[derive(Debug, Clone)]
pub struct Client<S: ClientState> {
    pub url: Option<String>,
    pub state: S,
}

pub trait HasUrlExt {
    fn url(&self) -> &str;
}
