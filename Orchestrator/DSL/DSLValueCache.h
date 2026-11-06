/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef DSL_VALUE_CACHE_H
#define DSL_VALUE_CACHE_H

#include "SerialisationHelper.h"

#include <mutex>
#include <optional>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

struct ActualMeasurement;
struct ActualControl;

/**
 * Cache of the latest ActualMeasurements and ActualControls, used for 'when'/'when_rearming' clauses.
 * ActualMeasurements can be published at a throughput of 500k/s, so we only stored the necessary ones
 * (via ref-counting with watchIds()/unwatchIds()). (In any case, we do one O(1) hashmap lookup per
 * onActualMeasurement() call, but only saving the watched ids allows to keep the map in L1/L2 instead of L3/RAM)
 *
 * values_ and watch_refcounts_ are owned by the simulation thread alone and are therefore never locked, which is what
 * keeps that throughput affordable. watchIds()/unwatchIds() are however also called from a DSLWebInterface thread (via
 * DSLEngine::commitBatch/removeReadyEvent), so they only queue their change into pending_deltas_; applyPendingWatches()
 * then applies the queue back on the simulation thread.
 */
class DSLValueCache {
    public:
        void onActualMeasurement(const ActualMeasurement& info);
        void onActualControl(const ActualControl& info);

        std::optional<double> get(const std::string& id) const;

        /**
         * Applies every watch change queued since the last call. This is done only in the main simulation thread.
         * This function is to be called at the start of DSLEngine::goToNextTimeStep, i.e. before the conditionals that requested those watches are evaluated.
         */
        void applyPendingWatches();

        // Any thread
        void watchIds(const std::unordered_set<std::string>& ids);
        void unwatchIds(const std::unordered_set<std::string>& ids);

        /**
         * values_ is serialized (part of DSLEngine::serialize()) so a reload doesn't momentarily lose the last-known value of an id.
         * watch_refcounts_ and pending_deltas_ are deliberately NOT serialized: DSLEngine::postLoadFixup() rebuilds the refcounts from
         * events_, which also regenerates any delta that was still pending when the dump was taken.
         */
        template<class Archive>
        void serialize(Archive& ar) { ar(values_); }

    private:
        void queueDeltas(const std::unordered_set<std::string>& ids, int delta);

        std::unordered_map<std::string, double> values_;
        std::unordered_map<std::string, int> watch_refcounts_;

        std::mutex pending_mutex_;
        std::vector<std::pair<std::string, int>> pending_deltas_;  // (id, +1/-1), drained by applyPendingWatches()
};
CHECK_SERIALIZABLE(DSLValueCache);

#endif // DSL_VALUE_CACHE_H
