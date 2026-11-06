/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use tauri::ipc::Channel;
use tokio::sync::oneshot;

#[derive(Default, Clone)]
pub struct ChannelTaskManager {
    senders: Arc<Mutex<HashMap<u32, oneshot::Sender<()>>>>,
}

impl ChannelTaskManager {
    pub async fn new() -> Self {
        Self::default()
    }

    pub fn register<T>(&self, channel: &Channel<T>) -> oneshot::Receiver<()> {
        let (tx, rx) = oneshot::channel();
        let id = channel.id();

        let mut map_guard = match self.senders.lock() {
            Ok(guard) => guard,
            Err(poisoned) => {
                log::warn!(target: "ChannelGC", "Mutex poisoned (recovering).");
                poisoned.into_inner()
            }
        };

        map_guard.insert(id, tx);
        rx
    }

    pub fn unregister(&self, channel_id: u32) -> Option<oneshot::Sender<()>> {
        let mut map_guard = match self.senders.lock() {
            Ok(guard) => guard,
            Err(poisoned) => {
                log::warn!(target: "ChannelGC", "Mutex poisoned during cleanup.");
                poisoned.into_inner()
            }
        };

        map_guard.remove(&channel_id)
    }

    #[allow(dead_code)]
    pub fn is_alive(&self, channel_id: u32) -> bool {
        match self.senders.lock() {
            Ok(map_guard) => map_guard.contains_key(&channel_id),
            Err(poisoned) => poisoned.into_inner().contains_key(&channel_id),
        }
    }
}

pub struct ChannelGuard {
    pub channel_id: u32,
    pub manager: Arc<ChannelTaskManager>,
}

impl Drop for ChannelGuard {
    fn drop(&mut self) {
        log::debug!(target: "ChannelGC", "Auto-cleanup for channel {} with RAII", self.channel_id);
        self.manager.unregister(self.channel_id);
    }
}
