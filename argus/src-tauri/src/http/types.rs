/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use std::collections::HashMap;

#[derive(serde::Serialize)]
struct ResponseMeta {
    status: u16,
    headers: HashMap<String, String>,
}

impl TryFrom<crate::http_client::types::TauriHttpResponse> for tauri::ipc::Response {
    type Error = super::error::Error;

    fn try_from(
        response: crate::http_client::types::TauriHttpResponse,
    ) -> Result<Self, Self::Error> {
        let meta = ResponseMeta {
            status: response.status,
            headers: response.headers,
        };

        let meta_json = serde_json::to_string(&meta)
            .map_err(|e| super::error::Error::InvalidState(e.to_string()))?;

        let meta_bytes = meta_json.as_bytes();

        let mut payload = Vec::with_capacity(4 + meta_bytes.len() + response.body.len());
        payload.extend_from_slice(&(meta_bytes.len() as u32).to_be_bytes());
        payload.extend_from_slice(meta_bytes);
        payload.extend_from_slice(&response.body);

        Ok(tauri::ipc::Response::new(payload))
    }
}

#[derive(serde::Serialize, Clone, Debug)]
#[serde(tag = "type", rename_all = "lowercase")]
pub enum StreamChunk {
    End,
    Error { message: String },
}

#[derive(serde::Serialize)]
pub struct HttpResponseHead {
    pub status: u16,
    pub headers: HashMap<String, String>,
}

#[derive(serde::Deserialize, serde::Serialize, Clone, Debug, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct FilePartDescriptor {
    pub field_name: String,
    pub file_name: String,
    pub local_path: std::path::PathBuf,
}

#[derive(serde::Deserialize, serde::Serialize, Clone, Debug, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct MultipartFieldDescriptor {
    pub name: String,
    pub value: String,
}

#[derive(serde::Deserialize, serde::Serialize, Clone, Debug, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct MultipartManifest {
    pub client_id: String,
    pub req_id: String,
    pub endpoint: String,
    pub method: String,
    pub headers: HashMap<String, String>,
    pub fields: Vec<MultipartFieldDescriptor>,
    pub files: Vec<FilePartDescriptor>,
}

#[derive(serde::Serialize)]
pub struct MultipartResponsePayload {
    pub status: u16,
    pub headers: HashMap<String, String>,
    pub body: String,
}

#[cfg(test)]
mod tests {
    use crate::http_client::types::TauriHttpResponse;
    use proptest::prelude::*;
    use std::collections::HashMap;

    proptest! {
        #[test]
        fn prop_tauri_response_wire_format(
            status in 100u16..600u16,
            headers in prop::collection::hash_map("[a-z0-9_-]{1,15}", "[a-zA-Z0-9_ -]{0,30}", 0..10),
            body in prop::collection::vec(any::<u8>(), 0..1024),
        ) {
            let tauri_resp = TauriHttpResponse {
                status,
                headers: headers.clone(),
                body: body.clone(),
            };

            let ipc_resp: tauri::ipc::Response = tauri_resp.try_into().expect("Serialization must succeed");
            let raw_bytes = match tauri::ipc::IpcResponse::body(ipc_resp).expect("Valid body") {
                tauri::ipc::InvokeResponseBody::Raw(b) => b,
                _ => panic!("Expected Raw payload"),
            };

            prop_assert!(raw_bytes.len() >= 4);

            let meta_len = u32::from_be_bytes(raw_bytes[0..4].try_into().unwrap()) as usize;
            prop_assert_eq!(raw_bytes.len(), 4 + meta_len + body.len());

            let meta_json = std::str::from_utf8(&raw_bytes[4..4 + meta_len]).expect("Meta must be valid utf8 JSON");
            let parsed_meta: serde_json::Value = serde_json::from_str(meta_json).expect("Meta must parse as JSON");

            prop_assert_eq!(parsed_meta["status"].as_u64().unwrap(), status as u64);

            let parsed_headers: HashMap<String, String> = serde_json::from_value(parsed_meta["headers"].clone()).unwrap();
            prop_assert_eq!(parsed_headers, headers);

            let parsed_body = &raw_bytes[4 + meta_len..];
            prop_assert_eq!(parsed_body, body.as_slice());
        }
    }
}
