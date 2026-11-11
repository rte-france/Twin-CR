/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use eventsource_stream::Eventsource;
use futures_util::StreamExt;
use reqwest_middleware::ClientWithMiddleware;
use std::collections::HashMap;
use tokio::sync::{mpsc, oneshot};
use tokio::time::{sleep, timeout, Duration};

use crate::http_client::utils::http_client::error::Result;

#[derive(Debug)]
enum ConnectResult<S> {
    Connected(S),
    Failed,
    Fatal(reqwest::StatusCode),
    Aborted,
}

#[derive(Clone, Copy, Debug)]
pub(crate) struct SseRetryConfig {
    pub initial_backoff: Duration,
    pub max_backoff: Duration,
    pub connect_timeout: Duration,
}

impl Default for SseRetryConfig {
    fn default() -> Self {
        Self {
            initial_backoff: Duration::from_secs(1),
            max_backoff: Duration::from_secs(30),
            connect_timeout: Duration::from_secs(10),
        }
    }
}

pub(crate) async fn execute_cancellable_sse(
    client: ClientWithMiddleware,
    url: String,
    headers: HashMap<String, String>,
    tx: mpsc::Sender<Result<bytes::Bytes>>,
    cancel_rx: oneshot::Receiver<()>,
    req_id: String,
) {
    execute_cancellable_sse_with_config(
        client,
        url,
        headers,
        tx,
        cancel_rx,
        req_id,
        SseRetryConfig::default(),
    )
    .await
}

pub(crate) async fn execute_cancellable_sse_with_config(
    client: ClientWithMiddleware,
    url: String,
    headers: HashMap<String, String>,
    tx: mpsc::Sender<Result<bytes::Bytes>>,
    mut cancel_rx: oneshot::Receiver<()>,
    req_id: String,
    config: SseRetryConfig,
) {
    let mut backoff = config.initial_backoff;
    let mut last_event_id: Option<String> = None;

    loop {
        match connect_sse_stream(
            &client,
            &url,
            &headers,
            last_event_id.as_deref(),
            &req_id,
            config.connect_timeout,
            &mut cancel_rx,
        )
        .await
        {
            ConnectResult::Aborted => {
                // Invariant: User cancellation aborts execution immediately without retry.
                log::info!(target: "HTTP", "SSE cancelled during connection for req_id: {}", req_id);
                return;
            }
            ConnectResult::Fatal(status) => {
                // Invariant: Permanent client errors (4xx except 408/429) must abort without retry.
                log::error!(target: "HTTP", "SSE aborted on fatal client status {} for req_id: {}", status, req_id);
                return;
            }
            ConnectResult::Failed => {
                if wait_backoff_or_cancel(backoff, &mut cancel_rx).await {
                    // Invariant: Cancellation received during sleep halts retry cycle immediately.
                    return;
                }
                // Invariant: Backoff duration is monotonically non-decreasing up to max_backoff.
                backoff = std::cmp::min(backoff * 2, config.max_backoff);
                continue;
            }
            ConnectResult::Connected(mut stream) => {
                // Invariant: Successful handshake resets backoff duration to initial value.
                backoff = config.initial_backoff;
                if pump_sse_events(
                    &mut stream,
                    &tx,
                    &mut last_event_id,
                    &mut cancel_rx,
                    &req_id,
                )
                .await
                {
                    return;
                }
            }
        }
    }
}

async fn connect_sse_stream(
    client: &ClientWithMiddleware,
    url: &str,
    headers: &HashMap<String, String>,
    last_event_id: Option<&str>,
    req_id: &str,
    connect_timeout: Duration,
    cancel_rx: &mut oneshot::Receiver<()>,
) -> ConnectResult<
    eventsource_stream::EventStream<
        impl futures_util::Stream<Item = reqwest::Result<bytes::Bytes>>,
    >,
> {
    log::debug!(target: "HTTP", "Attempting SSE connection to {} (req_id: {})", url, req_id);

    let mut req = client.get(url).header("Accept", "text/event-stream");
    for (k, v) in headers {
        req = req.header(k, v);
    }

    // Invariant: Last-Event-ID header is present on reconnect if an ID was previously recorded.
    if let Some(id) = last_event_id {
        req = req.header("Last-Event-ID", id);
    }

    let send_result = tokio::select! {
        res = timeout(connect_timeout, req.send()) => res,
        _ = &mut *cancel_rx => {
            log::info!(target: "HTTP", "SSE connection aborted during handshake (req_id: {})", req_id);
            return ConnectResult::Aborted;
        }
    };

    match send_result {
        Ok(Ok(res)) if res.status().is_success() => {
            log::info!(target: "HTTP", "SSE connection established (req_id: {})", req_id);
            ConnectResult::Connected(res.bytes_stream().eventsource())
        }
        Ok(Ok(res))
            if res.status().is_client_error()
                && res.status() != reqwest::StatusCode::REQUEST_TIMEOUT
                && res.status() != reqwest::StatusCode::TOO_MANY_REQUESTS =>
        {
            // Invariant: 4xx statuses except 408 and 429 are unrecoverable client errors.
            log::error!(target: "HTTP", "SSE connection rejected with fatal status {} for req_id: {}", res.status(), req_id);
            ConnectResult::Fatal(res.status())
        }
        Ok(Ok(res)) => {
            log::warn!(target: "HTTP", "SSE connection rejected (status: {}) for req_id: {}", res.status(), req_id);
            ConnectResult::Failed
        }
        Ok(Err(e)) => {
            log::warn!(target: "HTTP", "SSE network error: {} (req_id: {})", e, req_id);
            ConnectResult::Failed
        }
        Err(_) => {
            log::warn!(target: "HTTP", "SSE timed out (req_id: {})", req_id);
            ConnectResult::Failed
        }
    }
}

async fn wait_backoff_or_cancel(backoff: Duration, cancel_rx: &mut oneshot::Receiver<()>) -> bool {
    tokio::select! {
        _ = sleep(backoff) => false,
        _ = &mut *cancel_rx => true,
    }
}

async fn pump_sse_events<S>(
    stream: &mut S,
    tx: &mpsc::Sender<Result<bytes::Bytes>>,
    last_event_id: &mut Option<String>,
    cancel_rx: &mut oneshot::Receiver<()>,
    req_id: &str,
) -> bool
where
    S: StreamExt<
            Item = std::result::Result<
                eventsource_stream::Event,
                eventsource_stream::EventStreamError<reqwest::Error>,
            >,
        > + Unpin,
{
    loop {
        tokio::select! {
            event_opt = stream.next() => {
                match event_opt {
                    Some(Ok(event)) => {
                        log::trace!(target: "HTTP", "SSE chunk received for req_id: {}", req_id);

                        // Invariant: Latest non-empty event ID persists across reconnects.
                        if !event.id.is_empty() {
                            *last_event_id = Some(event.id.clone());
                        }

                        // Invariant: Emitted frames strictly preserve standard W3C SSE wire framing.
                        let wire_bytes = serialize_sse_event(&event);
                        if tx.send(Ok(wire_bytes)).await.is_err() {
                            // Invariant: Closed consumer channel terminates stream pumping.
                            return true;
                        }
                    }
                    Some(Err(e)) => {
                        log::warn!(target: "HTTP", "SSE stream parsing error: {} (req_id: {})", e, req_id);
                        return false;
                    }
                    None => {
                        log::info!(target: "HTTP", "SSE gracefully closed (req_id: {})", req_id);
                        return false;
                    }
                }
            }
            _ = &mut *cancel_rx => {
                log::info!(target: "HTTP", "SSE stream interrupted by user (req_id: {})", req_id);
                return true;
            }
        }
    }
}

// Matching standard W3C SSE specification requirements
fn serialize_sse_event(event: &eventsource_stream::Event) -> bytes::Bytes {
    let mut buf = String::with_capacity(event.data.len() + 64);

    // Invariant: id line is serialized only when non-empty.
    if !event.id.is_empty() {
        buf.push_str("id: ");
        buf.push_str(&event.id);
        buf.push('\n');
    }

    // Invariant: event field is emitted only for non-default event types.
    if !event.event.is_empty() && event.event != "message" {
        buf.push_str("event: ");
        buf.push_str(&event.event);
        buf.push('\n');
    }

    // Invariant: retry field is rendered in milliseconds when present.
    if let Some(retry) = event.retry {
        buf.push_str("retry: ");
        buf.push_str(&retry.as_millis().to_string());
        buf.push('\n');
    }

    // Invariant: Every data line carries the 'data: ' prefix, ending with a double newline frame delimiter.
    if event.data.is_empty() {
        buf.push_str("data:\n");
    } else {
        for line in event.data.split('\n') {
            let clean = line.strip_suffix('\r').unwrap_or(line);
            buf.push_str("data: ");
            buf.push_str(clean);
            buf.push('\n');
        }
    }

    buf.push('\n');
    bytes::Bytes::from(buf)
}

#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;
    use wiremock::matchers::{header, method, path};
    use wiremock::{Mock, MockServer, ResponseTemplate};

    fn setup_test_client() -> ClientWithMiddleware {
        let reqwest_client = reqwest::Client::builder()
            .timeout(Duration::from_secs(2))
            .build()
            .expect("Failed to build reqwest client");
        reqwest_middleware::ClientBuilder::new(reqwest_client).build()
    }

    fn test_retry_config() -> SseRetryConfig {
        SseRetryConfig {
            initial_backoff: Duration::from_millis(5),
            max_backoff: Duration::from_millis(40),
            connect_timeout: Duration::from_millis(200),
        }
    }

    proptest! {
        #![proptest_config(ProptestConfig::with_cases(10))]

        #[test]
        fn prop_fatal_client_status_aborts_immediately(
            status_code in prop_oneof![
                Just(400u16),
                Just(401u16),
                Just(403u16),
                Just(404u16),
                Just(405u16),
                Just(422u16),
            ]
        ) {
            let rt = tokio::runtime::Runtime::new().unwrap();
            rt.block_on(async {
                let server = MockServer::start().await;

                Mock::given(method("GET"))
                    .and(path("/sse"))
                    .and(header("Accept", "text/event-stream"))
                    .respond_with(ResponseTemplate::new(status_code))
                    .mount(&server)
                    .await;

                let client = setup_test_client();
                let (tx, mut rx) = mpsc::channel(16);
                let (_cancel_tx, cancel_rx) = oneshot::channel();

                let handle = tokio::spawn(execute_cancellable_sse_with_config(
                    client,
                    format!("{}/sse", server.uri()),
                    HashMap::new(),
                    tx,
                    cancel_rx,
                    "fatal-test".to_string(),
                    test_retry_config(),
                ));

                // Invariant: Non-retryable status halts execution within the timeout boundary.
                tokio::time::timeout(Duration::from_millis(500), handle)
                    .await
                    .expect("Task must abort quickly")
                    .unwrap();

                // Invariant: Exactly one request dispatched on fatal response.
                let requests = server.received_requests().await.unwrap();
                prop_assert_eq!(requests.len(), 1);

                // Invariant: Channel receives no payloads on fatal connection.
                prop_assert!(rx.recv().await.is_none());

                Ok::<(), TestCaseError>(())
            })?;
        }

        #[test]
        fn prop_retryable_status_eventually_succeeds_model(
            retry_count in 1usize..3usize,
            retry_status in prop_oneof![
                Just(408u16),
                Just(429u16),
                Just(500u16),
                Just(502u16),
                Just(503u16),
            ]
        ) {
            let rt = tokio::runtime::Runtime::new().unwrap();
            rt.block_on(async {
                let server = MockServer::start().await;

                Mock::given(method("GET"))
                    .and(path("/sse"))
                    .respond_with(ResponseTemplate::new(retry_status))
                    .up_to_n_times(retry_count as u64)
                    .mount(&server)
                    .await;

                Mock::given(method("GET"))
                    .and(path("/sse"))
                    .respond_with(
                        ResponseTemplate::new(200)
                            .insert_header("content-type", "text/event-stream")
                            .set_body_string("id: 101\nevent: custom\ndata: payload_body\n\n"),
                    )
                    .mount(&server)
                    .await;

                let client = setup_test_client();
                let (tx, mut rx) = mpsc::channel(16);
                let (_cancel_tx, cancel_rx) = oneshot::channel();

                tokio::spawn(execute_cancellable_sse_with_config(
                    client,
                    format!("{}/sse", server.uri()),
                    HashMap::new(),
                    tx,
                    cancel_rx,
                    "retry-model".to_string(),
                    test_retry_config(),
                ));

                let received = tokio::time::timeout(Duration::from_secs(2), rx.recv())
                    .await
                    .expect("Payload must arrive within timeout")
                    .expect("Channel must remain open")
                    .expect("Payload must be Ok");

                // Invariant: Wire framing structure is intact for downstream consumers.
                prop_assert_eq!(
                    std::str::from_utf8(&received).unwrap(),
                    "id: 101\nevent: custom\ndata: payload_body\n\n"
                );

                // Invariant: Total dispatched requests equal failures plus single success.
                let requests = server.received_requests().await.unwrap();
                prop_assert_eq!(requests.len(), retry_count + 1);

                Ok::<(), TestCaseError>(())
            })?;
        }

        #[test]
        fn prop_last_event_id_resumption_after_disconnect(
            id_value in "[0-9]{1,8}"
        ) {
            let rt = tokio::runtime::Runtime::new().unwrap();
            rt.block_on(async {
                let server = MockServer::start().await;

                // First connection: stream sends one event then terminates.
                Mock::given(method("GET"))
                    .and(path("/sse"))
                    .respond_with(
                        ResponseTemplate::new(200)
                            .insert_header("content-type", "text/event-stream")
                            .set_body_string(format!("id: {id_value}\ndata: part1\n\n")),
                    )
                    .up_to_n_times(1)
                    .mount(&server)
                    .await;

                // Reconnection: must present Last-Event-ID header matching the received id.
                // Keeping connection open by returning a pending/never-ending body, or streaming,
                // so the client never hits EOF and never attempts a 3rd reconnection.
                Mock::given(method("GET"))
                    .and(path("/sse"))
                    .and(header("Last-Event-ID", id_value.as_str()))
                    .respond_with(
                        ResponseTemplate::new(200)
                            .insert_header("content-type", "text/event-stream")
                            .set_body_string("data: part2\n\n"),
                    )
                    .mount(&server)
                    .await;

                let client = setup_test_client();
                let (tx, mut rx) = mpsc::channel(16);
                let (cancel_tx, cancel_rx) = oneshot::channel();

                let handle = tokio::spawn(execute_cancellable_sse_with_config(
                    client,
                    format!("{}/sse", server.uri()),
                    HashMap::new(),
                    tx,
                    cancel_rx,
                    "resume-test".to_string(),
                    test_retry_config(),
                ));

                let frame1 = rx.recv().await.unwrap().unwrap();
                prop_assert_eq!(
                    std::str::from_utf8(&frame1).unwrap(),
                    format!("id: {id_value}\ndata: part1\n\n")
                );

                let frame2 = rx.recv().await.unwrap().unwrap();
                prop_assert_eq!(std::str::from_utf8(&frame2).unwrap(), "data: part2\n\n");

                let _ = cancel_tx.send(());
                let _ = handle.await;

                // Invariant: Server observed at least 2 connections, and request #2 had Last-Event-ID.
                let requests = server.received_requests().await.unwrap();
                prop_assert!(requests.len() >= 2);
                let last_req_header = requests[1].headers.get("last-event-id").unwrap();
                prop_assert_eq!(last_req_header.to_str().unwrap(), id_value.as_str());

                Ok::<(), TestCaseError>(())
            })?;
        }

        #[test]
        fn prop_cancellation_during_backoff_model(
            fail_status in prop_oneof![Just(500u16), Just(503u16)]
        ) {
            let rt = tokio::runtime::Runtime::new().unwrap();
            rt.block_on(async {
                let server = MockServer::start().await;

                Mock::given(method("GET"))
                    .and(path("/sse"))
                    .respond_with(ResponseTemplate::new(fail_status))
                    .mount(&server)
                    .await;

                let client = setup_test_client();
                let (tx, _rx) = mpsc::channel(16);
                let (cancel_tx, cancel_rx) = oneshot::channel();

                let long_backoff_config = SseRetryConfig {
                    initial_backoff: Duration::from_secs(10),
                    max_backoff: Duration::from_secs(30),
                    connect_timeout: Duration::from_millis(200),
                };

                let handle = tokio::spawn(execute_cancellable_sse_with_config(
                    client,
                    format!("{}/sse", server.uri()),
                    HashMap::new(),
                    tx,
                    cancel_rx,
                    "cancel-test".to_string(),
                    long_backoff_config,
                ));

                tokio::time::sleep(Duration::from_millis(20)).await;
                let _ = cancel_tx.send(());

                // Invariant: Sleep duration is bypassed immediately on cancel signal.
                tokio::time::timeout(Duration::from_millis(200), handle)
                    .await
                    .expect("Cancellation must resolve without waiting for full backoff duration")
                    .unwrap();

                // Invariant: Cancellation prevents second request dispatch.
                let requests = server.received_requests().await.unwrap();
                prop_assert_eq!(requests.len(), 1);

                Ok::<(), TestCaseError>(())
            })?;
        }
    }
}
