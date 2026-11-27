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

use argus_lib::http_client::utils::http_client::client::{Client, Connected};

use super::common::{setup_client, start_hyper_echo_server};

fn get_rss_bytes() -> usize {
    #[cfg(target_os = "macos")]
    {
        use std::mem::MaybeUninit;
        let mut task_info = MaybeUninit::<libc::mach_task_basic_info>::uninit();
        let mut count = (std::mem::size_of::<libc::mach_task_basic_info>()
            / std::mem::size_of::<libc::natural_t>())
            as libc::mach_msg_type_number_t;
        #[allow(deprecated)]
        let ret = unsafe {
            libc::task_info(
                libc::mach_task_self(),
                libc::MACH_TASK_BASIC_INFO,
                task_info.as_mut_ptr() as libc::task_info_t,
                &mut count,
            )
        };
        if ret == libc::KERN_SUCCESS {
            let info = unsafe { task_info.assume_init() };
            return info.resident_size as usize;
        }
    }
    #[cfg(target_os = "linux")]
    {
        if let Ok(statm) = std::fs::read_to_string("/proc/self/statm") {
            if let Some(pages) = statm
                .split_whitespace()
                .nth(1)
                .and_then(|s| s.parse::<usize>().ok())
            {
                let page_size = unsafe { libc::sysconf(libc::_SC_PAGESIZE) };
                if page_size > 0 {
                    return pages * (page_size as usize);
                }
            }
        }
    }
    0
}

pub fn run() {
    let rt = tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .build()
        .unwrap();
    rt.block_on(run_async());
}

async fn run_batch(
    client: &Arc<Client<Connected>>,
    path: &str,
    current_idx: &Arc<AtomicUsize>,
    target_idx: usize,
    concurrency: usize,
    completed: &Arc<AtomicUsize>,
) {
    let mut handles = Vec::with_capacity(concurrency);
    for _ in 0..concurrency {
        let client = client.clone();
        let completed = completed.clone();
        let current_idx = current_idx.clone();
        let path = path.to_string();

        handles.push(tokio::spawn(async move {
            loop {
                let i = match current_idx.fetch_update(Ordering::Relaxed, Ordering::Relaxed, |i| {
                    (i < target_idx).then(|| i + 1)
                }) {
                    Ok(i) => i,
                    Err(_) => break,
                };
                let req_id = format!("req-{}", i);
                if let Ok(rx) = client.get(req_id, &path, HashMap::new()).await {
                    if let Ok(resp) = Client::<Connected>::wait_for_response(rx).await {
                        std::hint::black_box(resp.body);
                        completed.fetch_add(1, Ordering::Relaxed);
                    }
                }
            }
        }));
    }

    for h in handles {
        let _ = h.await;
    }
}

async fn run_async() {
    let (base_url, _) = start_hyper_echo_server().await;
    let client = Arc::new(setup_client(&base_url));
    let path = std::env::var("PROFILE_PATH").unwrap_or_else(|_| "/large".to_string());

    let total_requests: usize = std::env::var("PROFILE_TOTAL")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(200_000);

    let n = total_requests / 2;
    let concurrency: usize = 100;
    let completed = Arc::new(AtomicUsize::new(0));

    let rss_initial = get_rss_bytes();

    println!("============================================================");
    println!("  HTTP ENGINE PROFILE: CPU, RAM & MEMORY LEAK ANALYSIS");
    println!(
        "  Total requests : {} (Phase 1: {}, Phase 2: {})",
        total_requests, n, n
    );
    println!("  Concurrency    : {}", concurrency);
    println!("============================================================");

    let current_idx = Arc::new(AtomicUsize::new(0));

    // Phase 1: N requests (warmup / reach steady-state)
    println!("Running Phase 1 (0 -> N requests: warmup & steady-state)...");
    let p1_start = Instant::now();
    run_batch(&client, &path, &current_idx, n, concurrency, &completed).await;
    let p1_elapsed = p1_start.elapsed();
    tokio::time::sleep(Duration::from_millis(200)).await;
    let rss_at_n = get_rss_bytes();

    // Phase 2: N additional requests (steady-state measurement: N -> 2N)
    println!("Running Phase 2 (N -> 2N requests: steady-state leak measurement)...");
    let p2_start = Instant::now();
    run_batch(&client, &path, &current_idx, 2 * n, concurrency, &completed).await;
    let p2_elapsed = p2_start.elapsed();
    tokio::time::sleep(Duration::from_millis(200)).await;
    let rss_at_2n = get_rss_bytes();

    let elapsed = p1_elapsed + p2_elapsed;
    let rss_after_cooldown = get_rss_bytes();

    let success_count = completed.load(Ordering::Relaxed);
    let rps = (success_count as f64) / elapsed.as_secs_f64();

    // Steady-state drift (RAM difference between N and 2N requests)
    let steady_drift_bytes = (rss_at_2n as i64) - (rss_at_n as i64);
    let bytes_per_req_drift = (steady_drift_bytes as f64) / (n as f64);

    println!("\n--- MEMORY & RESOURCE MEASUREMENTS ---");
    println!("Total time           : {:.2?}", elapsed);
    println!("Successful requests  : {}", success_count);
    println!("Average throughput   : {:.0} req/s", rps);
    println!(
        "Initial RAM (RSS)    : {:.2} MB",
        (rss_initial as f64) / (1024.0 * 1024.0)
    );
    println!(
        "Steady RAM @ N req   : {:.2} MB",
        (rss_at_n as f64) / (1024.0 * 1024.0)
    );
    println!(
        "Steady RAM @ 2N req  : {:.2} MB",
        (rss_at_2n as f64) / (1024.0 * 1024.0)
    );
    println!(
        "Post-cooldown RAM    : {:.2} MB",
        (rss_after_cooldown as f64) / (1024.0 * 1024.0)
    );
    println!(
        "Steady drift (N->2N) : {:+.2} MB ({:+.2} bytes/req)",
        (steady_drift_bytes as f64) / (1024.0 * 1024.0),
        bytes_per_req_drift
    );
}
