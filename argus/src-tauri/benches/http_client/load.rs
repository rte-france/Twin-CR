/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use std::collections::HashMap;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};

use hdrhistogram::Histogram;
use rand::RngExt;
use tokio::sync::Semaphore;

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
    let (base_url, _) = start_hyper_echo_server().await;
    let client = Arc::new(setup_client(&base_url));

    let total_requests: usize = std::env::var("BENCH_TOTAL")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(10_000);

    let concurrency: usize = std::env::var("BENCH_CONCURRENCY")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(100);

    let cancel_rate: f64 = std::env::var("BENCH_CANCEL_RATE")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(0.20); // 20% default

    println!("============================================================");
    println!("  LOAD & CONCURRENCY BENCHMARK (hyper + hdrhistogram)");
    println!("  Total requests : {}", total_requests);
    println!("  Concurrency    : {}", concurrency);
    println!("  Cancel rate    : {:.0}%", cancel_rate * 100.0);
    println!("============================================================");

    let semaphore = Arc::new(Semaphore::new(concurrency));
    let mut histogram_service = Histogram::<u64>::new_with_bounds(1, 60_000_000, 3).unwrap();
    let mut histogram_total = Histogram::<u64>::new_with_bounds(1, 60_000_000, 3).unwrap();
    let (hist_tx, mut hist_rx) = tokio::sync::mpsc::unbounded_channel::<(u64, u64)>();

    let completed = Arc::new(AtomicUsize::new(0));
    let cancelled = Arc::new(AtomicUsize::new(0));
    let errors = Arc::new(AtomicUsize::new(0));

    let start_instant = Instant::now();
    let mut handles = Vec::with_capacity(total_requests);

    for i in 0..total_requests {
        let sem = semaphore.clone();
        let client = client.clone();
        let tx = hist_tx.clone();
        let completed = completed.clone();
        let cancelled = cancelled.clone();
        let errors = errors.clone();

        handles.push(tokio::spawn(async move {
            let scheduled_time = Instant::now();
            let _permit = sem.acquire().await.unwrap();
            let service_start = Instant::now();
            let req_id = format!("req-{}", i);

            let should_cancel = cancel_rate > 0.0 && rand::rng().random_bool(cancel_rate);

            let rx = match client.get(req_id.clone(), "/test", HashMap::new()).await {
                Ok(rx) => rx,
                Err(_) => {
                    errors.fetch_add(1, Ordering::Relaxed);
                    return;
                }
            };

            if should_cancel {
                let _ = client.cancel_request(req_id).await;
                cancelled.fetch_add(1, Ordering::Relaxed);
                return;
            }

            match Client::<Connected>::wait_for_response(rx).await {
                Ok(_) => {
                    let service_micros = service_start.elapsed().as_micros() as u64;
                    let total_micros = scheduled_time.elapsed().as_micros() as u64;
                    let _ = tx.send((service_micros, total_micros));
                    completed.fetch_add(1, Ordering::Relaxed);
                }
                Err(_) => {
                    errors.fetch_add(1, Ordering::Relaxed);
                }
            }
        }));
    }

    drop(hist_tx);

    while let Some((service_micros, total_micros)) = hist_rx.recv().await {
        let _ = histogram_service.record(service_micros);
        let _ = histogram_total.record(total_micros);
    }

    for h in handles {
        let _ = h.await;
    }

    let elapsed = start_instant.elapsed();
    let success_count = completed.load(Ordering::Relaxed);
    let cancel_count = cancelled.load(Ordering::Relaxed);
    let error_count = errors.load(Ordering::Relaxed);
    let effective_rps = (success_count as f64) / elapsed.as_secs_f64();
    let throughput_total = (total_requests as f64) / elapsed.as_secs_f64();

    println!("\n--- LOAD TEST RESULTS ---");
    println!("Total time           : {:.2?}", elapsed);
    println!("Successful requests  : {}", success_count);
    println!("Cancelled requests   : {}", cancel_count);
    println!("Errors               : {}", error_count);
    println!("Effective throughput : {:.0} req/s", effective_rps);
    println!("Total throughput     : {:.0} req/s", throughput_total);
    println!(
        "Service Latency p50  : {:?}",
        Duration::from_micros(histogram_service.value_at_quantile(0.50))
    );
    println!(
        "Service Latency p90  : {:?}",
        Duration::from_micros(histogram_service.value_at_quantile(0.90))
    );
    println!(
        "Service Latency p99  : {:?}",
        Duration::from_micros(histogram_service.value_at_quantile(0.99))
    );
    println!(
        "End-to-End Latency p50 (inc. queue): {:?}",
        Duration::from_micros(histogram_total.value_at_quantile(0.50))
    );
    println!(
        "End-to-End Latency p90 (inc. queue): {:?}",
        Duration::from_micros(histogram_total.value_at_quantile(0.90))
    );
    println!(
        "End-to-End Latency p99 (inc. queue): {:?}",
        Duration::from_micros(histogram_total.value_at_quantile(0.99))
    );
    println!(
        "End-to-End Latency p99.9 (inc. queue): {:?}",
        Duration::from_micros(histogram_total.value_at_quantile(0.999))
    );
    println!(
        "End-to-End Latency Max               : {:?}",
        Duration::from_micros(histogram_total.max())
    );
}
