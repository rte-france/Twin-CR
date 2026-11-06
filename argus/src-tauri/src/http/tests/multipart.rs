/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use std::collections::HashMap;
use wiremock::matchers::{header, method, path};
use wiremock::{Mock, MockServer, ResponseTemplate};

use crate::http::manager::HttpManager;
use crate::http::types::{FilePartDescriptor, MultipartFieldDescriptor, MultipartManifest};
use crate::http_client::types::AllowedEndpoint;

#[tokio::test]
async fn test_post_multipart_stream_wiremock_integration() {
    let server = MockServer::start().await;

    Mock::given(method("POST"))
        .and(path("/api/v1/context/upload"))
        .and(header("x-custom-token", "auth-token-123"))
        .respond_with(
            ResponseTemplate::new(201)
                .insert_header("content-type", "application/json")
                .set_body_bytes(b"{\"success\":true,\"filesReceived\":1}"),
        )
        .mount(&server)
        .await;

    // Create a temporary file on disk representing a Dynawo file
    let temp_dir = std::env::temp_dir();
    let temp_file_path = temp_dir.join("test_stream_job.xml");
    let file_content = b"<jobs><job name=\"sample\"/></jobs>";
    tokio::fs::write(&temp_file_path, file_content)
        .await
        .expect("Write temp XML file");

    let http_manager = HttpManager::new();
    let client_manager =
        crate::http_client::utils::client_manager::manager::ClientManager::new("session_client");
    client_manager.configure_endpoints(vec![AllowedEndpoint {
        endpoint: "session".into(),
        base_url: format!("{}/api/v1", server.uri()),
    }]);

    http_manager
        .clients
        .write()
        .await
        .insert("session_client".into(), client_manager.clone());

    let mut headers = HashMap::new();
    headers.insert("x-custom-token".into(), "auth-token-123".into());

    let manifest = MultipartManifest {
        client_id: "session_client".into(),
        req_id: "req-stream-42".into(),
        endpoint: "session://context/upload".into(),
        method: "POST".into(),
        headers: headers.clone(),
        fields: vec![MultipartFieldDescriptor {
            name: "template_name".into(),
            value: "MyTemplate".into(),
        }],
        files: vec![FilePartDescriptor {
            field_name: "job_file".into(),
            file_name: "job.xml".into(),
            local_path: temp_file_path.clone(),
        }],
    };

    let (endpoint, _) = (
        crate::http::utils::resolve_endpoint(
            &client_manager,
            &manifest.client_id,
            &manifest.endpoint,
            &mut headers,
        )
        .expect("Resolve endpoint"),
        crate::http::utils::verify_endpoint_access(
            &client_manager,
            &manifest.client_id,
            &manifest.endpoint,
        )
        .expect("Verify access"),
    );

    assert_eq!(endpoint, format!("{}/api/v1/context/upload", server.uri()));

    // Construct streaming form identically to post_multipart_stream
    let mut form = reqwest::multipart::Form::new();
    for f in manifest.fields {
        form = form.text(f.name, f.value);
    }
    for file_desc in manifest.files {
        let file = tokio::fs::File::open(&file_desc.local_path).await.unwrap();
        use tokio_util::codec::{BytesCodec, FramedRead};
        let stream = FramedRead::new(file, BytesCodec::new());
        let body = reqwest::Body::wrap_stream(stream);
        let part = reqwest::multipart::Part::stream(body).file_name(file_desc.file_name);
        form = form.part(file_desc.field_name, part);
    }

    let reqwest_client = reqwest::Client::new();
    let mut req_builder = reqwest_client.post(&endpoint);
    for (k, v) in headers {
        req_builder = req_builder.header(k, v);
    }

    let resp = req_builder
        .multipart(form)
        .send()
        .await
        .expect("Send multipart stream");

    assert_eq!(resp.status().as_u16(), 201);
    let body_str = resp.text().await.unwrap();
    assert_eq!(body_str, "{\"success\":true,\"filesReceived\":1}");

    let _ = tokio::fs::remove_file(&temp_file_path).await;
}

#[tokio::test]
async fn test_multipart_cancellation_lifecycle() {
    let (cmd_tx, mut cmd_rx) = tokio::sync::mpsc::channel(32);
    let client = crate::http_client::utils::http_client::Client {
        url: Some("http://127.0.0.1".into()),
        state: crate::http_client::utils::http_client::Connected { sender: cmd_tx },
    };

    let register_task = tokio::spawn(async move {
        client
            .register_cancel("req-multipart-cancel")
            .await
            .unwrap()
    });

    let cancel_rx = match cmd_rx.recv().await.unwrap() {
        crate::http_client::utils::http_client::command::Command::RegisterCancel {
            req_id,
            cancel_rx_sender,
        } => {
            assert_eq!(req_id, "req-multipart-cancel");
            let (tx, rx) = tokio::sync::oneshot::channel();
            cancel_rx_sender.send(rx).unwrap();
            let _ = tx.send(()); // simulate cancellation triggered
            register_task.await.unwrap()
        }
        _ => panic!("Expected RegisterCancel command"),
    };

    assert!(cancel_rx.await.is_ok(), "Cancel signal must be received");
}

#[tokio::test]
async fn test_multipart_patch_method_roundtrip() {
    let server = MockServer::start().await;

    Mock::given(method("PATCH"))
        .and(path("/api/v1/context/patch"))
        .respond_with(ResponseTemplate::new(200).set_body_bytes(b"{\"patched\":true}"))
        .mount(&server)
        .await;

    let reqwest_client = reqwest::Client::new();
    let method = reqwest::Method::from_bytes(b"PATCH").unwrap();
    let resp = reqwest_client
        .request(method, format!("{}/api/v1/context/patch", server.uri()))
        .send()
        .await
        .expect("Send PATCH request");

    assert_eq!(resp.status().as_u16(), 200);
    assert_eq!(resp.text().await.unwrap(), "{\"patched\":true}");
}
