/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use std::collections::HashMap;
use std::convert::Infallible;
use std::net::SocketAddr;
use std::time::{Duration, Instant};

use bytes::Bytes;
use hdrhistogram::Histogram;
use http_body_util::combinators::BoxBody;
use http_body_util::{BodyExt, StreamBody};
use hyper::service::service_fn;
use hyper::{Request, Response};
use hyper_util::rt::{TokioExecutor, TokioIo};
use hyper_util::server::conn::auto::Builder;
use tokio::net::TcpListener;
use tokio::sync::mpsc;

use super::common::setup_client;

async fn start_hyper_sse_server(events_count: usize) -> (String, SocketAddr) {
    let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let addr = listener.local_addr().unwrap();

    tokio::spawn(async move {
        loop {
            let (stream, _) = match listener.accept().await {
                Ok(conn) => conn,
                Err(_) => break,
            };

            tokio::spawn(async move {
                let io = TokioIo::new(stream);
                let service = service_fn(move |_req: Request<hyper::body::Incoming>| async move {
                    let (tx, rx) =
                        mpsc::channel::<Result<hyper::body::Frame<Bytes>, Infallible>>(128);

                    tokio::spawn(async move {
                        for i in 0..events_count {
                            let msg = format!(
                                "data: {{\"event_id\":{},\"payload\":\"bench_sse\"}}\n\n",
                                i
                            );
                            if tx
                                .send(Ok(hyper::body::Frame::data(Bytes::from(msg))))
                                .await
                                .is_err()
                            {
                                break;
                            }
                        }
                    });

                    let stream = futures_util::stream::unfold(rx, |mut rx| async move {
                        rx.recv().await.map(|item| (item, rx))
                    });
                    let stream_body = StreamBody::new(stream);
                    let boxed_body: BoxBody<Bytes, Infallible> = stream_body.boxed();

                    Ok::<_, Infallible>(
                        Response::builder()
                            .status(200)
                            .header("content-type", "text/event-stream")
                            .header("cache-control", "no-cache")
                            .header("connection", "keep-alive")
                            .body(boxed_body)
                            .unwrap(),
                    )
                });

                let _ = Builder::new(TokioExecutor::new())
                    .serve_connection(io, service)
                    .await;
            });
        }
    });

    (format!("http://{}", addr), addr)
}

pub fn run() {
    let rt = tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .build()
        .unwrap();
    rt.block_on(run_async());
}

async fn run_async() {
    let streams_count: usize = std::env::var("BENCH_SSE_STREAMS")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(20);

    let events_per_stream: usize = std::env::var("BENCH_SSE_EVENTS")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(5_000);

    let total_events = streams_count * events_per_stream;

    let (base_url, _) = start_hyper_sse_server(events_per_stream).await;
    let client = std::sync::Arc::new(setup_client(&base_url));

    println!("============================================================");
    println!("  SSE STREAMING BENCHMARK (Hyper stream -> SSE actor)");
    println!("  Concurrent streams : {}", streams_count);
    println!("  Events / stream    : {}", events_per_stream);
    println!("  Total events       : {}", total_events);
    println!("============================================================");

    let mut histogram = Histogram::<u64>::new_with_bounds(1, 60_000_000, 3).unwrap();
    let (hist_tx, mut hist_rx) = mpsc::unbounded_channel::<u64>();

    let start_instant = Instant::now();
    let mut handles = Vec::with_capacity(streams_count);

    for s in 0..streams_count {
        let client = client.clone();
        let tx = hist_tx.clone();
        let req_id = format!("sse-stream-{}", s);

        handles.push(tokio::spawn(async move {
            let mut event_rx = match client.sse(req_id.clone(), "/events", HashMap::new()).await {
                Ok(rx) => rx,
                Err(err) => {
                    eprintln!("Failed to start SSE stream {}: {:?}", req_id, err);
                    return 0usize;
                }
            };

            let mut count = 0usize;
            let mut last_instant = Instant::now();

            while let Some(res) = event_rx.recv().await {
                if res.is_ok() {
                    let micros = last_instant.elapsed().as_micros() as u64;
                    let _ = tx.send(micros);
                    last_instant = Instant::now();
                    count += 1;
                    if count >= events_per_stream {
                        break;
                    }
                } else {
                    break;
                }
            }

            let _ = client.cancel_request(req_id).await;
            count
        }));
    }

    drop(hist_tx);

    let hist_collector = tokio::spawn(async move {
        while let Some(micros) = hist_rx.recv().await {
            let _ = histogram.record(micros.max(1));
        }
        histogram
    });

    let mut received_events = 0;
    for h in handles {
        if let Ok(c) = h.await {
            received_events += c;
        }
    }

    let histogram = hist_collector.await.unwrap();
    let elapsed = start_instant.elapsed();
    let events_per_sec = (received_events as f64) / elapsed.as_secs_f64();

    println!("\n--- SSE STREAMING RESULTS ---");
    println!("Total time           : {:.2?}", elapsed);
    println!(
        "Events received      : {} / {}",
        received_events, total_events
    );
    println!("SSE throughput       : {:.0} events/s", events_per_sec);
    println!(
        "Inter-event p50      : {:?}",
        Duration::from_micros(histogram.value_at_quantile(0.50))
    );
    println!(
        "Inter-event p90      : {:?}",
        Duration::from_micros(histogram.value_at_quantile(0.90))
    );
    println!(
        "Inter-event p95      : {:?}",
        Duration::from_micros(histogram.value_at_quantile(0.95))
    );
    println!(
        "Inter-event p99      : {:?}",
        Duration::from_micros(histogram.value_at_quantile(0.99))
    );
    println!(
        "Inter-event Max      : {:?}",
        Duration::from_micros(histogram.max())
    );
}
