/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef DSL_POINT_EVENT_QUEUE_H
#define DSL_POINT_EVENT_QUEUE_H

#include <map>
#include <optional>
#include <unordered_map>
#include <vector>

/**
 * Time-ordered queue of point action ids (sorted by time, then by id (i.e. creation order)).
 * Uses std::multimap<double, unsigned long> + an index for O(log n) cancel-by-id.
 * Stores only (time, id); the actual DSLEvent objects live in DSLEngine's registry, resolved by id.
 */
class DSLPointEventQueue {
    public:
        void insert(double time, unsigned long event_id);
        bool cancel(unsigned long event_id);

        /**
         * Removes and returns, in increasing-time (then insertion) order, the ids of every entry with time <= t.
         */
        std::vector<unsigned long> popDue(double t);

    private:
        std::multimap<double, unsigned long> events_;
        std::unordered_map<unsigned long, std::multimap<double, unsigned long>::iterator> index_;  // Multimap iterators stay valid when other elements are added/removed
};

#endif // DSL_POINT_EVENT_QUEUE_H
