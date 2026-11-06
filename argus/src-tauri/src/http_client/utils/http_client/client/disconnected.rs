/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use reqwest::header::{HeaderMap, HeaderValue, ACCEPT, USER_AGENT};
use reqwest_middleware::{ClientBuilder as MiddlewareClientBuilder, ClientWithMiddleware};
use std::net::IpAddr;
use std::time::Duration;
use tokio::sync::mpsc;

use super::super::actor;
use super::super::command::Command;
use super::super::error::{Error, Result};
use super::super::middlewares::LoggingMiddleware;
use super::connected::Connected;
use super::private::Sealed;
use super::{Client, ClientState, HasUrlExt};

#[derive(Debug, Clone)]
pub struct Disconnected;

impl Sealed for Disconnected {}
impl ClientState for Disconnected {}

impl HasUrlExt for Client<Disconnected> {
    fn url(&self) -> &str {
        self.url
            .as_ref()
            .expect("URL must be set in Disconnected state")
    }
}

fn is_private_or_local_host(host: &str) -> bool {
    if host.eq_ignore_ascii_case("localhost") || !host.contains('.') {
        return true;
    }

    // IP RFC 1918
    if let Ok(ip) = host.parse::<IpAddr>() {
        match ip {
            IpAddr::V4(ipv4) => ipv4.is_loopback() || ipv4.is_private() || ipv4.is_link_local(),
            IpAddr::V6(ipv6) => ipv6.is_loopback(),
        }
    } else {
        false
    }
}

impl Client<Disconnected> {
    pub async fn connect(
        self,
        client_name: String,
        app_handle: tauri::AppHandle,
        proxy: Option<String>,
        no_proxy: Option<Vec<String>>,
    ) -> Result<Client<Connected>> {
        let base_client = self.build_base_client(proxy, no_proxy)?;

        let client_with_middleware = self.setup_middlewares(client_name, app_handle, base_client);

        let (sender, cmd_rx) = mpsc::channel::<Command>(1024);
        let base_url = self.url().to_string();

        tokio::spawn(async move {
            actor::run_http_client_actor(client_with_middleware, base_url, cmd_rx).await;
        });

        Ok(Client {
            url: self.url,
            state: Connected { sender },
        })
    }

    pub fn build_base_client(
        &self,
        proxy: Option<String>,
        no_proxy: Option<Vec<String>>,
    ) -> Result<reqwest::Client> {
        let mut default_headers = HeaderMap::new();
        default_headers.insert(USER_AGENT, HeaderValue::from_static("Argus/0.2"));
        default_headers.insert(ACCEPT, HeaderValue::from_static("*/*"));

        let mut builder = reqwest::Client::builder()
            .default_headers(default_headers)
            .danger_accept_invalid_certs(true)
            .danger_accept_invalid_hostnames(true)
            .pool_max_idle_per_host(100)
            .pool_idle_timeout(Duration::from_secs(90))
            .connect_timeout(Duration::from_secs(15))
            .read_timeout(Duration::from_mins(3))
            .tcp_keepalive(Duration::from_secs(15))
            .http2_keep_alive_interval(Duration::from_secs(15))
            .http2_keep_alive_while_idle(true);

        let is_target_private_or_local = reqwest::Url::parse(self.url())
            .ok()
            .and_then(|u| u.host_str().map(is_private_or_local_host))
            .unwrap_or(false);

        if is_target_private_or_local {
            return builder
                .no_proxy()
                .build()
                .map_err(|e| Error::from_reqwest(e, self.url().to_string()));
        }

        let effective_proxy = proxy.or_else(|| {
            std::env::var("HTTP_PROXY")
                .or_else(|_| std::env::var("http_proxy"))
                .or_else(|_| std::env::var("HTTPS_PROXY"))
                .or_else(|_| std::env::var("https_proxy"))
                .or_else(|_| std::env::var("ALL_PROXY"))
                .or_else(|_| std::env::var("all_proxy"))
                .ok()
        });

        if let Some(proxy_url) = effective_proxy {
            let mut reqwest_proxy = reqwest::Proxy::all(&proxy_url)
                .map_err(|e| Error::from_reqwest(e, self.url().to_string()))?;

            let mut bypass_list = vec![
                "localhost".to_string(),
                "127.0.0.1".to_string(),
                "0.0.0.0".to_string(),
                "::1".to_string(),
            ];

            let effective_no_proxy = no_proxy.or_else(|| {
                std::env::var("NO_PROXY")
                    .or_else(|_| std::env::var("no_proxy"))
                    .ok()
                    .map(|v| {
                        v.split(',')
                            .map(|s| s.trim().to_string())
                            .filter(|s| !s.is_empty())
                            .collect()
                    })
            });

            if let Some(user_rules) = effective_no_proxy {
                bypass_list.extend(user_rules);
            }

            let no_proxy_string = bypass_list.join(",");
            reqwest_proxy =
                reqwest_proxy.no_proxy(reqwest::NoProxy::from_string(no_proxy_string.as_str()));

            builder = builder.proxy(reqwest_proxy);
        }

        builder
            .build()
            .map_err(|e| Error::from_reqwest(e, self.url().to_string()))
    }

    fn setup_middlewares(
        &self,
        _client_name: String,
        _app_handle: tauri::AppHandle,
        base_client: reqwest::Client,
    ) -> ClientWithMiddleware {
        MiddlewareClientBuilder::new(base_client)
            .with(LoggingMiddleware)
            .build()
    }
}
