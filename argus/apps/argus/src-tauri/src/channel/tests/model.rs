/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use crate::channel::manager::ChannelTaskManager;
use proptest::prelude::*;
use std::collections::HashMap;
use tokio::sync::oneshot;

#[derive(Clone, Debug)]
enum ChannelOp {
    RegisterNew,
    UnregisterExisting(usize), // Index among currently active channels
    CheckRandomId(u32),
}

proptest! {
    #![proptest_config(ProptestConfig::with_cases(30))]
    #[test]
    fn prop_channel_manager_real_cancellation_lifecycle(
        ops in prop::collection::vec(
            prop_oneof![
                Just(ChannelOp::RegisterNew),
                Just(ChannelOp::RegisterNew),
                (0usize..10).prop_map(ChannelOp::UnregisterExisting),
                (1u32..50).prop_map(ChannelOp::CheckRandomId),
            ],
            5..30
        )
    ) {
        let rt = tokio::runtime::Runtime::new().unwrap();
        rt.block_on(async {
            let manager = ChannelTaskManager::new().await;

            // Model: maps real channel_id to its cancellation receiver
            let mut active_channels: HashMap<u32, oneshot::Receiver<()>> = HashMap::new();
            let mut registered_ids: Vec<u32> = Vec::new();

            for op in ops {
                match op {
                    ChannelOp::RegisterNew => {
                        let channel = tauri::ipc::Channel::<()>::new(|_| Ok(()));
                        let id = channel.id();
                        let cancel_rx = manager.register(&channel);

                        // Invariant: channel must be alive
                        prop_assert!(manager.is_alive(id));

                        active_channels.insert(id, cancel_rx);
                        registered_ids.push(id);
                    }
                    ChannelOp::UnregisterExisting(idx) => {
                        if !registered_ids.is_empty() {
                            let chosen_idx = idx % registered_ids.len();
                            let target_id = registered_ids.remove(chosen_idx);

                            let cancel_rx = active_channels.remove(&target_id).unwrap();
                            let tx = manager.unregister(target_id);

                            // Invariant 1: unregister() must return the sender
                            prop_assert!(tx.is_some());

                            // Invariant 2: manager must no longer consider it alive
                            prop_assert!(!manager.is_alive(target_id));

                            // Invariant 3: cancellation must notify the receiver
                            if let Some(sender) = tx {
                                let _ = sender.send(());
                                prop_assert!(cancel_rx.await.is_ok(), "Receiver must receive the cancellation signal");
                            }
                        }
                    }
                    ChannelOp::CheckRandomId(any_id) => {
                        let is_actually_alive = manager.is_alive(any_id);
                        let expected = active_channels.contains_key(&any_id);
                        prop_assert_eq!(is_actually_alive, expected);
                    }
                }
            }

            // Invariant 4: all channels remaining in model must be alive
            for &id in active_channels.keys() {
                prop_assert!(manager.is_alive(id));
            }

            // Cleanup: unregister everything and verify zero remain alive
            for id in active_channels.into_keys() {
                manager.unregister(id);
                prop_assert!(!manager.is_alive(id));
            }

            Ok(())
        })?;
    }
}
