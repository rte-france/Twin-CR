/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use log::{error, info, warn};
use reqwest::{Client, RequestBuilder};
use std::collections::HashMap;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::{mpsc, oneshot, watch};
use tokio::task::JoinSet;

use crate::common::utils::http_client::task::{Method, Task};
use crate::common::utils::http_client::HealthStrategy;

use super::command::Command;
use super::error::{Error, Result};
use super::status::ServerStatus;
use super::task::ActiveTask;

pub(crate) fn build_api_url(base_url: &str, endpoint: &str) -> String {
    format!(
        "{}/{}",
        base_url.trim_end_matches('/'),
        endpoint.trim_start_matches('/')
    )
}

pub(crate) async fn execute_cancellable_req(
    req_builder: RequestBuilder,
    url: String,
    responder: oneshot::Sender<Result<(u16, bytes::Bytes)>>,
    mut cancel_rx: oneshot::Receiver<()>,
    req_id: String,
) {
    let fetch_future = async {
        let response = req_builder
            .send()
            .await
            .map_err(|e| Error::NetworkFailure {
                endpoint: url.clone(),
                reason: e.to_string(),
            })?;

        let status = response.status().as_u16();
        let bytes = response.bytes().await.map_err(|e| Error::NetworkFailure {
            endpoint: url.clone(),
            reason: e.to_string(),
        })?;

        Ok((status, bytes))
    };

    let result = tokio::select! {
        res = fetch_future => res,
        _ = &mut cancel_rx => {
            Err(Error::ActorClosed)
        }
    };

    if responder.send(result).is_err() {
        warn!(
            "Client dropped receiver for {} before response arrived.",
            req_id
        );
    }
}

pub(crate) async fn execute_cancellable_sse(
    client: Client,
    url: String,
    tx: mpsc::Sender<Result<bytes::Bytes>>,
    mut cancel_rx: oneshot::Receiver<()>,
    req_id: String,
) {
    let req = client.get(&url).header("Accept", "text/event-stream");

    let mut res = match req.send().await {
        Ok(r) => r,
        Err(e) => {
            let err = Err(Error::NetworkFailure {
                endpoint: url.clone(),
                reason: e.to_string(),
            });
            if tx.send(err).await.is_err() {
                warn!(
                    "SSE receiver dropped before network error could be sent for {}.",
                    url
                );
            }
            return;
        }
    };

    loop {
        tokio::select! {
            chunk_res = res.chunk() => {
                match chunk_res {
                    Ok(Some(chunk)) => {
                        if tx.send(Ok(chunk)).await.is_err() {
                            warn!("SSE Receiver dropped. Closing stream for {}.", url);
                            break;
                        }
                    }
                    Ok(None) => break, // Stream ended naturally by server
                    Err(e) => {
                        let err = Err(Error::NetworkFailure { endpoint: url.clone(), reason: e.to_string() });
                        if tx.send(err).await.is_err() {
                            warn!("SSE receiver dropped during chunk error for {}.", url);
                        }
                        break;
                    }
                }
            }
            _ = &mut cancel_rx => {
                warn!("SSE stream {} to {} was explicitly cancelled.", req_id, url);
                break;
            }
        }
    }
}

pub(crate) async fn check_health(
    client: &Client,
    base_url: &str,
    status_tx: &watch::Sender<ServerStatus>,
    strategy: &dyn HealthStrategy,
) -> bool {
    let new_status = strategy.check(client, base_url).await;
    if status_tx.send(new_status).is_err() {
        error!("CRITICAL: Loss of observability. Aborting actor execution.");
        return false;
    }
    true
}

pub(crate) async fn run_scada_actor(
    client: Client,
    base_url: String,
    status_tx: watch::Sender<ServerStatus>,
    mut cmd_rx: mpsc::Receiver<Command>,
    health_strategy: Arc<dyn HealthStrategy>,
) {
    let mut health_interval = tokio::time::interval(Duration::from_secs(30));
    health_interval.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Skip);

    let mut child_tasks = JoinSet::new();
    let mut active_requests: HashMap<String, ActiveTask> = HashMap::new();

    let (hc_tx, mut hc_rx) = mpsc::channel(2);

    loop {
        tokio::select! {
            _ = health_interval.tick() => {
                let client_clone = client.clone();
                let base_url_clone = base_url.clone();
                let strategy_clone = health_strategy.clone();
                let hc_tx_clone = hc_tx.clone();

                child_tasks.spawn(async move {
                    let status = strategy_clone.check(&client_clone, &base_url_clone).await;
                    let _ = hc_tx_clone.send(status).await;
                });
            }
            Some(new_status) = hc_rx.recv() => {
                if status_tx.send(new_status).is_err() {
                    error!("CRITICAL: Loss of observability. Aborting actor execution.");
                    break;
                }
            }
            Some(join_result) = child_tasks.join_next() => {
                if let Err(panic_err) = join_result {
                    error!("CRITICAL: A supervised child task panicked: {}", panic_err);
                }
                sweep_dead_requests(&mut active_requests);
            }
            cmd_opt = cmd_rx.recv() => {
                let Some(cmd) = cmd_opt else {
                    info!("Command channel closed. Stopping actor.");
                    break;
                };
                dispatch_cmd(&client, &base_url, cmd, &mut active_requests, &mut child_tasks);
            }
        }
    }
    child_tasks.abort_all();
}

fn sweep_dead_requests(active_requests: &mut HashMap<String, ActiveTask>) {
    active_requests.retain(|_, task| !task.cancel_tx.is_closed());
}

fn handle_cancellable_cmd(
    req: RequestBuilder,
    url: String,
    req_id: String,
    method: Method,
    responder: oneshot::Sender<Result<(u16, bytes::Bytes)>>,
    active_requests: &mut HashMap<String, ActiveTask>,
    child_tasks: &mut JoinSet<()>,
) {
    let (cancel_tx, cancel_rx) = oneshot::channel();
    active_requests.insert(
        req_id.clone(),
        ActiveTask {
            task: Task {
                req_id: req_id.to_string(),
                method,
                endpoint: url.clone(),
            },
            cancel_tx,
        },
    );
    child_tasks.spawn(execute_cancellable_req(
        req, url, responder, cancel_rx, req_id,
    ));
}

fn dispatch_cmd(
    client: &Client,
    base_url: &str,
    cmd: Command,
    active_requests: &mut HashMap<String, ActiveTask>,
    child_tasks: &mut JoinSet<()>,
) {
    match cmd {
        Command::GetTasks { responder } => {
            sweep_dead_requests(active_requests);
            let tasks = active_requests.values().map(|t| t.task.clone()).collect();
            let _ = responder.send(tasks);
        }
        Command::Cancel { req_id } => {
            if let Some(task) = active_requests.remove(&req_id) {
                if task.cancel_tx.send(()).is_err() {
                    warn!("Cancel failed: Task {} was already dead.", req_id);
                }
            }
        }
        Command::Get {
            req_id,
            endpoint,
            responder,
        } => {
            let url = build_api_url(base_url, &endpoint);
            handle_cancellable_cmd(
                client
                    .get(&url)
                    .header("user-agent", "PostmanRuntime/7.51.0")
                    .header("accept", "*/*"),
                url,
                req_id,
                Method::GET,
                responder,
                active_requests,
                child_tasks,
            );
        }
        Command::Post {
            req_id,
            endpoint,
            body,
            responder,
        } => {
            let url = build_api_url(base_url, &endpoint);
            let req = client
                .post(&url)
                .header("Content-Type", "application/json")
                .body(body);
            handle_cancellable_cmd(
                req,
                url,
                req_id,
                Method::POST,
                responder,
                active_requests,
                child_tasks,
            );
        }
        Command::Put {
            req_id,
            endpoint,
            body,
            responder,
        } => {
            let url = build_api_url(base_url, &endpoint);
            let req = client
                .put(&url)
                .header("Content-Type", "application/json")
                .body(body);
            handle_cancellable_cmd(
                req,
                url,
                req_id,
                Method::PUT,
                responder,
                active_requests,
                child_tasks,
            );
        }
        Command::PutMultipart {
            req_id,
            endpoint,
            form,
            responder,
        } => {
            let url = build_api_url(base_url, &endpoint);
            handle_cancellable_cmd(
                client.put(&url).multipart(form),
                url,
                req_id,
                Method::MULTIPART,
                responder,
                active_requests,
                child_tasks,
            );
        }
        Command::Delete {
            req_id,
            endpoint,
            responder,
        } => {
            let url = build_api_url(base_url, &endpoint);
            handle_cancellable_cmd(
                client.delete(&url),
                url,
                req_id,
                Method::DELETE,
                responder,
                active_requests,
                child_tasks,
            );
        }
        Command::PostMultipart {
            req_id,
            endpoint,
            form,
            responder,
        } => {
            let url = build_api_url(base_url, &endpoint);
            handle_cancellable_cmd(
                client.post(&url).multipart(form),
                url,
                req_id,
                Method::MULTIPART,
                responder,
                active_requests,
                child_tasks,
            );
        }
        Command::Sse {
            req_id,
            endpoint,
            event_sender,
        } => {
            let url = build_api_url(base_url, &endpoint);
            let (cancel_tx, cancel_rx) = oneshot::channel();
            active_requests.insert(
                req_id.clone(),
                ActiveTask {
                    task: Task {
                        req_id: req_id.clone(),
                        method: Method::SEE,
                        endpoint: url.clone(),
                    },
                    cancel_tx,
                },
            );
            child_tasks.spawn(execute_cancellable_sse(
                client.clone(),
                url,
                event_sender,
                cancel_rx,
                req_id,
            ));
        }
    }
}
