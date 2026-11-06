/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use reqwest::{Request, Response};
use reqwest_middleware::{Middleware, Next, Result as MiddlewareResult};

pub struct LoggingMiddleware;

#[async_trait::async_trait]
impl Middleware for LoggingMiddleware {
    async fn handle(
        &self,
        req: Request,
        extensions: &mut http::Extensions,
        next: Next<'_>,
    ) -> MiddlewareResult<Response> {
        let method = req.method().clone();

        let mut clean_url = req.url().clone();
        clean_url.set_query(None);

        let start = std::time::Instant::now();
        let res = next.run(req, extensions).await;
        let elapsed = start.elapsed().as_millis();

        match &res {
            Ok(response) => {
                let status = response.status();

                // Check slow requests (over 1 second)
                if elapsed > 1000 {
                    log::warn!(
                        target: "HTTP",
                        "SLOW: {} {} - {} ({}ms)",
                        method, clean_url, status, elapsed
                    );
                } else if !status.is_success() {
                    log::error!(
                        target: "HTTP",
                        "HTTP ERROR {}: {} {} ({}ms)",
                        status, method, clean_url, elapsed
                    );
                } else {
                    log::debug!(
                        target: "HTTP",
                        "{} {} - {} ({}ms)",
                        method, clean_url, status, elapsed
                    );
                }
            }
            Err(err) => {
                log::error!(
                    target: "HTTP",
                    "NETWORK ERROR: {} {} - {}",
                    method, clean_url, err
                );
            }
        }

        res
    }
}
