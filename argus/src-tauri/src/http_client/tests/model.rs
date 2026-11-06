/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use crate::http_client::types::AllowedEndpoint;
use crate::http_client::utils::client_manager::{ClientManager, ClientState};
use crate::http_client::utils::http_client::HasUrlExt;
use proptest::prelude::*;

#[test]
fn test_client_manager_configuration() {
    let manager = ClientManager::new_with_prefix("TestClient", "test");
    assert_eq!(manager.name, "TestClient");
    assert_eq!(manager.event_prefix, "test");

    let current = manager.client.load();
    assert!(matches!(**current, ClientState::Unconfigured));

    manager.configure("http://localhost:9999");
    let updated = manager.client.load();
    assert!(matches!(**updated, ClientState::Disconnected(_)));
}

#[derive(Debug, Clone, PartialEq)]
enum ExpectedStatus {
    Unconfigured,
    Disconnected { primary_url: String },
}

#[derive(Debug, Clone)]
enum ManagerAction {
    ConfigureSingle(String),
    ConfigureEndpoints(Vec<(String, String)>),
}

proptest! {
    #[test]
    fn prop_client_manager_state_machine(
        actions in prop::collection::vec(
            prop_oneof![
                "[a-z0-9_]{3,8}\\.local".prop_map(|h| ManagerAction::ConfigureSingle(format!("http://{h}"))),
                prop::collection::vec(
                    ("[a-z]{3,6}", "https://[a-z0-9]{3,8}\\.com"),
                    0..4
                ).prop_map(|eps| {
                    ManagerAction::ConfigureEndpoints(
                        eps.into_iter().map(|(a, u)| (a.to_string(), u.to_string())).collect()
                    )
                }),
            ],
            1..25
        )
    ) {
        let manager = ClientManager::new("test_agent");
        let mut expected_model = ExpectedStatus::Unconfigured;

        // Invariant check on initial state
        prop_assert_eq!(&expected_model, &ExpectedStatus::Unconfigured);
        prop_assert!(matches!(**manager.client.load(), ClientState::Unconfigured));

        for action in actions {
            match action {
                ManagerAction::ConfigureSingle(url) => {
                    manager.configure(&url);
                    expected_model = ExpectedStatus::Disconnected { primary_url: url.clone() };

                    let stored_endpoints = manager.endpoints.load();
                    prop_assert_eq!(stored_endpoints.len(), 1);
                    prop_assert_eq!(&stored_endpoints[0].base_url, &url);
                }
                ManagerAction::ConfigureEndpoints(endpoints) => {
                    let allowed: Vec<AllowedEndpoint> = endpoints
                        .iter()
                        .map(|(ep, url)| AllowedEndpoint {
                            endpoint: ep.clone(),
                            base_url: url.clone(),
                        })
                        .collect();

                    let primary_url = allowed.first().map(|e| e.base_url.clone()).unwrap_or_default();
                    manager.configure_endpoints(allowed);
                    expected_model = ExpectedStatus::Disconnected { primary_url };

                    let stored_endpoints = manager.endpoints.load();
                    prop_assert_eq!(stored_endpoints.len(), endpoints.len());
                }
            }

            // Invariant check: compare actual manager state with model
            let current_state = manager.client.load();
            match (&expected_model, &**current_state) {
                (ExpectedStatus::Unconfigured, ClientState::Unconfigured) => {}
                (ExpectedStatus::Disconnected { primary_url }, ClientState::Disconnected(client)) => {
                    prop_assert_eq!(client.url(), primary_url.as_str());
                }
                _ => panic!("Model and actual state diverged: expected {:?}, actual not matching", expected_model),
            }
        }
    }
}
