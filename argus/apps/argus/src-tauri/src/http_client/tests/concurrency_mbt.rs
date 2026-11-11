/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use proptest::prelude::*;
use std::collections::{HashMap, HashSet};
use std::time::Duration;
use wiremock::matchers::{method, path};
use wiremock::{Mock, MockServer, ResponseTemplate};

use crate::http_client::utils::http_client::actor::run_http_client_actor;
use crate::http_client::utils::http_client::client::{Client, Connected};
use crate::http_client::utils::http_client::error::{Error, Result};

async fn collect_body(
    rx: &mut tokio::sync::mpsc::Receiver<Result<bytes::Bytes>>,
) -> Result<Vec<u8>> {
    let mut bytes = Vec::new();
    while let Some(chunk_res) = rx.recv().await {
        bytes.extend_from_slice(&chunk_res?);
    }
    Ok(bytes)
}

fn setup_test_actor(base_url: &str) -> Client<Connected> {
    let (cmd_tx, cmd_rx) = tokio::sync::mpsc::channel(128);
    let reqwest_client = reqwest::Client::builder()
        .timeout(Duration::from_secs(5))
        .build()
        .expect("Failed to build reqwest client");
    let client = reqwest_middleware::ClientBuilder::new(reqwest_client).build();

    let url = base_url.to_string();
    tokio::spawn(run_http_client_actor(client, url.clone(), cmd_rx));

    Client {
        url: Some(url),
        state: Connected { sender: cmd_tx },
    }
}

#[derive(Clone, Debug)]
enum RequestSpeed {
    Fast, // Responds in ~5ms
    Slow, // Responds in ~150ms
}

#[derive(Clone, Debug)]
enum Action {
    Spawn { id: u8, speed: RequestSpeed },
    Cancel(u8),
}

proptest! {
    #![proptest_config(ProptestConfig::with_cases(8))]
    #[test]
    fn prop_real_async_concurrency_race_and_cancellation(
        actions in prop::collection::vec(
            prop_oneof![
                (0u8..6).prop_map(|id| Action::Spawn { id, speed: RequestSpeed::Fast }),
                (0u8..6).prop_map(|id| Action::Spawn { id, speed: RequestSpeed::Slow }),
                (0u8..6).prop_map(Action::Cancel),
            ],
            8..20
        )
    ) {
        let rt = tokio::runtime::Runtime::new().unwrap();
        rt.block_on(async {
            let server = MockServer::start().await;

            // Fast route
            Mock::given(method("GET"))
                .and(path("/fast"))
                .respond_with(
                    ResponseTemplate::new(200)
                        .set_body_bytes(b"FAST_PAYLOAD")
                )
                .mount(&server)
                .await;

            // Slow route
            Mock::given(method("GET"))
                .and(path("/slow"))
                .respond_with(
                    ResponseTemplate::new(200)
                        .set_delay(Duration::from_millis(150))
                        .set_body_bytes(b"SLOW_PAYLOAD")
                )
                .mount(&server)
                .await;

            let client = setup_test_actor(&server.uri());

            // Model: tracks expected state of each request
            // - true if actively cancelled
            // - false if not cancelled (must complete with expected payload)
            let mut cancelled_ids = HashSet::new();
            let mut active_receivers = HashMap::new();
            let mut expected_payload = HashMap::new();

            for action in actions {
                match action {
                    Action::Spawn { id, speed } => {
                        let req_id = format!("req-{id}");
                        let (endpoint, payload) = match speed {
                            RequestSpeed::Fast => ("/fast", "FAST_PAYLOAD"),
                            RequestSpeed::Slow => ("/slow", "SLOW_PAYLOAD"),
                        };

                        if let Ok(rx) = client.get(req_id.clone(), endpoint, HashMap::new()).await {
                            cancelled_ids.remove(&req_id);
                            active_receivers.insert(req_id.clone(), rx);
                            expected_payload.insert(req_id, payload);
                        }
                    }
                    Action::Cancel(id) => {
                        let req_id = format!("req-{id}");
                        if active_receivers.contains_key(&req_id) {
                            cancelled_ids.insert(req_id.clone());
                            let _ = client.cancel_request(req_id).await;
                        }
                    }
                }
            }

            // Real verification: await ALL responses
            for (req_id, rx) in active_receivers {
                let outcome = rx.await;
                if cancelled_ids.contains(&req_id) {
                    // If request was cancelled in flight, actor must return Error::ActorClosed or close the channel
                    match outcome {
                        Ok(Err(Error::ActorClosed)) | Err(_) => {
                            // Clean cancellation successful
                        }
                        Ok(Ok(mut resp)) => {
                            // Legitimate race condition: /fast request completed BEFORE cancel reached the dispatcher
                            assert_eq!(resp.status, 200);
                            let expected = expected_payload.get(&req_id).unwrap();

                            if let Ok(bytes) = collect_body(&mut resp.body_rx).await {
                                assert!(
                                    bytes.as_slice() == expected.as_bytes() || bytes.len() <= expected.len(),
                                    "Payload is oversized"
                                );
                            }
                        }
                        other => panic!("Unexpected outcome for cancelled request {}: {:?}", req_id, other),
                    }
                } else {
                    // If NOT cancelled, must succeed and return exact expected payload
                    let res = outcome.expect("Receiver must not be dropped prematurely");
                    let mut resp = res.expect("Network request must succeed");
                    assert_eq!(resp.status, 200, "HTTP status for {} must be 200", req_id);

                    let bytes = collect_body(&mut resp.body_rx)
                        .await
                        .expect("Body streaming must succeed");

                    let expected = expected_payload.get(&req_id).unwrap();
                    assert_eq!(
                        bytes.as_slice(),
                        expected.as_bytes(),
                        "Received body for {} does not match expected payload",
                        req_id
                    );
                }
            }

            // Final invariant: all tasks finished, actor must have zero active task leaks
            // Brief yield to allow sweep_dead_requests to clean up if needed
            tokio::time::sleep(Duration::from_millis(50)).await;
            let remaining_tasks = client.get_active_tasks().await.unwrap();
            assert!(
                remaining_tasks.is_empty(),
                "Leak detected: {} tasks still active in HTTP actor",
                remaining_tasks.len()
            );

            Ok::<(), TestCaseError>(())
        })?;
    }
}
