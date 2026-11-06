/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef DSL_EVERY_TICK_WATCH_LIST_H
#define DSL_EVERY_TICK_WATCH_LIST_H

#include <algorithm>
#include <vector>

/**
 * Container of event ids evaluated by linear scan at every time step.
 * Includes in-progress ramps and when/when_rearming/after watches.
 * Expected to contain a small number of events (unlike the point queue, which can hold thousands of bulk-scheduled point events),
 * so a linear scan at each time step should not cause performance issues.
 * Stores only ids; the actual DSLEvent objects live in DSLEngine's registry.
 */
class DSLEveryTickWatchList {
    public:
        void addRamp(unsigned long event_id) { ramp_ids_.push_back(event_id); }
        void addConditional(unsigned long event_id) { conditional_ids_.push_back(event_id); }

        bool cancel(unsigned long event_id) {
            return removeFrom(ramp_ids_, event_id) || removeFrom(conditional_ids_, event_id);
        }

        const std::vector<unsigned long>& rampIds() const { return ramp_ids_; }
        const std::vector<unsigned long>& conditionalIds() const { return conditional_ids_; }

        void removeRamps(const std::vector<unsigned long>& ids_to_remove) {
            for (auto& id : ids_to_remove) {
                removeFrom(ramp_ids_, id);
            }
        }
        void removeConditionals(const std::vector<unsigned long>& ids_to_remove) {
            for (auto& id : ids_to_remove) {
                removeFrom(conditional_ids_, id);
            }
        }

    private:
        static bool removeFrom(std::vector<unsigned long>& v, unsigned long id) {
            auto it = std::find(v.begin(), v.end(), id);
            if (it == v.end()) return false;
            v.erase(it);
            return true;
        }

        std::vector<unsigned long> ramp_ids_;
        std::vector<unsigned long> conditional_ids_;
};

#endif // DSL_EVERY_TICK_WATCH_LIST_H
