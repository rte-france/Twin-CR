/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use std::collections::HashMap;
use std::time::Duration;
use wiremock::matchers::{body_bytes, header, method, path};
use wiremock::{Mock, MockServer, ResponseTemplate};

use crate::http_client::utils::http_client::actor::run_http_client_actor;
use crate::http_client::utils::http_client::client::{Client, Connected};

fn setup_actor(base_url: &str) -> Client<Connected> {
    let (cmd_tx, cmd_rx) = tokio::sync::mpsc::channel(32);
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

#[tokio::test]
async fn test_get_request_wiremock_roundtrip() {
    let server = MockServer::start().await;

    Mock::given(method("GET"))
        .and(path("/api/v1/resource"))
        .and(header("X-Custom-Header", "HelloWiremock"))
        .respond_with(
            ResponseTemplate::new(200)
                .set_body_bytes(b"{\"status\":\"ok\"}")
                .insert_header("content-type", "application/json"),
        )
        .mount(&server)
        .await;

    let client = setup_actor(&server.uri());

    let mut headers = HashMap::new();
    headers.insert("X-Custom-Header".into(), "HelloWiremock".into());

    let rx = client
        .get("req-get-1".into(), "/api/v1/resource", headers)
        .await
        .expect("Dispatch GET");

    let tauri_resp = Client::<Connected>::wait_for_response(rx)
        .await
        .expect("Receive response");

    assert_eq!(tauri_resp.status, 200);
    assert_eq!(
        tauri_resp.headers.get("content-type").map(|s| s.as_str()),
        Some("application/json")
    );
    assert_eq!(tauri_resp.body, b"{\"status\":\"ok\"}");

    let ipc_resp: tauri::ipc::Response = tauri_resp.try_into().expect("TryInto tauri Response");
    let raw = match tauri::ipc::IpcResponse::body(ipc_resp).expect("Valid body") {
        tauri::ipc::InvokeResponseBody::Raw(b) => b,
        _ => panic!("Expected Raw payload"),
    };

    let meta_len = u32::from_be_bytes(raw[0..4].try_into().unwrap()) as usize;
    let meta_json = std::str::from_utf8(&raw[4..4 + meta_len]).unwrap();
    assert!(meta_json.contains("\"status\":200"));
    assert_eq!(&raw[4 + meta_len..], b"{\"status\":\"ok\"}");
}

#[tokio::test]
async fn test_post_binary_payload_wiremock_roundtrip() {
    let server = MockServer::start().await;
    let payload = vec![0xCA, 0xFE, 0xBA, 0xBE, 0x01, 0x02, 0x03];

    Mock::given(method("POST"))
        .and(path("/api/binary"))
        .and(body_bytes(payload.clone()))
        .respond_with(ResponseTemplate::new(201).set_body_bytes(b"ACK"))
        .mount(&server)
        .await;

    let client = setup_actor(&server.uri());

    let rx = client
        .post(
            "req-post-bin".into(),
            "/api/binary",
            HashMap::new(),
            payload.clone(),
        )
        .await
        .expect("Dispatch POST");

    let tauri_resp = Client::<Connected>::wait_for_response(rx)
        .await
        .expect("Receive response");

    assert_eq!(tauri_resp.status, 201);
    assert_eq!(tauri_resp.body, b"ACK");
}

#[tokio::test]
async fn test_server_500_error_mapped_in_response() {
    let server = MockServer::start().await;

    Mock::given(method("GET"))
        .and(path("/api/fail"))
        .respond_with(ResponseTemplate::new(500).set_body_bytes(b"Internal Error"))
        .mount(&server)
        .await;

    let client = setup_actor(&server.uri());

    let rx = client
        .get("req-err-1".into(), "/api/fail", HashMap::new())
        .await
        .expect("Dispatch GET");

    let tauri_resp = Client::<Connected>::wait_for_response(rx)
        .await
        .expect("Receive response");

    assert_eq!(tauri_resp.status, 500);
    assert_eq!(tauri_resp.body, b"Internal Error");
}

#[tokio::test]
async fn test_sse_streaming_over_wiremock() {
    let server = MockServer::start().await;

    let sse_body = "data: first event\n\ndata: second event\n\n";

    Mock::given(method("GET"))
        .and(path("/sse/events"))
        .respond_with(
            ResponseTemplate::new(200)
                .insert_header("content-type", "text/event-stream")
                .set_body_bytes(sse_body.as_bytes()),
        )
        .mount(&server)
        .await;

    let client = setup_actor(&server.uri());

    let mut event_rx = client
        .sse("req-sse-1".into(), "/sse/events", HashMap::new())
        .await
        .expect("Dispatch SSE");

    let first = event_rx
        .recv()
        .await
        .expect("Receive first chunk")
        .expect("Ok chunk");
    assert_eq!(first, bytes::Bytes::from("data: first event\n\n"));

    let second = event_rx
        .recv()
        .await
        .expect("Receive second chunk")
        .expect("Ok chunk");
    assert_eq!(second, bytes::Bytes::from("data: second event\n\n"));

    client
        .cancel_request("req-sse-1".into())
        .await
        .expect("Cancel SSE stream");
}

#[tokio::test]
async fn test_multipart_streaming_upload_roundtrip() {
    let server = MockServer::start().await;

    Mock::given(method("POST"))
        .and(path("/api/upload"))
        .respond_with(
            ResponseTemplate::new(200)
                .set_body_bytes(b"{\"uploaded\":true}")
                .insert_header("content-type", "application/json"),
        )
        .mount(&server)
        .await;

    let temp_dir = std::env::temp_dir();
    let temp_file_path = temp_dir.join("test_wiremock_upload.txt");
    tokio::fs::write(&temp_file_path, b"streaming file content hello wiremock")
        .await
        .expect("Write temp file");

    let file = tokio::fs::File::open(&temp_file_path)
        .await
        .expect("Open temp file");

    use tokio_util::codec::{BytesCodec, FramedRead};
    let stream = FramedRead::new(file, BytesCodec::new());
    let body = reqwest::Body::wrap_stream(stream);
    let part = reqwest::multipart::Part::stream(body).file_name("test_wiremock_upload.txt");

    let form = reqwest::multipart::Form::new()
        .text("description", "sample upload")
        .part("file", part);

    let client = reqwest::Client::new();
    let response = client
        .post(format!("{}/api/upload", server.uri()))
        .multipart(form)
        .send()
        .await
        .expect("Send multipart request");

    assert_eq!(response.status().as_u16(), 200);
    let resp_bytes = response.bytes().await.expect("Read response bytes");
    assert_eq!(resp_bytes.as_ref(), b"{\"uploaded\":true}");

    let _ = tokio::fs::remove_file(&temp_file_path).await;
}
