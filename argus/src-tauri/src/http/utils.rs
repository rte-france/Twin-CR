/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use std::{collections::HashMap, sync::Arc};
use tauri::{ipc::InvokeResponseBody, AppHandle};

use crate::{
    channel::manager::{ChannelGuard, ChannelTaskManager},
    http::types::HttpResponseHead,
    http_client::utils::{
        client_manager::ClientManager,
        http_client::{Client, Connected},
    },
};

use super::error::{Error, Result};
use super::manager::HttpManager;

pub async fn get_connected_client(
    http_manager: &HttpManager,
    app_handle: &AppHandle,
    client_id: &str,
) -> Result<Arc<ClientManager>> {
    http_manager
        .get_or_resolve_client(client_id, app_handle)
        .await
        .map_err(Error::InvalidState)
}

/// Parses a requested endpoint string into (alias, path).
/// Supports:
/// - Explicit client scheme: `clientId://alias/path` (when `scheme == client_id`)
/// - Direct alias scheme: `alias://path`
/// - Path format: `alias/path`
fn parse_endpoint_alias_and_path<'a>(client_id: &str, raw: &'a str) -> Result<(&'a str, &'a str)> {
    if let Some((scheme, rest)) = raw.split_once("://") {
        if scheme == client_id {
            // Format: "clientId://alias/path" or "clientId://alias//path"
            let rest_trimmed = rest.trim_start_matches('/');
            let (alias, path) = rest_trimmed.split_once('/').unwrap_or((rest_trimmed, ""));
            let path_clean = path.trim_start_matches('/');
            return Ok((alias, path_clean));
        }
        // Format: "alias://path" or "alias:////path"
        let path_clean = rest.trim_start_matches('/');
        return Ok((scheme, path_clean));
    }

    let raw_trimmed = raw.trim_start_matches('/');
    if let Some((alias, path)) = raw_trimmed.split_once('/') {
        let path_clean = path.trim_start_matches('/');
        return Ok((alias, path_clean));
    }

    Ok((raw_trimmed, ""))
}

pub fn verify_endpoint_access(
    manager: &ClientManager,
    client_id: &str,
    endpoint: &str,
) -> Result<()> {
    // Direct absolute HTTP/HTTPS URLs bypass allowed_endpoints verification
    if endpoint.starts_with("http://") || endpoint.starts_with("https://") {
        return Ok(());
    }

    let endpoints = manager.endpoints.load();
    let (requested_alias, _) = parse_endpoint_alias_and_path(client_id, endpoint)?;

    let is_allowed = endpoints
        .iter()
        .any(|allowed| allowed.endpoint == requested_alias);

    if !is_allowed {
        let allowed_list: Vec<String> = endpoints.iter().map(|a| a.endpoint.clone()).collect();
        let allowed_str = allowed_list.join(", ");

        log::warn!(
            "Security Blocked: Client '{}' attempted to access alias '{}'. Allowed aliases: [{}]",
            client_id,
            requested_alias,
            allowed_str
        );

        return Err(Error::InvalidState(format!(
            "Endpoint '{}' access blocked by manifest. Requested: '{}', Allowed: [{}]",
            endpoint, requested_alias, allowed_str
        )));
    }

    Ok(())
}

pub fn resolve_endpoint(
    manager: &ClientManager,
    client_id: &str,
    requested_url: &str,
    headers: &mut HashMap<String, String>,
) -> Result<String> {
    if !headers.contains_key("Accept") {
        headers.insert("Accept".to_string(), "application/json".to_string());
    }

    // Direct absolute HTTP/HTTPS URLs require no alias rewrite
    if requested_url.starts_with("http://") || requested_url.starts_with("https://") {
        return Ok(requested_url.to_string());
    }

    let (alias, path) = parse_endpoint_alias_and_path(client_id, requested_url)?;

    let endpoints = manager.endpoints.load();
    let allowed = endpoints
        .iter()
        .find(|a| a.endpoint == alias)
        .ok_or_else(|| {
            log::warn!(
                "Security: Client '{}' attempted to use unauthorized alias: '{}'",
                client_id,
                alias
            );
            Error::InvalidState("Network access blocked by manifest".into())
        })?;

    let base = allowed.base_url.trim_end_matches('/');
    let path_clean = path.trim_start_matches('/');

    if path_clean.is_empty() {
        Ok(base.to_string())
    } else {
        Ok(format!("{}/{}", base, path_clean))
    }
}

pub async fn prepare_request(
    app_handle: &AppHandle,
    http_manager: &HttpManager,
    client_id: &str,
    endpoint: &str,
    headers: &mut HashMap<String, String>,
) -> Result<(Arc<Client<Connected>>, String)> {
    let manager = get_connected_client(http_manager, app_handle, client_id).await?;

    verify_endpoint_access(&manager, client_id, endpoint)?;

    let resolved_url = resolve_endpoint(&manager, client_id, endpoint, headers)?;

    let client_arc = manager.client.load();
    let client = ClientManager::get_connected(&client_arc)?;

    Ok((client, resolved_url))
}

pub async fn stream_http_response(
    task_manager: &ChannelTaskManager,
    req_id: String,
    response_rx: tokio::sync::oneshot::Receiver<
        crate::http_client::utils::http_client::error::Result<
            crate::http_client::types::HttpResponse,
        >,
    >,
    on_chunk: tauri::ipc::Channel<InvokeResponseBody>,
) -> Result<super::types::HttpResponseHead> {
    let manager_arc = task_manager.clone();
    let channel_id = on_chunk.id();
    let mut cancel_rx = task_manager.register(&on_chunk);

    let http_response = response_rx
        .await
        .map_err(|_| crate::http_client::utils::http_client::error::Error::ActorClosed)??;

    let head = HttpResponseHead {
        status: http_response.status,
        headers: http_response.headers,
    };

    let mut body_rx = http_response.body_rx;

    tokio::spawn(async move {
        let _guard = ChannelGuard {
            channel_id,
            manager: Arc::new(manager_arc),
        };

        let mut error_msg: Option<String> = None;

        loop {
            tokio::select! {
                _ = &mut cancel_rx => {
                    log::info!(target: "HTTP", "Stream cancelled manually for {}.", req_id);
                    break;
                }
                maybe_chunk = body_rx.recv() => {
                    match maybe_chunk {
                        Some(Ok(bytes)) => {
                            if on_chunk
                                .send(InvokeResponseBody::Raw(bytes.to_vec()))
                                .is_err()
                            {
                                log::info!(target: "HTTP", "Frontend disconnected (F5/Cancel) for {}.", req_id);
                                break;
                            }
                        }
                        Some(Err(e)) => {
                            log::warn!(target: "HTTP", "Stream chunk error for {}: {}", req_id, e);
                            error_msg = Some(e.to_string());
                            break;
                        }
                        None => break,
                    }
                }
            }
        }

        let terminal_chunk = match error_msg {
            Some(message) => super::types::StreamChunk::Error { message },
            None => super::types::StreamChunk::End,
        };
        if let Ok(json) = serde_json::to_string(&terminal_chunk) {
            let _ = on_chunk.send(InvokeResponseBody::Json(json));
        }
    });

    Ok(head)
}
