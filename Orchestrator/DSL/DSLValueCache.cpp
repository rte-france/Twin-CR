/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "DSLValueCache.h"
#include "Information.h"

void DSLValueCache::onActualMeasurement(const ActualMeasurement& info) {
    if (!watch_refcounts_.contains(info.id)) return;
    values_[info.id] = info.value.to_double();
}

void DSLValueCache::onActualControl(const ActualControl& info) {
    if (!watch_refcounts_.contains(info.id)) return;
    values_[info.id] = info.value.to_double();
}

std::optional<double> DSLValueCache::get(const std::string& id) const {
    if (!values_.contains(id)) return std::nullopt;
    return values_.at(id);
}

void DSLValueCache::queueDeltas(const std::unordered_set<std::string>& ids, int delta) {
    std::lock_guard<std::mutex> lock(pending_mutex_);
    for (auto& id : ids) pending_deltas_.emplace_back(id, delta);
}

void DSLValueCache::watchIds(const std::unordered_set<std::string>& ids) {
    queueDeltas(ids, 1);
}

void DSLValueCache::unwatchIds(const std::unordered_set<std::string>& ids) {
    queueDeltas(ids, -1);
}

void DSLValueCache::applyPendingWatches() {
    std::vector<std::pair<std::string, int>> deltas;
    {
        std::lock_guard<std::mutex> lock(pending_mutex_);
        deltas.swap(pending_deltas_);
    }

    for (auto& [id, delta] : deltas) {
        int& count = watch_refcounts_[id];
        count += delta;
        if (count <= 0) {
            watch_refcounts_.erase(id);
            values_.erase(id);
        }
    }
}
