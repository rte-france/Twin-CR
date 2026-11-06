/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef REPLAY_H
#define REPLAY_H

#include "Information.h"
#include "ThreadPool.h"

/**
 * Replays a simulation by replaying the logged events.
 */
class Replay {
    public:
        Replay();
        ~Replay();

        /**
         * Go to the time 'time' and replay all events that occured by repeatidly asking the orchestrator to call goToNextTimeStep()
         */
        void setTargetTime(double time);

        /**
         * Jump to time 'time' without playing events
         */
        void jumpToTime(double time);

        /**
         * Set a filter to only emit events that exactly match the topic filter.
         * "" (empty) means no filter
         * Events without a defined topic (e.g. TimeUpdate) are always emitted
         */
        void setTopicFilter(const std::string& filter) { topic_filter_ = filter; }

    private:
        /**
         * Go to the next time step and replay all events that occured between current_time_ and next_time_step_
         */
        void goToNextTimeStep();

        std::string getFullTableName(const std::string& table_name) const;
        std::string generateQuery(int event_type, double start_time, double end_time);

        void fillBuffer(int event_type);
        void fillBuffers();

        std::string simulation_name_;

        void setStep(unsigned long index);

        unsigned long step_index_ = 0;
        double current_time_;
        double period_;
        double next_time_step_;
        double target_time_;
        std::string topic_filter_;
        std::unordered_map<int, std::vector<std::unique_ptr<Serializable>>> buffers_;
        ThreadPool pool_{std::thread::hardware_concurrency()};
};

#endif // REPLAY_H
