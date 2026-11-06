/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use futures_util::StreamExt;
use reqwest_middleware::RequestBuilder;
use std::collections::HashMap;
use tokio::sync::{mpsc, oneshot};

use crate::http_client::types::HttpResponse;
use crate::http_client::utils::http_client::error::{Error, Result};

pub(crate) async fn execute_cancellable_req(
    req_builder: RequestBuilder,
    url: String,
    responder: oneshot::Sender<Result<HttpResponse>>,
    mut cancel_rx: oneshot::Receiver<()>,
    req_id: String,
) {
    let response = tokio::select! {
        res = req_builder.send() => match res {
            Ok(r) => r,
            Err(e) => {
                let _ = responder.send(Err(Error::NetworkFailure { endpoint: url, reason: e.to_string() }));
                return;
            }
        },
        _ = &mut cancel_rx => {
            let _ = responder.send(Err(Error::ActorClosed));
            return;
        }
    };

    let status = response.status().as_u16();
    let mut headers = HashMap::new();
    for (k, v) in response.headers() {
        if let Ok(val) = v.to_str() {
            headers.insert(k.as_str().to_string(), val.to_string());
        }
    }

    let (body_tx, body_rx) = mpsc::channel(32);
    if responder
        .send(Ok(HttpResponse {
            status,
            headers,
            body_rx,
        }))
        .is_err()
    {
        log::warn!(
            target: "HTTP",
            "Client dropped receiver for {} before response arrived.",
            req_id
        );
        return;
    }

    let mut stream = response.bytes_stream();
    loop {
        tokio::select! {
            chunk_opt = stream.next() => match chunk_opt {
                Some(Ok(bytes)) => {
                    if body_tx.send(Ok(bytes)).await.is_err() {
                        log::debug!(target: "HTTP", "Consumer closed stream for {}", req_id);
                        break;
                    }
                }
                Some(Err(e)) => {
                    log::warn!(target: "HTTP", "Network error streaming {} : {}", req_id, e);
                    let _ = body_tx.send(Err(Error::NetworkFailure { endpoint: url, reason: e.to_string() })).await;
                    break;
                }
                None => break,
            },
            _ = &mut cancel_rx => {
                log::info!(target: "HTTP", "Request {} cancelled by user", req_id);
                let _ = body_tx.send(Err(Error::ActorClosed)).await;
                break;
            },
        }
    }
}
