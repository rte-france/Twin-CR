/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

pub(crate) mod dispatcher;
pub(crate) mod request;
pub(crate) mod sse;
pub mod url;

use reqwest_middleware::ClientWithMiddleware;
use std::collections::HashMap;
use tokio::sync::mpsc;
use tokio::task::JoinSet;

use super::command::Command;
use super::task::ActiveTask;

#[cfg(test)]
pub(crate) use dispatcher::sweep_dead_requests;
#[cfg(test)]
pub(crate) use request::execute_cancellable_req;

pub async fn run_http_client_actor(
    client: ClientWithMiddleware,
    base_url: String,
    mut cmd_rx: mpsc::Receiver<Command>,
) {
    let mut child_tasks = JoinSet::new();
    let mut active_requests: HashMap<String, ActiveTask> = HashMap::new();

    loop {
        tokio::select! {
            Some(join_result) = child_tasks.join_next() => {
                if let Err(panic_err) = join_result {
                    log::error!(target: "HTTP", "CRITICAL: child task panicked: {}", panic_err);
                }
                dispatcher::sweep_dead_requests(&mut active_requests);
            }
            cmd_opt = cmd_rx.recv() => {
                let Some(cmd) = cmd_opt else {
                    log::info!(target: "HTTP", "Command channel closed. Stopping actor.");
                    break;
                };
                dispatcher::dispatch_cmd(&client, &base_url, cmd, &mut active_requests, &mut child_tasks);
            }
        }
    }
    child_tasks.abort_all();
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::http_client::utils::http_client::error::Error;
    use crate::http_client::utils::http_client::task::{Method, Task};
    use std::time::Duration;
    use tokio::sync::oneshot;

    #[tokio::test]
    async fn test_cancellable_req_aborted_when_cancel_rx_triggered() {
        let (responder_tx, responder_rx) = oneshot::channel();
        let (cancel_tx, cancel_rx) = oneshot::channel();

        let client = reqwest_middleware::ClientBuilder::new(reqwest::Client::new()).build();
        let req_builder = client.get("http://192.0.2.1/hang");

        let join_handle = tokio::spawn(execute_cancellable_req(
            req_builder,
            "http://192.0.2.1/hang".to_string(),
            responder_tx,
            cancel_rx,
            "req-cancel-test".to_string(),
        ));

        cancel_tx.send(()).unwrap();

        let res = responder_rx.await.expect("Responder must receive result");
        assert!(matches!(res, Err(Error::ActorClosed)));

        join_handle.await.expect("Task must terminate cleanly");
    }

    #[tokio::test]
    async fn test_cancellable_req_handles_responder_dropped_gracefully() {
        let (responder_tx, responder_rx) = oneshot::channel();
        let (_cancel_tx, cancel_rx) = oneshot::channel();

        drop(responder_rx);

        let client = reqwest_middleware::ClientBuilder::new(reqwest::Client::new()).build();
        let req_builder = client.get("http://127.0.0.1:1/refused");

        execute_cancellable_req(
            req_builder,
            "http://127.0.0.1:1/refused".to_string(),
            responder_tx,
            cancel_rx,
            "req-dropped-test".to_string(),
        )
        .await;
    }

    #[tokio::test]
    async fn test_sweep_dead_requests_cleans_closed_channels() {
        let mut active_requests: HashMap<String, ActiveTask> = HashMap::new();

        let (live_tx, _live_rx) = oneshot::channel();
        active_requests.insert(
            "live".into(),
            ActiveTask {
                task: Task {
                    req_id: "live".into(),
                    method: Method::GET,
                    endpoint: "http://example.com".into(),
                },
                cancel_tx: live_tx,
            },
        );

        let (dead_tx, dead_rx) = oneshot::channel();
        drop(dead_rx);
        active_requests.insert(
            "dead".into(),
            ActiveTask {
                task: Task {
                    req_id: "dead".into(),
                    method: Method::POST,
                    endpoint: "http://example.com".into(),
                },
                cancel_tx: dead_tx,
            },
        );

        assert_eq!(active_requests.len(), 2);
        sweep_dead_requests(&mut active_requests);
        assert_eq!(active_requests.len(), 1);
        assert!(active_requests.contains_key("live"));
        assert!(!active_requests.contains_key("dead"));
    }

    #[tokio::test]
    async fn test_actor_lifecycle_cancel_and_get_tasks() {
        let (cmd_tx, cmd_rx) = mpsc::channel(32);
        let client = reqwest_middleware::ClientBuilder::new(reqwest::Client::new()).build();

        let actor_handle = tokio::spawn(run_http_client_actor(
            client,
            "http://192.0.2.1".to_string(),
            cmd_rx,
        ));

        let connected = super::super::client::Client {
            url: Some("http://192.0.2.1".to_string()),
            state: super::super::client::Connected { sender: cmd_tx },
        };

        let rx1 = connected
            .get("req-1".into(), "/hang1", HashMap::new())
            .await
            .expect("Send req 1");
        let rx2 = connected
            .get("req-2".into(), "/hang2", HashMap::new())
            .await
            .expect("Send req 2");

        let tasks = connected.get_active_tasks().await.expect("Get tasks");
        assert_eq!(tasks.len(), 2);
        let ids: Vec<String> = tasks.into_iter().map(|t| t.req_id).collect();
        assert!(ids.contains(&"req-1".to_string()));
        assert!(ids.contains(&"req-2".to_string()));

        connected
            .cancel_request("req-1".into())
            .await
            .expect("Cancel req-1");

        let res1 = rx1.await.expect("rx1 receives response");
        assert!(matches!(res1, Err(Error::ActorClosed)));

        let tasks_after = connected
            .get_active_tasks()
            .await
            .expect("Get tasks after cancel");
        assert_eq!(tasks_after.len(), 1);
        assert_eq!(tasks_after[0].req_id, "req-2");

        drop(connected);
        drop(rx2);

        tokio::time::timeout(Duration::from_millis(500), actor_handle)
            .await
            .expect("Actor did not hang on shutdown")
            .expect("Actor finished without panic");
    }
}
