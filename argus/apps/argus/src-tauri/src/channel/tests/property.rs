/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use crate::channel::manager::{ChannelGuard, ChannelTaskManager};
use proptest::prelude::*;
use std::sync::Arc;

proptest! {
    #[test]
    fn prop_channel_guard_raii_cleanup(
        channel_count in 1usize..15
    ) {
        let rt = tokio::runtime::Runtime::new().unwrap();
        rt.block_on(async {
            let manager = Arc::new(ChannelTaskManager::new().await);
            let mut ids = Vec::new();

            // Create channels and wrap half of them in ChannelGuard
            for _ in 0..channel_count {
                let channel = tauri::ipc::Channel::<()>::new(|_| Ok(()));
                let id = channel.id();
                let _rx = manager.register(&channel);
                ids.push(id);
            }

            for &id in &ids {
                prop_assert!(manager.is_alive(id));
            }

            // RAII Scope: Guards created and dropped
            {
                let _guards: Vec<_> = ids
                    .iter()
                    .map(|&channel_id| ChannelGuard {
                        channel_id,
                        manager: manager.clone(),
                    })
                    .collect();

                // While in scope, all must still be alive
                for &id in &ids {
                    prop_assert!(manager.is_alive(id));
                }
            } // _guards dropped here

            // Invariant: after dropping ChannelGuard, all channels must be unregistered automatically
            for &id in &ids {
                prop_assert!(!manager.is_alive(id));
            }

            Ok(())
        })?;
    }
}
