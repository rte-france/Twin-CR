/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use std::collections::HashMap;
use std::hint::black_box;
use std::time::Duration;

use criterion::{BatchSize, BenchmarkId, Criterion, Throughput};
#[cfg(unix)]
use pprof::criterion::{Output, PProfProfiler};

use argus_lib::http_client::{
    types::TauriHttpResponse,
    utils::http_client::client::{Client, Connected},
};

use super::common::{next_req_id, setup_client, start_hyper_echo_server};

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
                .get(next_req_id("req-bench-get"), "/test", HashMap::new())
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
                .delete(next_req_id("req-bench-del"), "/test", HashMap::new())
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
                .head(next_req_id("req-bench-head"), "/test", HashMap::new())
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
                .options(next_req_id("req-bench-opt"), "/test", HashMap::new())
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
                .trace(next_req_id("req-bench-trace"), "/test", HashMap::new())
                .await
                .expect("send trace");
            let resp = Client::<Connected>::wait_for_response(rx)
                .await
                .expect("wait response");
            black_box(resp);
        });
    });

    // Methods with body (14 B JSON payload)
    let body = bytes::Bytes::from_static(b"{\"bench\":true}");

    let body_post = body.clone();
    group.bench_function("post", |b| {
        let body = body_post.clone();
        b.to_async(&rt).iter(|| {
            let body = body.clone();
            async {
                let rx = client
                    .post(
                        next_req_id("req-bench-post"),
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
                        next_req_id("req-bench-put"),
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
                        next_req_id("req-bench-patch"),
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

    // Pure Tauri IPC serialization cost (isolated from HTTP roundtrip)
    let sample_headers = HashMap::from([
        ("content-type".to_string(), "application/json".to_string()),
        ("x-request-id".to_string(), "req-bench-ipc".to_string()),
    ]);
    let sample_body =
        b"{\"status\":\"ok\",\"engine\":\"argus\",\"payload\":{\"nodes\":100,\"active\":true}}"
            .to_vec();

    group.bench_function("tauri_ipc_serialization", |b| {
        b.iter_batched(
            || TauriHttpResponse {
                status: 200,
                headers: sample_headers.clone(),
                body: sample_body.clone(),
            },
            |resp| {
                let ipc_resp: tauri::ipc::Response =
                    black_box(resp).try_into().expect("ipc conversion");
                black_box(ipc_resp);
            },
            BatchSize::SmallInput,
        );
    });

    // End-to-end HTTP roundtrip + Tauri IPC serialization
    group.bench_function("get_e2e_ipc", |b| {
        b.to_async(&rt).iter(|| async {
            let rx = client
                .get(next_req_id("req-bench-ipc"), "/test", HashMap::new())
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
        group.throughput(Throughput::Bytes((size * 2) as u64));

        group.bench_with_input(BenchmarkId::from_parameter(size), &payload, |b, data| {
            let data = data.clone();
            b.to_async(&rt).iter(|| {
                let data = data.clone();
                async {
                    let rx = client
                        .post(
                            next_req_id("req-bench-scale"),
                            "/echo",
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
    let is_quick = args.iter().any(|a| a == "--quick");
    let has_custom_criterion_args = args.iter().any(|a| a != "--bench" && a != "--quick");

    let mut builder = if is_quick {
        Criterion::default()
            .sample_size(10)
            .warm_up_time(Duration::from_millis(500))
            .measurement_time(Duration::from_secs(1))
    } else if has_custom_criterion_args {
        Criterion::default().configure_from_args()
    } else {
        Criterion::default()
    };

    #[cfg(unix)]
    {
        builder = builder.with_profiler(PProfProfiler::new(100, Output::Flamegraph(None)));
    }

    let mut c = builder;

    bench_http_methods_roundtrip(&mut c);
    bench_payload_scaling(&mut c);

    c.final_summary();
}
