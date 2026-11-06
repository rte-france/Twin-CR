/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use reqwest::multipart::{Form, Part};
use std::{collections::HashMap, sync::Arc};
use tauri::{ipc::InvokeResponseBody, AppHandle, Manager, State};
use tokio_util::codec::{BytesCodec, FramedRead};

use crate::{
    channel::manager::{ChannelGuard, ChannelTaskManager},
    http::{
        error::Error,
        types::{HttpResponseHead, MultipartManifest, MultipartResponsePayload},
        utils::stream_http_response,
    },
    http_client::utils::{
        client_manager::ClientManager,
        http_client::{Client, Connected},
    },
};

use super::error::Result;
use super::manager::HttpManager;
use super::utils::prepare_request;

#[tauri::command]
pub async fn get_registered_clients(
    http_manager: State<'_, Arc<HttpManager>>,
) -> Result<Vec<String>> {
    Ok(http_manager.get_registered_client_ids().await)
}

macro_rules! impl_http_command {
    ($fn_name:ident) => {
        #[tauri::command]
        pub async fn $fn_name(
            app_handle: AppHandle,
            task_manager: State<'_, ChannelTaskManager>,
            http_manager: State<'_, Arc<HttpManager>>,
            client_id: String,
            req_id: String,
            endpoint: String,
            mut headers: HashMap<String, String>,
            on_chunk: tauri::ipc::Channel<InvokeResponseBody>,
        ) -> Result<HttpResponseHead> {
            let (client, endpoint) = prepare_request(
                &app_handle,
                &http_manager,
                &client_id,
                &endpoint,
                &mut headers,
            )
            .await?;

            let response_rx = client.$fn_name(req_id.clone(), endpoint, headers).await?;
            stream_http_response(task_manager.inner(), req_id, response_rx, on_chunk).await
        }
    };
}

macro_rules! impl_http_command_with_body {
    ($fn_name:ident) => {
        #[tauri::command]
        pub async fn $fn_name(
            app_handle: AppHandle,
            task_manager: State<'_, ChannelTaskManager>,
            http_manager: State<'_, Arc<HttpManager>>,
            client_id: String,
            req_id: String,
            endpoint: String,
            mut headers: HashMap<String, String>,
            body: Vec<u8>,
            on_chunk: tauri::ipc::Channel<InvokeResponseBody>,
        ) -> Result<HttpResponseHead> {
            let (client, endpoint) = prepare_request(
                &app_handle,
                &http_manager,
                &client_id,
                &endpoint,
                &mut headers,
            )
            .await?;

            let response_rx = client
                .$fn_name(req_id.clone(), endpoint, headers, body)
                .await?;
            stream_http_response(task_manager.inner(), req_id, response_rx, on_chunk).await
        }
    };
}

impl_http_command!(get);
impl_http_command!(delete);
impl_http_command!(head);
impl_http_command!(options);
impl_http_command!(trace);

impl_http_command_with_body!(post);
impl_http_command_with_body!(put);
impl_http_command_with_body!(patch);

#[tauri::command]
pub async fn sse(
    app_handle: AppHandle,
    task_manager: State<'_, ChannelTaskManager>,
    http_manager: State<'_, Arc<HttpManager>>,
    client_id: String,
    req_id: String,
    endpoint: String,
    mut headers: HashMap<String, String>,
    on_event: tauri::ipc::Channel<String>,
) -> Result<()> {
    let manager_arc = task_manager.inner().clone();
    let channel_id = on_event.id();
    let mut cancel_rx = task_manager.register(&on_event);

    let (client, endpoint) = prepare_request(
        &app_handle,
        &http_manager,
        &client_id,
        &endpoint,
        &mut headers,
    )
    .await?;

    let mut response_rx = client.sse(req_id.clone(), endpoint, headers).await?;

    tokio::spawn(async move {
        let _guard = ChannelGuard {
            channel_id,
            manager: Arc::new(manager_arc),
        };

        loop {
            tokio::select! {
                _ = &mut cancel_rx => {
                    log::info!(target: "HTTP_SSE", "SSE stream cancelled manually for {}.", req_id);
                    break;
                }
                maybe_result = response_rx.recv() => {
                    match maybe_result {
                        Some(Ok(bytes)) => {
                            let text = String::from_utf8_lossy(&bytes).to_string();
                            if on_event.send(text).is_err() {
                                log::info!(target: "HTTP_SSE", "Frontend disconnected (F5/Reload). Terminating {}.", req_id);
                                break;
                            }
                        }
                        _ => {
                            let _ = on_event.send("ERROR: Stream closed".to_string());
                            break;
                        }
                    }
                }
            }
        }

        let _ = on_event.send("[CLOSE]".to_string());
    });

    Ok(())
}

#[tauri::command]
pub async fn post_multipart_stream(
    app_handle: AppHandle,
    http_manager: State<'_, Arc<HttpManager>>,
    manifest: MultipartManifest,
) -> Result<MultipartResponsePayload> {
    let mut headers = manifest.headers;
    let (client, endpoint) = prepare_request(
        &app_handle,
        &http_manager,
        &manifest.client_id,
        &manifest.endpoint,
        &mut headers,
    )
    .await?;

    let manager =
        super::utils::get_connected_client(&http_manager, &app_handle, &manifest.client_id).await?;

    let mut form = Form::new();

    // Add scalar fields
    for field in manifest.fields {
        form = form.text(field.name, field.value);
    }

    // Stream files: O(1) RAM via chunks
    for file_desc in manifest.files {
        let file = tokio::fs::File::open(&file_desc.local_path)
            .await
            .map_err(|e| {
                Error::Generic(format!(
                    "Cannot open {}: {}",
                    file_desc.local_path.display(),
                    e
                ))
            })?;

        let metadata = file.metadata().await.map_err(|e| {
            Error::Generic(format!(
                "Cannot read metadata for {}: {}",
                file_desc.local_path.display(),
                e
            ))
        })?;
        let file_len = metadata.len();

        let stream = FramedRead::new(file, BytesCodec::new());
        let body = reqwest::Body::wrap_stream(stream);
        let part = Part::stream_with_length(body, file_len).file_name(file_desc.file_name);

        form = form.part(file_desc.field_name, part);
    }

    let method = reqwest::Method::from_bytes(manifest.method.as_bytes())
        .map_err(|_| Error::Generic(format!("Invalid HTTP method: {}", manifest.method)))?;

    let (proxy, no_proxy) = app_handle
        .try_state::<crate::config::manager::ConfigManager>()
        .map(|config| {
            let settings = config.settings.load().load();
            (settings.proxy.clone(), settings.no_proxy.clone())
        })
        .unwrap_or((None, None));

    let primary_url = manager
        .endpoints
        .load()
        .first()
        .map(|e| e.base_url.clone())
        .unwrap_or_else(|| endpoint.clone());

    let disconnected = crate::http_client::utils::http_client::Client::with_url(&primary_url);
    let reqwest_client = disconnected.build_base_client(proxy, no_proxy)?;

    let mut req_builder = reqwest_client.request(method, &endpoint);

    for (k, v) in headers {
        req_builder = req_builder.header(k, v);
    }

    let mut cancel_rx = client.register_cancel(&manifest.req_id).await?;

    let response = tokio::select! {
        res = req_builder.multipart(form).send() => {
            res.map_err(|e| Error::Generic(e.to_string()))?
        }
        _ = &mut cancel_rx => {
            return Err(Error::InvalidState(format!(
                "Multipart request {} cancelled",
                manifest.req_id
            )));
        }
    };

    let status = response.status().as_u16();
    let response_headers = response
        .headers()
        .iter()
        .map(|(k, v)| (k.to_string(), v.to_str().unwrap_or("").to_string()))
        .collect();

    let mut stream = response.bytes_stream();
    use futures_util::StreamExt;
    let mut body_bytes = Vec::new();

    loop {
        tokio::select! {
            chunk_opt = stream.next() => match chunk_opt {
                Some(Ok(bytes)) => body_bytes.extend_from_slice(&bytes),
                Some(Err(e)) => return Err(Error::Generic(format!("Failed to read response body: {e}"))),
                None => break,
            },
            _ = &mut cancel_rx => {
                return Err(Error::InvalidState(format!(
                    "Multipart request {} cancelled while reading body",
                    manifest.req_id
                )));
            }
        }
    }

    let body = String::from_utf8(body_bytes)
        .map_err(|e| Error::Generic(format!("Response body is not valid UTF-8: {e}")))?;

    Ok(MultipartResponsePayload {
        status,
        headers: response_headers,
        body,
    })
}

#[tauri::command]
pub async fn active_ping(
    http_manager: State<'_, Arc<HttpManager>>,
    client_id: String,
) -> Result<()> {
    log::info!(target: "HTTP", "Starting active ping for client: {}", client_id);

    if let Some(manager) = http_manager.get_client(&client_id).await {
        let client_arc = manager.client.load();

        if let Ok(connected_client) = ClientManager::get_connected(&client_arc) {
            let req_id = format!(
                "ping-{}-{}",
                client_id,
                std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap_or_default()
                    .as_millis()
            );

            let headers = std::collections::HashMap::new();

            log::debug!(target: "Ping", "Sending HEAD request to / for {}", client_id);

            match connected_client
                .head(req_id, "/".to_string(), headers)
                .await
            {
                Ok(response_rx) => {
                    tokio::spawn(async move {
                        let _ = Client::<Connected>::wait_for_response(response_rx).await;
                    });
                }
                Err(e) => {
                    log::warn!(target: "Ping", "Failed to send ping for {}: {:?}", client_id, e);
                }
            }
        }
    } else {
        log::warn!(target: "Ping", "Client {} not found for ping", client_id);
    }

    Ok(())
}

#[tauri::command]
pub async fn cancel_http_request(
    http_manager: State<'_, Arc<HttpManager>>,
    client_id: String,
    req_id: String,
) -> Result<()> {
    log::info!(
        target: "HTTP",
        "Cancellation request received for request {} on client {}",
        req_id,
        client_id
    );

    if let Some(manager) = http_manager.get_client(&client_id).await {
        let client_arc = manager.client.load();
        if let Ok(connected_client) = ClientManager::get_connected(&client_arc) {
            let _ = connected_client.cancel_request(req_id).await;
        }
    }

    Ok(())
}
