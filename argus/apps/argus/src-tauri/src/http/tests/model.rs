/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use crate::http::manager::HttpManager;
use proptest::prelude::*;
use std::collections::HashMap;

#[derive(Clone, Debug)]
enum ManagerOp {
    Register(String),
    Query(String),
}

proptest! {
    #[test]
    fn prop_http_manager_model_consistency(
        ops in prop::collection::vec(
            prop_oneof![
                "[a-z0-9_]{1,8}".prop_map(ManagerOp::Register),
                "[a-z0-9_]{1,8}".prop_map(ManagerOp::Query),
            ],
            1..30
        )
    ) {
        let rt = tokio::runtime::Runtime::new().unwrap();
        rt.block_on(async {
            let manager = HttpManager::new();
            let mut model = HashMap::new();

            for op in ops {
                match op {
                    ManagerOp::Register(name) => {
                        let client = crate::http_client::utils::client_manager::manager::ClientManager::new(&name);
                        manager.clients.write().await.insert(name.clone(), client);
                        model.insert(name, ());
                    }
                    ManagerOp::Query(name) => {
                        let actual = manager.get_client(&name).await;
                        assert_eq!(actual.is_some(), model.contains_key(&name));
                    }
                }
            }

            let mut registered = manager.get_registered_client_ids().await;
            registered.sort();
            let mut expected: Vec<_> = model.into_keys().collect();
            expected.sort();
            assert_eq!(registered, expected);
        });
    }
}
