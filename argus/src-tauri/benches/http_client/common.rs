/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use std::convert::Infallible;
use std::net::SocketAddr;
use std::time::Duration;

use bytes::Bytes;
use http_body_util::Full;
use hyper::service::service_fn;
use hyper::{Request, Response};
use hyper_util::rt::{TokioExecutor, TokioIo};
use hyper_util::server::conn::auto::Builder;
use tokio::net::TcpListener;

use argus_lib::http_client::utils::http_client::actor::run_http_client_actor;
use argus_lib::http_client::utils::http_client::client::{Client, Connected};

/// Fast loopback HTTP server with zero serialization overhead
#[allow(dead_code)]
pub async fn start_hyper_echo_server() -> (String, SocketAddr) {
    let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let addr = listener.local_addr().unwrap();

    tokio::spawn(async move {
        loop {
            let (stream, _) = match listener.accept().await {
                Ok(conn) => conn,
                Err(_) => break,
            };

            tokio::spawn(async move {
                let io = TokioIo::new(stream);
                let service = service_fn(|mut req: Request<hyper::body::Incoming>| async move {
                    use http_body_util::BodyExt;
                    // Drain the incoming request body so the HTTP connection remains clean for pipelining/keep-alive
                    while let Some(frame) = req.body_mut().frame().await {
                        if frame.is_err() {
                            break;
                        }
                    }

                    let path = req.uri().path();
                    let (status, body) = match path {
                        "/error" => (
                            500,
                            Bytes::from_static(b"{\"error\":\"internal_server_error\"}"),
                        ),
                        "/not_found" => (
                            404,
                            Bytes::from_static(b"{\"error\":\"not_found\"}"),
                        ),
                        _ => (
                            200,
                            Bytes::from_static(
                                b"{\"status\":\"ok\",\"engine\":\"argus\",\"payload\":{\"nodes\":100,\"active\":true}}",
                            ),
                        ),
                    };

                    Ok::<_, Infallible>(
                        Response::builder()
                            .status(status)
                            .header("content-type", "application/json")
                            .body(Full::new(body))
                            .unwrap(),
                    )
                });

                let _ = Builder::new(TokioExecutor::new())
                    .serve_connection(io, service)
                    .await;
            });
        }
    });

    (format!("http://{}", addr), addr)
}

/// Sets up connected client instance wired directly to actor loop
pub fn setup_client(base_url: &str) -> Client<Connected> {
    let (cmd_tx, cmd_rx) = tokio::sync::mpsc::channel(2048);
    let reqwest_client = reqwest::Client::builder()
        .pool_max_idle_per_host(200)
        .pool_idle_timeout(Duration::from_secs(60))
        .tcp_nodelay(true)
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
