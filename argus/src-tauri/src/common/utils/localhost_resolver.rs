/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

//! DNS resolver of the HTTP clients: `localhost` and its subdomains (e.g. `keycloak.localhost`, the Keycloak of a local
//! Nomad infrastructure) are the loopback addresses (RFC 6761), as in browsers; other names use the system resolver.
//! Windows only resolves `localhost` itself, not its subdomains.

use std::net::{IpAddr, Ipv4Addr, Ipv6Addr, SocketAddr};

use reqwest::dns::{Addrs, Name, Resolve, Resolving};

pub struct LocalhostResolver;

/// Whether the host name is `localhost` or one of its subdomains (case and trailing dot ignored).
fn is_localhost(host: &str) -> bool {
    let host = host.trim_end_matches('.').to_ascii_lowercase();
    host == "localhost" || host.ends_with(".localhost")
}

impl Resolve for LocalhostResolver {
    fn resolve(&self, name: Name) -> Resolving {
        let host = name.as_str().to_string();
        Box::pin(async move {
            if is_localhost(&host) {
                let loopback = [IpAddr::V4(Ipv4Addr::LOCALHOST), IpAddr::V6(Ipv6Addr::LOCALHOST)];
                let addrs: Addrs = Box::new(loopback.into_iter().map(|ip| SocketAddr::new(ip, 0)));
                return Ok(addrs);
            }
            // The port is set by the client: 0 here, as with the default resolver
            let addrs = tokio::net::lookup_host((host.as_str(), 0)).await?;
            Ok(Box::new(addrs.collect::<Vec<_>>().into_iter()) as Addrs)
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn localhost_and_its_subdomains_only() {
        assert!(is_localhost("localhost"));
        assert!(is_localhost("keycloak.localhost"));
        assert!(is_localhost("Keycloak.LocalHost."));
        assert!(!is_localhost("localhost.example.org"));
        assert!(!is_localhost("mylocalhost"));
    }
}
