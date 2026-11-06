/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use proptest::prelude::*;
use std::time::Duration;
use tokio::sync::oneshot;
use wiremock::matchers::{method, path};
use wiremock::{Mock, MockServer, ResponseTemplate};

use crate::http_client::types::HttpResponse;
use crate::http_client::utils::http_client::actor::execute_cancellable_req;
use crate::http_client::utils::http_client::error::Error;

#[derive(Debug, Clone, PartialEq, Eq)]
enum TerminalState {
    Completed,
    Aborted,
    Failed,
}

#[derive(Debug, Clone)]
enum StreamAction {
    ConsumeAll,
    CancelAt(usize),
    DropReceiverAt(usize),
}

// Spawns a local HTTP/1.1 server yielding discrete chunked transfer frames
async fn start_chunked_mock_server(
    chunks: Vec<Vec<u8>>,
    chunk_delay: Duration,
) -> (String, tokio::task::JoinHandle<()>) {
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let addr = listener.local_addr().unwrap();

    let server_handle = tokio::spawn(async move {
        if let Ok((mut socket, _)) = listener.accept().await {
            use tokio::io::{AsyncReadExt, AsyncWriteExt};
            let _ = socket.set_nodelay(true);

            let mut buf = [0u8; 1024];
            let _ = socket.read(&mut buf).await;

            let header =
                "HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\nConnection: close\r\n\r\n";
            if socket.write_all(header.as_bytes()).await.is_err() {
                return;
            }
            let _ = socket.flush().await;

            for chunk in chunks {
                if !chunk_delay.is_zero() {
                    tokio::time::sleep(chunk_delay).await;
                }
                let frame_header = format!("{:X}\r\n", chunk.len());
                if socket.write_all(frame_header.as_bytes()).await.is_err() {
                    return;
                }
                if socket.write_all(&chunk).await.is_err() {
                    return;
                }
                if socket.write_all(b"\r\n").await.is_err() {
                    return;
                }
                let _ = socket.flush().await;
            }

            let _ = socket.write_all(b"0\r\n\r\n").await;
            let _ = socket.flush().await;
        }
    });

    (format!("http://{}", addr), server_handle)
}

fn arbitrary_stream_test_case() -> impl Strategy<Value = (Vec<Vec<u8>>, StreamAction)> {
    prop::collection::vec(prop::collection::vec(any::<u8>(), 32..256), 4..10).prop_flat_map(
        |chunks| {
            let n = chunks.len();
            let action_strat = prop_oneof![
                Just(StreamAction::ConsumeAll),
                (0..n - 1).prop_map(StreamAction::CancelAt),
                (0..n - 1).prop_map(StreamAction::DropReceiverAt),
            ];
            (Just(chunks), action_strat)
        },
    )
}

// ---------------------------------------------------------------------------
// Transitions, Integrity, Cancellation, Drop & Terminality
// ---------------------------------------------------------------------------
proptest! {
    #![proptest_config(ProptestConfig::with_cases(15))]

    #[test]
    fn prop_streaming_state_machine_and_invariants(
        (chunks, action) in arbitrary_stream_test_case()
    ) {
        let rt = tokio::runtime::Runtime::new().unwrap();
        rt.block_on(async {
            let expected_payload: Vec<u8> = chunks.iter().flatten().copied().collect();
            let (server_url, server_handle) =
                start_chunked_mock_server(chunks, Duration::from_millis(2)).await;

            let reqwest_client = reqwest::Client::new();
            let client = reqwest_middleware::ClientBuilder::new(reqwest_client).build();
            let req_builder = client.get(format!("{}/stream", server_url));

            let (responder_tx, responder_rx) = oneshot::channel();
            let (cancel_tx, cancel_rx) = oneshot::channel();
            let mut cancel_tx = Some(cancel_tx);

            let task_handle = tokio::spawn(execute_cancellable_req(
                req_builder,
                format!("{}/stream", server_url),
                responder_tx,
                cancel_rx,
                "mbt-req".to_string(),
            ));

            // Transition: [Init] -> [StreamingBody]
            let http_response: HttpResponse = responder_rx
                .await
                .expect("Responder channel dropped")
                .expect("Initial handshake must succeed");

            prop_assert_eq!(http_response.status, 200);

            let mut body_rx = http_response.body_rx;
            let mut received_bytes = Vec::new();
            let mut chunks_count = 0;
            let mut cancel_at = None;
            let mut terminal_outcomes = Vec::new();

            loop {
                match &action {
                    StreamAction::CancelAt(idx) if *idx == chunks_count && cancel_at.is_none() => {
                        if let Some(tx) = cancel_tx.take() {
                            let _ = tx.send(());
                            cancel_at = Some(chunks_count);
                        }
                    }
                    StreamAction::DropReceiverAt(idx) if *idx == chunks_count => {
                        // Transition: [StreamingBody] -> [Aborted] (Client Drop)
                        drop(body_rx);
                        terminal_outcomes.push(TerminalState::Aborted);
                        break;
                    }
                    _ => {}
                }

                match body_rx.recv().await {
                    Some(Ok(bytes)) => {
                        received_bytes.extend_from_slice(&bytes);
                        chunks_count += 1;
                    }
                    Some(Err(_)) => {
                        if cancel_at.is_some() {
                            terminal_outcomes.push(TerminalState::Aborted);
                        } else {
                            terminal_outcomes.push(TerminalState::Failed);
                        }
                        break;
                    }
                    None => {
                        if cancel_at.is_some() {
                            terminal_outcomes.push(TerminalState::Aborted);
                        } else {
                            terminal_outcomes.push(TerminalState::Completed);
                        }
                        break;
                    }
                }
            }

            // Invariant 4: Client Drop Safety & task termination bound
            tokio::time::timeout(Duration::from_millis(150), task_handle)
                .await
                .expect("Producer task leaked: failed to terminate")
                .unwrap();

            // Invariant 5: At-Most-Once Completion
            prop_assert_eq!(
                terminal_outcomes.len(),
                1,
                "Stream reached multiple or zero terminal states"
            );

            // Invariant 1 & 3: Integrity and No-Waste Cancellation
            match action {
                StreamAction::ConsumeAll => {
                    prop_assert_eq!(terminal_outcomes[0].clone(), TerminalState::Completed);
                    prop_assert_eq!(received_bytes, expected_payload);
                }
                StreamAction::CancelAt(_) => {
                    prop_assert_eq!(terminal_outcomes[0].clone(), TerminalState::Aborted);
                    if let Some(at) = cancel_at {
                        prop_assert!(
                            chunks_count <= at + 3,
                            "Cancelled at chunk {}, but received {}",
                            at,
                            chunks_count
                        );
                    }
                }
                StreamAction::DropReceiverAt(_) => {
                    prop_assert_eq!(terminal_outcomes[0].clone(), TerminalState::Aborted);
                }
            }

            let _ = tokio::time::timeout(Duration::from_millis(100), server_handle).await;
            Ok::<(), TestCaseError>(())
        })?;
    }
}

// ---------------------------------------------------------------------------
// Backpressure Bound (Buffer Capacity O(C))
// ---------------------------------------------------------------------------

#[tokio::test]
async fn test_backpressure_bound_blocks_producer_when_consumer_idle() {
    // 45 discrete frames sent through a 32-capacity mpsc buffer
    let chunks: Vec<Vec<u8>> = (0..45).map(|i| vec![i as u8; 64]).collect();
    let (server_url, server_handle) =
        start_chunked_mock_server(chunks, Duration::from_millis(1)).await;

    let reqwest_client = reqwest::Client::new();
    let client = reqwest_middleware::ClientBuilder::new(reqwest_client).build();
    let req_builder = client.get(format!("{}/stream", server_url));

    let (responder_tx, responder_rx) = oneshot::channel();
    let (_cancel_tx, cancel_rx) = oneshot::channel();

    let mut task_handle = tokio::spawn(execute_cancellable_req(
        req_builder,
        format!("{}/stream", server_url),
        responder_tx,
        cancel_rx,
        "backpressure-test".to_string(),
    ));

    let http_response = responder_rx.await.unwrap().unwrap();
    let mut body_rx = http_response.body_rx;

    // Read only the first chunk
    let first_chunk = body_rx.recv().await.unwrap().unwrap();
    assert_eq!(first_chunk.len(), 64);

    // Wait for the server to emit chunks and saturate mpsc(32)
    tokio::time::sleep(Duration::from_millis(80)).await;

    // Invariant 2: Producer must suspend on body_tx.send() once the channel is full
    let finished = tokio::time::timeout(Duration::from_millis(50), &mut task_handle).await;
    assert!(
        finished.is_err(),
        "Producer must suspend when channel buffer reaches capacity"
    );

    // Dropping receiver unblocks and terminates the producer
    drop(body_rx);
    tokio::time::timeout(Duration::from_millis(150), task_handle)
        .await
        .expect("Producer must terminate on channel disconnect")
        .unwrap();

    let _ = tokio::time::timeout(Duration::from_millis(100), server_handle).await;
}

// ---------------------------------------------------------------------------
// Initial Phase Transitions: [Init] -> [Aborted] and [Init] -> [Failed]
// ---------------------------------------------------------------------------

#[tokio::test]
async fn test_transition_init_cancelled_aborts_immediately() {
    let server = MockServer::start().await;

    Mock::given(method("GET"))
        .and(path("/delayed"))
        .respond_with(
            ResponseTemplate::new(200)
                .set_delay(Duration::from_millis(200))
                .set_body_bytes(b"DATA"),
        )
        .mount(&server)
        .await;

    let reqwest_client = reqwest::Client::new();
    let client = reqwest_middleware::ClientBuilder::new(reqwest_client).build();
    let req_builder = client.get(format!("{}/delayed", server.uri()));

    let (responder_tx, responder_rx) = oneshot::channel();
    let (cancel_tx, cancel_rx) = oneshot::channel();

    let task_handle = tokio::spawn(execute_cancellable_req(
        req_builder,
        format!("{}/delayed", server.uri()),
        responder_tx,
        cancel_rx,
        "init-cancel-test".to_string(),
    ));

    cancel_tx.send(()).unwrap();

    let outcome = responder_rx.await.unwrap();
    match outcome {
        Err(Error::ActorClosed) => {}
        other => panic!("Expected Error::ActorClosed, got {:?}", other),
    }

    tokio::time::timeout(Duration::from_millis(100), task_handle)
        .await
        .expect("Producer must exit immediately on initial cancel")
        .unwrap();
}

#[tokio::test]
async fn test_transition_init_network_error_fails() {
    let invalid_url = "http://127.0.0.1:1/unreachable".to_string();

    let reqwest_client = reqwest::Client::new();
    let client = reqwest_middleware::ClientBuilder::new(reqwest_client).build();
    let req_builder = client.get(&invalid_url);

    let (responder_tx, responder_rx) = oneshot::channel();
    let (_cancel_tx, cancel_rx) = oneshot::channel();

    let task_handle = tokio::spawn(execute_cancellable_req(
        req_builder,
        invalid_url,
        responder_tx,
        cancel_rx,
        "init-fail-test".to_string(),
    ));

    let outcome = responder_rx.await.unwrap();
    match outcome {
        Err(Error::NetworkFailure { .. }) => {}
        other => panic!("Expected Error::NetworkFailure, got {:?}", other),
    }

    tokio::time::timeout(Duration::from_millis(100), task_handle)
        .await
        .expect("Producer must terminate on network error")
        .unwrap();
}
