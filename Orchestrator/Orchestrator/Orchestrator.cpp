/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "Orchestrator.h"
#include "EventQueue.h"
#include "Information.h"
#include "SignalHandler.h"
#include "../utils/TomlExtension.h"

#include <fmt/core.h>
#include <spdlog/spdlog.h>

#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdlib>
#include <optional>
#include <thread>

Orchestrator::Orchestrator(const std::filesystem::path& working_dir, const toml::table& config, double start_time, double end_time, const std::optional<std::string> simulation_name) :
working_dir_(working_dir),
config_(config),
current_time_(start_time),
paused_(true),
last_warning_time_(start_time),
start_time_(start_time),
last_time_update_(start_time),
end_time_(end_time),
real_start_time_(steady_clock::now()),
initial_clock_time_(std::chrono::system_clock::now()),
simulation_name_(simulation_name.has_value() ? simulation_name.value() : "sim_" + getTimestamp()),
main_thread_id_(std::this_thread::get_id()) {
    SignalHandler::create();
    speedup_ = config["master"]["speedup"].value_or(1.0);
    period_ = get_or_throw<double>(config, {"master", "period"});
    if (period_ <= 0) {
        throw std::invalid_argument(fmt::format("master.period must be strictly positive, got {}", period_));
    }
    dump_period_ = config["master"]["dump_period"].value_or(-1.0);
    if (dump_period_ > 0) {
        // A dump has to land on a time step, else periodic calls will be shifted after a dump/reload cycle
        double periods_per_dump = dump_period_ / period_;
        double rounded = std::round(periods_per_dump);
        if (rounded < 1 || std::abs(periods_per_dump - rounded) > 1e-9 * rounded) {
            throw std::invalid_argument(fmt::format(
                "master.dump_period ({}) must be a whole multiple of master.period ({}), got {} periods",
                dump_period_, period_, periods_per_dump));
        }
    }
    spdlog::info("Initializing simulation {}", simulation_name_);

    if (true)
        event_queue_ = std::make_unique<StrictEventQueue>();
    else
        event_queue_ = std::make_unique<NonStrictEventQueue>();

    resetRealTimeClock(start_time);  // Make the clock start from start_time
    // Reset the real-time clock once Dynawo has replied for the first time (otherwise the simulation will start with a lag
    // if Dynawo takes too much time for initialisation)
    scheduleEvent(
        start_time + 2 * period_,
        makeCallback<&Orchestrator::resetRealTimeClock>(this, start_time + 2 * period_)
    );

    dump_tick_index_ = 1;
    double next_dump_time = start_time_ + dump_tick_index_ * dump_period_;
    if (dump_period_ > 0 && next_dump_time < end_time_) {
        scheduleEvent(
            next_dump_time,
            makeCallback<&Orchestrator::emitDumpStateEvent>(this, DumpStateEvent(next_dump_time)),
            Event::Order::Dump
        );
    }
}

void Orchestrator::resetRealTimeClock(double elapsed_time) {
    real_start_time_ = steady_clock::now() - std::chrono::milliseconds(int(elapsed_time * 1000 / speedup_));
}

void Orchestrator::run(std::optional<double> run_to_time) {
    paused_ = false;
    while (!event_queue_->isEmpty() && !SignalHandler::gotExitSignal() && current_time_ <= end_time_) {
        if (run_to_time.has_value()) {
            if (event_queue_->nextTimeStep() > *run_to_time) {
                break;
            }
        }
        waitUntilNextEvent();
        Event event = event_queue_->popNext();
        current_time_ = event.time;
        while (current_time_ >= last_time_update_ + period_ && !SignalHandler::gotExitSignal()) {
            // Guarantee the TimeUpdate is always the first event of the period, regardless of the event queue implementation
            time_update_tick_index_++;
            last_time_update_ = start_time_ + time_update_tick_index_ * period_;  // Not last_time_update += period_ to avoid floating point error drift
            emit(TimeUpdate(last_time_update_));
            spdlog::info("Time update: {}", last_time_update_);
        }
        event.doEvent();
    }
}

void Orchestrator::pause() {
    paused_ = true;
}

void Orchestrator::resume() {
    speedup_ = 1;
    resetRealTimeClock(current_time_);
    paused_ = false;
}

void Orchestrator::fastForward() {
    speedup_ = 999;
    resetRealTimeClock(current_time_);
    paused_ = false;
}

void Orchestrator::emitDumpStateEvent(const DumpStateEvent& event) {
    emit(event);

    spdlog::info("Dumping simulation state at t={}", current_time_.load());

    dump_tick_index_++;
    double next_dump_time = start_time_ + dump_tick_index_ * dump_period_;
    if (next_dump_time < end_time_) {
        scheduleEvent(
            next_dump_time,
            makeCallback<&Orchestrator::emitDumpStateEvent>(this, DumpStateEvent(next_dump_time)),
            Event::Order::Dump
        );
    }
}

void Orchestrator::waitUntilNextEvent() {
    while (!SignalHandler::gotExitSignal()) {
        if (paused_) {
            // Wait by 100ms interval while the simulation is paused
            std::this_thread::sleep_for(std::chrono::duration<double>(0.1));
            continue;
        }
        double next_time = event_queue_->nextTimeStep();
        double elapsed_time = std::chrono::duration_cast<std::chrono::duration<double>>(steady_clock::now() - real_start_time_).count();
        elapsed_time *= speedup_;
        double waiting_time = (next_time - elapsed_time) / speedup_;
        // std::cout << "Waiting: " << waiting_time << ", next: " << next_time << ", elapsed: " << elapsed_time << std::endl;

        if (waiting_time < 0) {
            if (-waiting_time > 0.1 && current_time_ > (last_warning_time_ + period_)) {
                spdlog::warn("At time {}, simulation lagging by {} seconds", current_time_.load(), -waiting_time);
                last_warning_time_ = current_time_;
            }
            break;
        }

        // Sleep by 10ms increments to allow for interruptions
        std::this_thread::sleep_for(std::chrono::duration<double>(std::min(0.01, waiting_time)));
    }
}

std::string Orchestrator::getTimestamp() {
    auto t = std::chrono::system_clock::to_time_t(initial_clock_time_);
    std::ostringstream ss;
    ss << std::put_time(std::localtime(&t), "%Y_%m_%d_%H_%M_%S");
    return ss.str();
}
