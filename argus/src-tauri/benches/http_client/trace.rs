/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use std::collections::HashMap;
use std::sync::Arc;
use std::time::Duration;

use argus_lib::http_client::utils::http_client::client::{Client, Connected};
use tracing::Instrument;

use super::common::{next_req_id, setup_client, start_hyper_echo_server};

pub fn run() {
    let rt = tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .build()
        .unwrap();
    rt.block_on(run_async());
}

async fn run_async() {
    let console_layer = if std::env::var("TOKIO_CONSOLE").is_ok() {
        println!(
            ">>> Tokio Console listener started on 127.0.0.1:6669 (run `tokio-console` to connect)"
        );
        Some(console_subscriber::spawn())
    } else {
        None
    };

    let (chrome_layer, _flush_guard) = if let Ok(trace_path) = std::env::var("TRACE_FILE") {
        let (layer, guard) = tracing_chrome::ChromeLayerBuilder::new()
            .file(&trace_path)
            .include_args(true)
            .build();
        println!(">>> Chrome trace recording to: {}", trace_path);
        println!("    Open in https://ui.perfetto.dev/ or chrome://tracing to view async spans");
        (Some(layer), Some(guard))
    } else {
        (None, None)
    };

    if console_layer.is_some() || chrome_layer.is_some() {
        use tracing_subscriber::layer::SubscriberExt;
        let subscriber = tracing_subscriber::Registry::default()
            .with(console_layer)
            .with(chrome_layer);
        tracing::subscriber::set_global_default(subscriber).expect("set global subscriber");
    }

    let total: usize = std::env::var("TRACE_TOTAL")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(5_000);

    let concurrency: usize = std::env::var("TRACE_CONCURRENCY")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(50);

    let (base_url, _) = start_hyper_echo_server().await;
    let client = Arc::new(setup_client(&base_url));

    println!("============================================================");
    println!("  ASYNC SPAN & TRACING BENCHMARK");
    println!("  Total requests : {}", total);
    println!("  Concurrency    : {}", concurrency);
    println!("============================================================");

    let start = std::time::Instant::now();
    let mut handles = Vec::with_capacity(concurrency);
    let counter = Arc::new(std::sync::atomic::AtomicUsize::new(0));

    for _ in 0..concurrency {
        let client = client.clone();
        let counter = counter.clone();

        handles.push(tokio::spawn(async move {
            loop {
                let idx = counter.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                if idx >= total {
                    break;
                }

                let span = tracing::info_span!("http_request_span", req_id = idx);
                async {
                    let req_id = next_req_id("trace-req");
                    if let Ok(rx) = client.get(req_id, "/test", HashMap::new()).await {
                        let _ = Client::<Connected>::wait_for_response(rx).await;
                    }
                }
                .instrument(span)
                .await;
            }
        }));
    }

    for h in handles {
        let _ = h.await;
    }

    let elapsed = start.elapsed();
    println!(
        "Tracing completed in {:.2?} ({:.0} req/s)",
        elapsed,
        (total as f64) / elapsed.as_secs_f64()
    );

    // Allow background flush
    tokio::time::sleep(Duration::from_millis(200)).await;
}
