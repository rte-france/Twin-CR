/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use std::convert::Infallible;
use std::net::SocketAddr;

use bytes::Bytes;
use http_body_util::{BodyExt, Full};
use hyper::service::service_fn;
use hyper::{Request, Response};
use hyper_util::rt::{TokioExecutor, TokioIo};
use hyper_util::server::conn::auto::Builder;
use tokio::net::TcpListener;

use argus_lib::http_client::utils::http_client::actor::run_http_client_actor;
use argus_lib::http_client::utils::http_client::client::{Client, Connected};
use argus_lib::http_client::utils::http_client::Disconnected;

/// Fast loopback HTTP server with zero serialization overhead
pub async fn start_hyper_echo_server() -> (String, SocketAddr) {
    let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let addr = listener.local_addr().unwrap();
    let large_payload = Bytes::from(vec![0x42u8; 64 * 1024]);

    tokio::spawn(async move {
        loop {
            let (stream, _) = match listener.accept().await {
                Ok(conn) => conn,
                Err(_) => break,
            };

            let large_payload = large_payload.clone();
            tokio::spawn(async move {
                let io = TokioIo::new(stream);
                let service = service_fn(move |req: Request<hyper::body::Incoming>| {
                    let large_payload = large_payload.clone();
                    async move {
                        let path = req.uri().path().to_string();

                        // Collect incoming body (keeps HTTP/1.1 keep-alive clean and retrieves payload for /echo)
                        let incoming_bytes = match req.into_body().collect().await {
                            Ok(collected) => collected.to_bytes(),
                            Err(_) => Bytes::new(),
                        };

                        let (status, content_type, body) = match path.as_str() {
                            "/echo" => (200, "application/octet-stream", incoming_bytes),
                            "/large" => (200, "application/octet-stream", large_payload),
                            "/error" => (
                                500,
                                "application/json",
                                Bytes::from_static(b"{\"error\":\"internal_server_error\"}"),
                            ),
                            "/not_found" => (
                                404,
                                "application/json",
                                Bytes::from_static(b"{\"error\":\"not_found\"}"),
                            ),
                            _ => (
                                200,
                                "application/json",
                                Bytes::from_static(
                                    b"{\"status\":\"ok\",\"engine\":\"argus\",\"payload\":{\"nodes\":100,\"active\":true}}",
                                ),
                            ),
                        };

                        Ok::<_, Infallible>(
                            Response::builder()
                                .status(status)
                                .header("content-type", content_type)
                                .body(Full::new(body))
                                .unwrap(),
                        )
                    }
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

    let disconnected_client = Client {
        url: Some(base_url.to_string()),
        state: Disconnected,
    };

    let reqwest_client = disconnected_client
        .build_base_client(None, None)
        .expect("Failed to build base reqwest client");

    let client = reqwest_middleware::ClientBuilder::new(reqwest_client).build();

    let url = base_url.to_string();
    tokio::spawn(run_http_client_actor(client, url.clone(), cmd_rx));

    Client {
        url: Some(url),
        state: Connected { sender: cmd_tx },
    }
}
