/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "DSLPointEventQueue.h"

void DSLPointEventQueue::insert(double time, unsigned long event_id) {
    auto it = events_.emplace(time, event_id);
    index_[event_id] = it;
}

bool DSLPointEventQueue::cancel(unsigned long event_id) {
    if (!index_.contains(event_id)) {
        return false;
    }
    events_.erase(index_.at(event_id));
    index_.erase(event_id);
    return true;
}

std::vector<unsigned long> DSLPointEventQueue::popDue(double t) {
    std::vector<unsigned long> due;
    auto end = events_.upper_bound(t);
    for (auto it = events_.begin(); it != end; it++) {
        due.push_back(it->second);
        index_.erase(it->second);
    }
    events_.erase(events_.begin(), end);
    return due;
}
