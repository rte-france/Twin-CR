# Argus Benchmarks

This directory contains performance and scalability benchmarks for the Argus engine. Benchmarks are organized by domain under subdirectories (e.g., `benches/http_client/`).

---

## HTTP Client Benchmarks (`benches/http_client/`)

Measures the internal `http_client` actor engine (`Client<Connected>`, Tokio channels, and Tauri IPC conversions).

To eliminate external network latency and mock server lock contention, benchmarks run against an in-memory loopback HTTP server powered by **Hyper v1.12** (`benches/http_client/common.rs`).

All HTTP client benchmarks are unified under a single entry point: `benches/http_client/main.rs`.

### Available Benchmarks

| Subcommand  | Module                             | Description                                                                                                         |
| ----------- | ---------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `criterion` | `benches/http_client/criterion.rs` | Micro-benchmarks for channel dispatch roundtrip, Tauri IPC serialization, and payload scaling (default).            |
| `load`      | `benches/http_client/load.rs`      | Concurrency, backpressure, and in-flight cancellation stress using `hdrhistogram`.                                  |
| `sse`       | `benches/http_client/sse.rs`       | High-throughput concurrent Server-Sent Events streaming and inter-event latency.                                    |
| `profile`   | `benches/http_client/profile.rs`   | Real-time memory footprint (RSS) and leak detection over 200,000+ requests.                                         |
| `trace`     | `benches/http_client/trace.rs`     | Async span timeline exporter (Chrome / Perfetto JSON) and Tokio Console server.                                     |
| `all`       | All of the above                   | Executes all benchmarks sequentially.                                                                               |

---

## How to Run

### General Usage

```bash
cargo bench --bench http_client [-- <benchmark> [args...]]
```

Run help to inspect available subcommands:

```bash
cargo bench --bench http_client -- --help
```

---

### 1. Load & Concurrency Benchmark (`load`)

```bash
cargo bench --bench http_client -- load
```

Customizable via environment variables:

```bash
BENCH_TOTAL=20000 BENCH_CONCURRENCY=200 BENCH_CANCEL_RATE=0.20 cargo bench --bench http_client -- load
```

- `BENCH_TOTAL`: Total requests to dispatch (default: `10000`).
- `BENCH_CONCURRENCY`: Maximum concurrent worker tasks (default: `100`).
- `BENCH_CANCEL_RATE`: Ratio of requests cancelled in-flight (default: `0.20` for 20%).

### 2. Micro-benchmarks (`criterion`)

Full statistical run (default when no subcommand is specified):

```bash
cargo bench --bench http_client
# or explicitly:
cargo bench --bench http_client -- criterion
```

Fast run (reduced sampling iterations):

```bash
cargo bench --bench http_client -- criterion --quick
# or directly:
cargo bench --bench http_client -- --quick
```

HTML reports are generated automatically in `target/criterion/`.

### 3. SSE Streaming Benchmark (`sse`)

```bash
cargo bench --bench http_client -- sse
```

Customizable via environment variables:

```bash
BENCH_SSE_STREAMS=100 BENCH_SSE_EVENTS=5000 cargo bench --bench http_client -- sse
```

- `BENCH_SSE_STREAMS`: Number of concurrent streams (default: `20`).
- `BENCH_SSE_EVENTS`: Events per stream (default: `5000`).

### 4. Memory Profile & Leak Analysis (`profile`)

```bash
cargo bench --bench http_client -- profile
```

Customizable via environment variables:

```bash
PROFILE_TOTAL=300000 cargo bench --bench http_client -- profile
```

- `PROFILE_TOTAL`: Total requests to dispatch (default: `200000`).

### 5. Async Tracing & Flamegraphs

#### Flamegraphs (CPU profiling via Criterion + pprof)

Run criterion micro-benchmarks; flamegraphs will be automatically saved under `target/criterion/<group>/<benchmark>/profile/flamegraph.svg`:

```bash
cargo bench --bench http_client -- criterion
```

#### Async Timeline Spans (Chrome / Perfetto JSON)

Export a timeline trace file of async request spans:

```bash
TRACE_FILE="trace.json" TRACE_TOTAL=5000 cargo bench --bench http_client -- trace
```

Open `trace.json` in [https://ui.perfetto.dev/](https://ui.perfetto.dev/) or `chrome://tracing` to inspect `.await` latency and span timelines.

#### Tokio Console (Live async task monitor)

Start the benchmark with Tokio Console support:

```bash
TOKIO_CONSOLE=1 cargo bench --bench http_client -- trace
```

In another terminal, connect using:

```bash
tokio-console
```
