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

use super::common::{setup_client, start_hyper_echo_server};

pub fn run() {
    let rt = tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .build()
        .unwrap();
    rt.block_on(run_async());
}

async fn run_async() {
    // 1. Optional Tokio Console Server (set TOKIO_CONSOLE=1)
    if std::env::var("TOKIO_CONSOLE").is_ok() {
        console_subscriber::init();
        println!(
            ">>> Tokio Console listener started on 127.0.0.1:6669 (run `tokio-console` to connect)"
        );
    }

    // 2. Optional Chrome Tracing / Perfetto JSON exporter (set TRACE_FILE=trace.json)
    let _flush_guard = if let Ok(trace_path) = std::env::var("TRACE_FILE") {
        let (chrome_layer, guard) = tracing_chrome::ChromeLayerBuilder::new()
            .file(&trace_path)
            .include_args(true)
            .build();
        use tracing_subscriber::layer::SubscriberExt;
        let subscriber = tracing_subscriber::Registry::default().with(chrome_layer);
        tracing::subscriber::set_global_default(subscriber).expect("set global subscriber");
        println!(">>> Chrome trace recording to: {}", trace_path);
        println!("    Open in https://ui.perfetto.dev/ or chrome://tracing to view async spans");
        Some(guard)
    } else {
        None
    };

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
                let _enter = span.enter();

                let req_id = format!("trace-req-{}", idx);
                if let Ok(rx) = client.get(req_id, "/test", HashMap::new()).await {
                    let _ = Client::<Connected>::wait_for_response(rx).await;
                }
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
