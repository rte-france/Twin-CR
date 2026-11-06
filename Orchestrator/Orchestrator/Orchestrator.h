/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef ORCHESTRATOR_H
#define ORCHESTRATOR_H

#include "EventQueue.h"
#include "Information.h"

#include <nlohmann/json.hpp>
#include <toml++/toml.h>

#include <atomic>
#include <cassert>
#include <chrono>
#include <functional>
#include <optional>
#include <thread>
#include <tuple>
#include <type_traits>
#include <vector>

using namespace std::chrono;

template <class Event>
using Subscriptions = std::vector<std::function<void(const Event&)>>;

/**
 * @brief Orchestrator class
 *
 * Orchestrator class is responsible for the time management, and for instantiating and handling the interactions between all the other classes
 */
class Orchestrator {
    public:
        static void create(const std::filesystem::path& working_dir, const toml::table& config, double start_time, double end_time, const std::optional<std::string> simulation_name) {
            instance_ = std::unique_ptr<Orchestrator>(
                new Orchestrator(working_dir, config, start_time, end_time, simulation_name)
            );
        }

        static Orchestrator& get() {
            if (!instance_) {
                throw std::runtime_error("Orchestrator::create must be called first");
            }
            return *instance_;
        }

        /**
         * @brief Runs the simulation.
         * Time management is performed using an event queue, in which events are sorted in increasing order of event time.
         * This means that the master always pops the first event in the queue, execute it (which might create new events),
         * and repeats this process until the queue is empty or the SignalHandler receives an interrupt
         * The master waits for real-time before each event.
         * Runs until t = run_to_time if provided, else to the end of the simulation
        */
       void run(std::optional<double> run_to_time);

       /**
        * Pause the simulation
        */
       void pause();

       /**
        * Resume the simulation (with a speedup of 1)
        */
       void resume();

       /**
        * Let the simulation run at the maximum possible speed
        */
       void fastForward();

        /**
         * Subscribe to the emission of a given type of events, such that 'f' is called (using the event as argument)
         * each time one of these events is emitted.
        */
        template <class Event>
        void subscribe(std::function<void(const Event&)> f) {
            std::get<Subscriptions<Event>>(subscriptions_).push_back(std::move(f));
        }

        /**
         * Subscribe to the emission of a given type of events, such that the given member function is called
         * (using the event as argument) each time one of these events is emitted.
        */
        template <typename Event, auto Method, typename T>
        void subscribeTo(T* instance) {
            subscribe<Event>([instance](const Event& e) { (instance->*Method)(e); });
        }

        /**
         * Emit an event, calling all subscribers to that event's type
        */
        template <class Event>
        void emit(const Event& e) {
            assert(std::this_thread::get_id() == main_thread_id_ &&
                "emit() must only be called from the main simulation thread; use emitLater() to safely schedule emissions from other threads");
            for (auto& f : std::get<Subscriptions<Event>>(subscriptions_)) f(e);
        }

        // Special-cased as it also schedules the next dump event and logs the dump
        void emitDumpStateEvent(const DumpStateEvent& event);

        /**
         * Schedule the emission of 'e' to occur at t='time'.
         * Always goes through the main event queue for thread-safety (even if time = now)
        */
        template <class Event>
        void emitLater(Event&& e, double time) {
            static_assert(!std::is_lvalue_reference_v<Event>, "emitLater requires an rvalue (pass with std::move)");
            using E = std::decay_t<Event>;
            scheduleEvent(time, makeCallback<&Orchestrator::emit<E>>(this, std::forward<Event>(e)));
        }

        /**
         * Schedule the call of the function 'callback' to occur at t='time'
         */
        void scheduleEvent(double time, Callback&& callback, Event::Order order = Event::Order::Normal) {
            event_queue_->insertEvent(Event(time, std::move(callback), order));
        }

        /**
         * Schedule the call of the function 'callback' to occur at t='time'
         * The callbacks is called directly if time is lower or equal to the current time
         * Note: for hot paths, it is better to manually check for time < current_time_ to avoid the
         * unecessary creation of a callback
         * Note 2: the now branch is only thread-safe if the callback is thread-safe (currently ok as it is only used with the callbacks
         * Orchestrator::resume, Orchestrator::pause, and Orchestrator::fast_forward)
         */
        void scheduleEventOrNow(double time, Callback&& callback) {
            if (time <= current_time_) {
                callback();
            } else {
                scheduleEvent(time, std::move(callback));
            }
        }

        double getCurrentTime() const { return current_time_; }

        /**
         * True if called from the main simulation thread (the only thread emit() may be called from).
         */
        bool isMainThread() const { return std::this_thread::get_id() == main_thread_id_; }

        /**
         * Reset the real time clock to match elapsed_time
         */
        void resetRealTimeClock(double elapsed_time);

        void setSpeedUp(double speedup) { speedup_ = speedup; }

        const std::string& getSimulationName() const { return simulation_name_; }

        std::chrono::time_point<std::chrono::system_clock> getInitialClockTime() const { return initial_clock_time_; }

        const std::filesystem::path& getWorkingDir() const { return working_dir_; }

        const toml::table& getConfig() const { return config_; }

    private:
        Orchestrator(const std::filesystem::path& working_dir, const toml::table& config, double start_time, double end_time, const std::optional<std::string> simulation_name);

        /**
         * Wait until the real elapsed time (divided by speedup if different from 1) is equal to the time of the next event.
         * This function waits by 10ms interval and checks at each iteration if a new event has been added in the queue. This allows for example
         * the HMI to inject events while the Master is sleeping.
        */
        void waitUntilNextEvent();

        std::string getTimestamp();

        std::filesystem::path working_dir_;
        toml::table config_;
        std::atomic<double> current_time_;
        std::atomic<bool> paused_;
        double last_warning_time_;
        double start_time_;
        double last_time_update_;
        unsigned long time_update_tick_index_ = 0;
        unsigned long dump_tick_index_ = 0;
        std::atomic<double> speedup_;
        double period_;
        double dump_period_;
        double end_time_;
        std::unique_ptr<EventQueue> event_queue_;
        steady_clock::time_point real_start_time_;
        const std::chrono::time_point<std::chrono::system_clock> initial_clock_time_;
        const std::string simulation_name_;
        const std::thread::id main_thread_id_;  // Set at construction; emit() asserts it is only called back from this thread

        std::tuple<
            Subscriptions<MeasurementSent>,
            Subscriptions<MeasurementReceived>,
            Subscriptions<CycosimMeasurementReceived>,
            Subscriptions<ControlSent>,
            Subscriptions<ControlReceived>,
            Subscriptions<CycosimControlReceived>,
            Subscriptions<ActualMeasurement>,
            Subscriptions<ActualControl>,
            Subscriptions<TimeUpdate>,
            Subscriptions<DynawoTimelineEvent>,
            Subscriptions<DynawoConstraintEvent>,
            Subscriptions<DumpStateEvent>,
            Subscriptions<RawDynawoCommand>
        > subscriptions_;

        inline static std::unique_ptr<Orchestrator> instance_;
};

#endif // ORCHESTRATOR_H
