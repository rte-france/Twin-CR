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

async fn run_async() {
    let (base_url, _) = start_hyper_echo_server().await;
    let client = Arc::new(setup_client(&base_url));

    let total_requests: usize = std::env::var("PROFILE_TOTAL")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(200_000);

    let concurrency: usize = 100;
    let completed = Arc::new(AtomicUsize::new(0));

    let rss_initial = get_rss_bytes();
    let mut rss_peak = rss_initial;

    println!("============================================================");
    println!("  HTTP ENGINE PROFILE: CPU, RAM & MEMORY LEAK ANALYSIS");
    println!("  Total requests : {}", total_requests);
    println!("  Concurrency    : {}", concurrency);
    println!("============================================================");

    let completed_monitor = completed.clone();
    let monitor_handle = tokio::spawn(async move {
        let mut peak = 0;
        let mut history = Vec::new();
        let start = Instant::now();
        loop {
            let rss = get_rss_bytes();
            if rss > peak {
                peak = rss;
            }
            let done = completed_monitor.load(Ordering::Relaxed);
            history.push((start.elapsed(), done, rss));
            if done >= total_requests {
                break;
            }
            tokio::time::sleep(Duration::from_millis(100)).await;
        }
        (peak, history)
    });

    let start_instant = Instant::now();
    let mut handles = Vec::with_capacity(concurrency);
    let current_idx = Arc::new(AtomicUsize::new(0));

    for _ in 0..concurrency {
        let client = client.clone();
        let completed = completed.clone();
        let current_idx = current_idx.clone();

        handles.push(tokio::spawn(async move {
            loop {
                let i = current_idx.fetch_add(1, Ordering::Relaxed);
                if i >= total_requests {
                    break;
                }
                let req_id = format!("req-{}", i);
                if let Ok(rx) = client.get(req_id, "/test", HashMap::new()).await {
                    if Client::<Connected>::wait_for_response(rx).await.is_ok() {
                        completed.fetch_add(1, Ordering::Relaxed);
                    }
                }
            }
        }));
    }

    for h in handles {
        let _ = h.await;
    }

    let elapsed = start_instant.elapsed();
    let (peak, _history) = monitor_handle.await.unwrap();
    rss_peak = rss_peak.max(peak);

    // Yield runtime to let completed futures drop and GC settle
    tokio::time::sleep(Duration::from_millis(500)).await;
    let rss_after_cooldown = get_rss_bytes();

    let success_count = completed.load(Ordering::Relaxed);
    let rps = (success_count as f64) / elapsed.as_secs_f64();

    println!("\n--- MEMORY & RESOURCE MEASUREMENTS ---");
    println!("Total time           : {:.2?}", elapsed);
    println!("Successful requests  : {}", success_count);
    println!("Average throughput   : {:.0} req/s", rps);
    println!(
        "Initial RAM (RSS)    : {:.2} MB",
        (rss_initial as f64) / (1024.0 * 1024.0)
    );
    println!(
        "Peak RAM (Peak RSS)  : {:.2} MB",
        (rss_peak as f64) / (1024.0 * 1024.0)
    );
    println!(
        "Post-cooldown RAM    : {:.2} MB",
        (rss_after_cooldown as f64) / (1024.0 * 1024.0)
    );
    println!(
        "Memory / Request     : {:.2} bytes (in-flight)",
        ((rss_peak - rss_initial) as f64) / (concurrency as f64)
    );
}
