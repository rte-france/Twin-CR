/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use std::collections::HashMap;
use std::time::Duration;

use std::hint::black_box;

use argus_lib::http_client::utils::http_client::client::{Client, Connected};
use criterion::{BenchmarkId, Criterion, Throughput};
use pprof::criterion::{Output, PProfProfiler};

use super::common::{setup_client, start_hyper_echo_server};

fn bench_http_methods_roundtrip(c: &mut Criterion) {
    let rt = tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .build()
        .unwrap();

    let (client, _server_url) = rt.block_on(async {
        let (base_url, _) = start_hyper_echo_server().await;
        let c = setup_client(&base_url);
        (c, base_url)
    });

    let mut group = c.benchmark_group("http_methods");
    group.measurement_time(Duration::from_secs(5));

    // Bodyless methods
    group.bench_function("get", |b| {
        b.to_async(&rt).iter(|| async {
            let rx = client
                .get(black_box("req-bench-get".into()), "/test", HashMap::new())
                .await
                .expect("send get");
            let resp = Client::<Connected>::wait_for_response(rx)
                .await
                .expect("wait response");
            black_box(resp);
        });
    });

    group.bench_function("delete", |b| {
        b.to_async(&rt).iter(|| async {
            let rx = client
                .delete(black_box("req-bench-del".into()), "/test", HashMap::new())
                .await
                .expect("send delete");
            let resp = Client::<Connected>::wait_for_response(rx)
                .await
                .expect("wait response");
            black_box(resp);
        });
    });

    group.bench_function("head", |b| {
        b.to_async(&rt).iter(|| async {
            let rx = client
                .head(black_box("req-bench-head".into()), "/test", HashMap::new())
                .await
                .expect("send head");
            let resp = Client::<Connected>::wait_for_response(rx)
                .await
                .expect("wait response");
            black_box(resp);
        });
    });

    group.bench_function("options", |b| {
        b.to_async(&rt).iter(|| async {
            let rx = client
                .options(black_box("req-bench-opt".into()), "/test", HashMap::new())
                .await
                .expect("send options");
            let resp = Client::<Connected>::wait_for_response(rx)
                .await
                .expect("wait response");
            black_box(resp);
        });
    });

    group.bench_function("trace", |b| {
        b.to_async(&rt).iter(|| async {
            let rx = client
                .trace(black_box("req-bench-trace".into()), "/test", HashMap::new())
                .await
                .expect("send trace");
            let resp = Client::<Connected>::wait_for_response(rx)
                .await
                .expect("wait response");
            black_box(resp);
        });
    });

    // Methods with body (standard 256 B payload)
    let body = bytes::Bytes::from_static(b"{\"bench\":true}");

    let body_post = body.clone();
    group.bench_function("post", |b| {
        let body = body_post.clone();
        b.to_async(&rt).iter(|| {
            let body = body.clone();
            async {
                let rx = client
                    .post(
                        black_box("req-bench-post".into()),
                        "/test",
                        HashMap::new(),
                        black_box(body),
                    )
                    .await
                    .expect("send post");
                let resp = Client::<Connected>::wait_for_response(rx)
                    .await
                    .expect("wait response");
                black_box(resp);
            }
        });
    });

    let body_put = body.clone();
    group.bench_function("put", |b| {
        let body = body_put.clone();
        b.to_async(&rt).iter(|| {
            let body = body.clone();
            async {
                let rx = client
                    .put(
                        black_box("req-bench-put".into()),
                        "/test",
                        HashMap::new(),
                        black_box(body),
                    )
                    .await
                    .expect("send put");
                let resp = Client::<Connected>::wait_for_response(rx)
                    .await
                    .expect("wait response");
                black_box(resp);
            }
        });
    });

    let body_patch = body.clone();
    group.bench_function("patch", |b| {
        let body = body_patch.clone();
        b.to_async(&rt).iter(|| {
            let body = body.clone();
            async {
                let rx = client
                    .patch(
                        black_box("req-bench-patch".into()),
                        "/test",
                        HashMap::new(),
                        black_box(body),
                    )
                    .await
                    .expect("send patch");
                let resp = Client::<Connected>::wait_for_response(rx)
                    .await
                    .expect("wait response");
                black_box(resp);
            }
        });
    });

    // Tauri IPC serialization cost
    group.bench_function("get_to_tauri_ipc_response", |b| {
        b.to_async(&rt).iter(|| async {
            let rx = client
                .get(black_box("req-bench-ipc".into()), "/test", HashMap::new())
                .await
                .expect("send get");
            let resp = Client::<Connected>::wait_for_response(rx)
                .await
                .expect("wait response");
            let ipc_resp: tauri::ipc::Response = resp.try_into().expect("ipc conversion");
            black_box(ipc_resp);
        });
    });

    group.finish();
}

fn bench_payload_scaling(c: &mut Criterion) {
    let rt = tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .build()
        .unwrap();

    let (client, _server_url) = rt.block_on(async {
        let (base_url, _) = start_hyper_echo_server().await;
        let c = setup_client(&base_url);
        (c, base_url)
    });

    let mut group = c.benchmark_group("payload_scaling");
    group.measurement_time(Duration::from_secs(5));

    for size in [256, 4096, 65536] {
        let payload = bytes::Bytes::from(vec![0x42u8; size]);
        group.throughput(Throughput::Bytes(size as u64));

        group.bench_with_input(BenchmarkId::from_parameter(size), &payload, |b, data| {
            let data = data.clone();
            b.to_async(&rt).iter(|| {
                let data = data.clone();
                async {
                    let rx = client
                        .post(
                            black_box("req-bench-scale".into()),
                            "/test",
                            HashMap::new(),
                            black_box(data),
                        )
                        .await
                        .expect("send post");
                    let resp = Client::<Connected>::wait_for_response(rx)
                        .await
                        .expect("wait response");
                    black_box(resp);
                }
            });
        });
    }

    group.finish();
}

pub fn run(args: Vec<String>) {
    let mut c = Criterion::default()
        .with_profiler(PProfProfiler::new(100, Output::Flamegraph(None)))
        .configure_from_args();

    // If custom args were passed (e.g. --quick), re-parse or configure if needed
    if !args.is_empty() {
        // Criterion doesn't expose a direct method to parse arbitrary Vec<String>,
        // but configure_from_args reads std::env::args(). When run via `cargo bench -- ...`,
        // std::env::args already has the CLI flags!
    }

    bench_http_methods_roundtrip(&mut c);
    bench_payload_scaling(&mut c);

    c.final_summary();
}
