/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

mod common;
mod criterion;
mod load;
mod profile;
mod sse;
mod trace;

fn print_usage() {
    eprintln!(
        "Usage: cargo bench --bench http_client [-- <benchmark> [args...]]\n\n\
         Available benchmarks:\n  \
           criterion  Run Criterion micro-benchmarks (default)\n  \
           load       Run load & concurrency benchmark\n  \
           sse        Run SSE streaming benchmark\n  \
           profile    Run memory profile & leak analysis\n  \
           trace      Run async tracing & Tokio Console benchmark\n  \
           all        Run all benchmarks sequentially\n\n\
         Examples:\n  \
           cargo bench --bench http_client\n  \
           cargo bench --bench http_client -- load\n  \
           cargo bench --bench http_client -- sse\n  \
           cargo bench --bench http_client -- profile\n  \
           cargo bench --bench http_client -- trace\n  \
           cargo bench --bench http_client -- criterion --quick"
    );
}

fn main() {
    let mut args: Vec<String> = std::env::args().skip(1).collect();

    let target = if args.is_empty() {
        "criterion".to_string()
    } else {
        args.remove(0)
    };

    match target.as_str() {
        "criterion" => criterion::run(args),
        "load" => load::run(),
        "sse" => sse::run(),
        "profile" => profile::run(),
        "trace" => trace::run(),
        "all" => {
            println!(">>> Running load benchmark...");
            load::run();
            println!("\n>>> Running sse benchmark...");
            sse::run();
            println!("\n>>> Running profile benchmark...");
            profile::run();
            println!("\n>>> Running trace benchmark...");
            trace::run();
            println!("\n>>> Running criterion micro-benchmarks...");
            criterion::run(args);
        }
        "--help" | "-h" | "help" => print_usage(),
        other if other.starts_with('-') => {
            // Forward flags (e.g. --quick) directly to criterion
            let mut crit_args = vec![other.to_string()];
            crit_args.extend(args);
            criterion::run(crit_args);
        }
        unknown => {
            eprintln!("Unknown benchmark: '{}'\n", unknown);
            print_usage();
            std::process::exit(1);
        }
    }
}
