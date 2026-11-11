/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use reqwest_middleware::{ClientWithMiddleware, RequestBuilder};
use std::collections::HashMap;
use tokio::sync::oneshot;
use tokio::task::JoinSet;

use crate::http_client::types::HttpResponse;
use crate::http_client::utils::http_client::command::Command;
use crate::http_client::utils::http_client::error::Result;
use crate::http_client::utils::http_client::task::{ActiveTask, Method, Task};

use super::request::execute_cancellable_req;
use super::sse::execute_cancellable_sse;
use super::url::{apply_headers, build_api_url};

pub(crate) fn sweep_dead_requests(active_requests: &mut HashMap<String, ActiveTask>) {
    active_requests.retain(|_, task| !task.cancel_tx.is_closed());
}

pub(crate) fn dispatch_cmd(
    client: &ClientWithMiddleware,
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
                let _ = task.cancel_tx.send(());
            }
        }
        Command::RegisterCancel {
            req_id,
            cancel_rx_sender,
        } => {
            let (cancel_tx, cancel_rx) = tokio::sync::oneshot::channel();
            active_requests.insert(
                req_id.clone(),
                ActiveTask {
                    task: Task {
                        req_id,
                        method: Method::POST,
                        endpoint: String::new(),
                    },
                    cancel_tx,
                },
            );
            let _ = cancel_rx_sender.send(cancel_rx);
        }
        Command::Sse {
            req_id,
            endpoint,
            headers,
            event_sender,
        } => {
            dispatch_sse(
                client,
                base_url,
                req_id,
                endpoint,
                headers,
                event_sender,
                active_requests,
                child_tasks,
            );
        }
        http_cmd => {
            dispatch_http(client, base_url, http_cmd, active_requests, child_tasks);
        }
    }
}

fn dispatch_sse(
    client: &ClientWithMiddleware,
    base_url: &str,
    req_id: String,
    endpoint: String,
    headers: HashMap<String, String>,
    event_sender: tokio::sync::mpsc::Sender<Result<bytes::Bytes>>,
    active_requests: &mut HashMap<String, ActiveTask>,
    child_tasks: &mut JoinSet<()>,
) {
    let url = build_api_url(base_url, &endpoint);
    let (cancel_tx, cancel_rx) = oneshot::channel();
    active_requests.insert(
        req_id.clone(),
        ActiveTask {
            task: Task {
                req_id: req_id.clone(),
                method: Method::SSE,
                endpoint: url.clone(),
            },
            cancel_tx,
        },
    );
    child_tasks.spawn(execute_cancellable_sse(
        client.clone(),
        url,
        headers,
        event_sender,
        cancel_rx,
        req_id,
    ));
}

fn dispatch_http(
    client: &ClientWithMiddleware,
    base_url: &str,
    cmd: Command,
    active_requests: &mut HashMap<String, ActiveTask>,
    child_tasks: &mut JoinSet<()>,
) {
    let (req, url, req_id, method, responder) = match cmd {
        Command::Get {
            req_id,
            endpoint,
            headers,
            responder,
        } => {
            let (req, url) = prepare_builder(client, base_url, &endpoint, headers, |c, u| c.get(u));
            (req, url, req_id, Method::GET, responder)
        }
        Command::Post {
            req_id,
            endpoint,
            headers,
            body,
            responder,
        } => {
            let (req, url) =
                prepare_builder(client, base_url, &endpoint, headers, |c, u| c.post(u));
            (req.body(body), url, req_id, Method::POST, responder)
        }
        Command::Put {
            req_id,
            endpoint,
            headers,
            body,
            responder,
        } => {
            let (req, url) = prepare_builder(client, base_url, &endpoint, headers, |c, u| c.put(u));
            (req.body(body), url, req_id, Method::PUT, responder)
        }
        Command::Delete {
            req_id,
            endpoint,
            headers,
            responder,
        } => {
            let (req, url) =
                prepare_builder(client, base_url, &endpoint, headers, |c, u| c.delete(u));
            (req, url, req_id, Method::DELETE, responder)
        }
        Command::Patch {
            req_id,
            endpoint,
            headers,
            body,
            responder,
        } => {
            let (req, url) =
                prepare_builder(client, base_url, &endpoint, headers, |c, u| c.patch(u));
            (req.body(body), url, req_id, Method::PATCH, responder)
        }
        Command::Head {
            req_id,
            endpoint,
            headers,
            responder,
        } => {
            let (req, url) =
                prepare_builder(client, base_url, &endpoint, headers, |c, u| c.head(u));
            (req, url, req_id, Method::HEAD, responder)
        }
        Command::Options {
            req_id,
            endpoint,
            headers,
            responder,
        } => {
            let (req, url) = prepare_builder(client, base_url, &endpoint, headers, |c, u| {
                c.request(reqwest::Method::OPTIONS, u)
            });
            (req, url, req_id, Method::OPTIONS, responder)
        }
        Command::Trace {
            req_id,
            endpoint,
            headers,
            responder,
        } => {
            let (req, url) = prepare_builder(client, base_url, &endpoint, headers, |c, u| {
                c.request(reqwest::Method::TRACE, u)
            });
            (req, url, req_id, Method::TRACE, responder)
        }
        _ => return,
    };

    spawn_req_task(
        req,
        url,
        req_id,
        method,
        responder,
        active_requests,
        child_tasks,
    );
}

fn prepare_builder<F>(
    client: &ClientWithMiddleware,
    base_url: &str,
    endpoint: &str,
    headers: HashMap<String, String>,
    build_fn: F,
) -> (RequestBuilder, String)
where
    F: FnOnce(&ClientWithMiddleware, &str) -> RequestBuilder,
{
    let url = build_api_url(base_url, endpoint);
    let req = apply_headers(build_fn(client, &url), headers);
    (req, url)
}

fn spawn_req_task(
    req: RequestBuilder,
    url: String,
    req_id: String,
    method: Method,
    responder: oneshot::Sender<Result<HttpResponse>>,
    active_requests: &mut HashMap<String, ActiveTask>,
    child_tasks: &mut JoinSet<()>,
) {
    let (cancel_tx, cancel_rx) = oneshot::channel();
    active_requests.insert(
        req_id.clone(),
        ActiveTask {
            task: Task {
                req_id: req_id.clone(),
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
