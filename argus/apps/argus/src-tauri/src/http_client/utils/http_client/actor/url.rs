/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use reqwest_middleware::RequestBuilder;
use std::collections::HashMap;

pub fn build_api_url(base_url: &str, endpoint: &str) -> String {
    if endpoint.starts_with("http://") || endpoint.starts_with("https://") {
        return endpoint.to_string();
    }

    if base_url.is_empty() {
        return endpoint.trim_start_matches('/').to_string();
    }

    format!(
        "{}/{}",
        base_url.trim_end_matches('/'),
        endpoint.trim_start_matches('/')
    )
}

pub(crate) fn apply_headers(
    mut builder: RequestBuilder,
    headers: HashMap<String, String>,
) -> RequestBuilder {
    for (k, v) in headers {
        builder = builder.header(&k, &v);
    }
    builder
}
