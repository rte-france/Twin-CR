/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use crate::http::utils::{resolve_endpoint, verify_endpoint_access};
use crate::http_client::types::AllowedEndpoint;
use crate::http_client::utils::client_manager::ClientManager;
use proptest::prelude::*;
use std::collections::HashMap;

proptest! {
    #[test]
    fn prop_verify_and_resolve_allowed_endpoint(
        alias in "[a-z]{3,8}",
        base_url in "https://api\\.[a-z]{3,10}\\.com(/)?",
        path in "(/)?[a-z0-9_]{1,10}(/[a-z0-9_]{1,10})*",
    ) {
        let manager = ClientManager::new("test_ext");
        manager.configure_endpoints(vec![AllowedEndpoint {
            endpoint: alias.clone(),
            base_url: base_url.clone(),
        }]);

        let requested_url = format!("{}://{}", alias, path);

        let access_res = verify_endpoint_access(&manager, "test_ext", &requested_url);
        prop_assert!(access_res.is_ok());

        let mut headers = HashMap::new();
        let resolved = resolve_endpoint(&manager, "test_ext", &requested_url, &mut headers).unwrap();

        let expected_base = base_url.trim_end_matches('/');
        let expected_path = path.trim_start_matches('/');
        prop_assert_eq!(resolved, format!("{}/{}", expected_base, expected_path));

        prop_assert_eq!(headers.get("Accept").map(|s| s.as_str()), Some("application/json"));
    }

    #[test]
    fn prop_verify_endpoint_blocks_unauthorized_alias(
        registered_alias in "[a-z]{3,5}",
        unauthorized_alias in "[a-z]{6,10}",
        path in "[a-z0-9/]{1,10}",
    ) {
        let manager = ClientManager::new("test_ext");
        manager.configure_endpoints(vec![AllowedEndpoint {
            endpoint: registered_alias,
            base_url: "https://api.example.com".into(),
        }]);

        let bad_url = format!("{}://{}", unauthorized_alias, path);
        prop_assert!(verify_endpoint_access(&manager, "test_ext", &bad_url).is_err());
    }

    #[test]
    fn prop_direct_http_and_https_bypass_verification(
        proto in "https?://",
        domain in "[a-z]{3,10}\\.com",
        path in "(/[a-z0-9_]{1,10})*",
    ) {
        let manager = ClientManager::new("direct");
        let direct_url = format!("{}{}{}", proto, domain, path);

        let access_res = verify_endpoint_access(&manager, "direct", &direct_url);
        prop_assert!(access_res.is_ok());

        let mut headers = HashMap::new();
        let resolved = resolve_endpoint(&manager, "direct", &direct_url, &mut headers).unwrap();
        prop_assert_eq!(resolved, direct_url);
        prop_assert_eq!(headers.get("Accept").map(|s| s.as_str()), Some("application/json"));
    }

    #[test]
    fn prop_multipart_manifest_serde_roundtrip(
        client_id in "[a-z0-9_-]{1,10}",
        req_id in "[a-z0-9_-]{1,10}",
        endpoint in "https://api\\.[a-z]{3,10}\\.com/[a-z]{1,5}",
        method in prop::sample::select(vec!["POST".to_string(), "PUT".to_string()]),
        field_count in 0usize..4,
        file_count in 0usize..4,
    ) {
        use crate::http::types::{MultipartManifest, MultipartFieldDescriptor, FilePartDescriptor};

        let fields: Vec<MultipartFieldDescriptor> = (0..field_count)
            .map(|i| MultipartFieldDescriptor {
                name: format!("field_{}", i),
                value: format!("value_{}", i),
            })
            .collect();

        let files: Vec<FilePartDescriptor> = (0..file_count)
            .map(|i| FilePartDescriptor {
                field_name: format!("file_{}", i),
                file_name: format!("upload_{}.txt", i),
                local_path: std::path::PathBuf::from(format!("/tmp/test_{}.txt", i)),
            })
            .collect();

        let manifest = MultipartManifest {
            client_id: client_id.clone(),
            req_id: req_id.clone(),
            endpoint: endpoint.clone(),
            method: method.clone(),
            headers: HashMap::new(),
            fields,
            files,
        };

        // CamelCase serialization check (matching JS IPC payload)
        let json = serde_json::to_string(&manifest).unwrap();
        prop_assert!(json.contains("clientId"));
        prop_assert!(json.contains("reqId"));
        if file_count > 0 {
            prop_assert!(json.contains("fieldName"));
            prop_assert!(json.contains("fileName"));
            prop_assert!(json.contains("localPath"));
        }

        let deserialized: MultipartManifest = serde_json::from_str(&json).unwrap();
        prop_assert_eq!(deserialized.client_id, client_id);
        prop_assert_eq!(deserialized.req_id, req_id);
        prop_assert_eq!(deserialized.endpoint, endpoint);
        prop_assert_eq!(deserialized.method, method);
        prop_assert_eq!(deserialized.fields.len(), field_count);
        prop_assert_eq!(deserialized.files.len(), file_count);
    }
}
