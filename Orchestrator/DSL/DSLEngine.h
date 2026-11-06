/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef DSL_ENGINE_H
#define DSL_ENGINE_H

#include "../utils/ClickHouseLoggerInterface.h"
#include "../utils/DynawoInterfaceInterface.h"
#include "../utils/ScenarioHandlerInterface.h"
#include "DSLEveryTickWatchList.h"
#include "DSLFunctionDefinition.h"
#include "DSLPointEventQueue.h"
#include "DSLReplayLogger.h"
#include "DSLValueCache.h"
#include "Mapping/IFLMapping.h"
#include "Mapping/IIDMMapping.h"
#include "Scope.h"
#include "SerialisationHelper.h"

#include <filesystem>
#include <memory>
#include <mutex>
#include <string>
#include <unordered_map>
#include <vector>

class DSLEvent;
struct ActualMeasurement;
struct ActualControl;
struct DumpStateEvent;

/**
 * An autocompletion answer, a suggestion is a full word (with quotes when relevant, e.g. input "P").
 * replace_from is the position of the start of the partial word to be replaced.
 */
struct DSLCompletions {
    std::vector<std::string> suggestions;
    size_t replace_from = 0;
};

/**
 * Facade tying the DSL engine together: owns the event registry and the two
 * runtime queues, subscribes to ActualMeasurement/ActualControl/DumpStateEvent,
 * self-schedules its own periodic goToNextTimeStep tick, and drives
 * expansion/validation/commit of scripts and function calls.
 */
class DSLEngine {
    public:
        /**
         * Fresh start.
         */
        DSLEngine(bool with_subscriptions, ScenarioHandlerInterface& scenario_handler, DynawoInterfaceInterface& dynawo_interface, ClickHouseLoggerInterface& logger, double start_time);

        /**
         * Construct from a previously dumped archive fetched from ClickHouse.
         */
        DSLEngine(ScenarioHandlerInterface& scenario_handler, DynawoInterfaceInterface& dynawo_interface, ClickHouseLoggerInterface& logger, double time);

        ~DSLEngine();

        /**
         * Parses and commits every top-level statement of a script, in order.
         * Throws on the first invalid statement.
         */
        void loadScript(const std::string& source_text, const std::string& source_name);

        void onActualMeasurement(const ActualMeasurement& info);
        void onActualControl(const ActualControl& info);
        void handleDumpStateEvent(const DumpStateEvent& event);

        std::shared_ptr<FunctionDefinition> lookupFunction(const std::string& name) const;
        void registerFunction(std::shared_ptr<FunctionDefinition> def);

        /**
         * Looks up the id of a Dynawo output, by IIDM equipment or, for a purely dynamic model, by the model id.
         */
        std::string getOutputId(const std::string& iidm_id, const std::string& attribute) const;
        std::string getDynamicModelOutputId(const std::string& dynamic_model, const std::string& attribute) const;

        /**
         * Return the last value seen for a watched output
         */
        std::optional<double> currentValue(const std::string& output_id) const;

        /**
         * List of the iidm ids of the elements of a given type.
         * Used to resolve `cluster regex "..." on <gridElementType>`.
         */
        std::vector<std::string> listIidmIds(const std::string& pypowsybl_type) const;

        /**
         * Like listIidmsIds but for Dynawo purely dynamic models
         */
        std::vector<std::string> listDynamicModelIds(const std::string& model_lib) const;

        /**
         * Returns true if there is currently a ramp scheduled for (iidm_id, attribute) in the time interval [start, end].
         * 'exclude_id', if set, is ignored by the check (used when replacing a Ready ramp with itself via PUT /queue/{id},
         * so the event being replaced doesn't spuriously conflict with its own replacement).
         */
        /**
         * Record a ramp that the statement currently being expanded will create, so hasActiveRampOn can see it
         * before it is committed. Cleared at the start of every entry point that builds a batch.
         */
        void registerPendingRamp(const std::string& iidm_id, const std::string& attribute, double start, double end);

        bool hasActiveRampOn(const std::string& iidm_id, const std::string& attribute, double start, double end,
                             std::optional<unsigned long> exclude_id = std::nullopt) const;

        /**
         * Expands (and commits if mode==Execute) a function call: parses the callee's body, binds args into a fresh Scope frame, and recursively visits its statements.
         * Throws on the first validation failure (nothing produced so far is ever committed in that case).
         * Returns the produced events so the caller (a FunctionCallEvent) can record their ids.
         */
        std::vector<std::unique_ptr<DSLEvent>> expandFunctionCall(
            const std::string& function_name, const std::vector<ParamValue>& args, double call_time,
            std::shared_ptr<const Scope> caller_scope, unsigned long call_event_id,
            const std::string& source_name);

        IIDMMapping& iidmMapping() { return iidm_mapping_; }
        IFLMapping& iflMapping() { return ifl_mapping_; }
        unsigned long newEventId();

        /**
         * Path to the append-only replay log (what actually executed, in absolute time)
         */
        std::filesystem::path getReplayLogPath() const { return replay_logger_.path(); }

        /**
         * The DSL script text originally loaded from dsl_file at construction (empty if none was configured).
         * Never updated afterwards, regardless of any further loadScript/replaceEventIfReady calls.
         */
        const std::string& getInitialScript() const { return initial_script_; }

        /**
         * "Useful info" snapshot of every event currently in the registry, for the web interface's /queue/list.
         */
        nlohmann::json listEvents() const;

        /**
         * Return suggestions to complete the `partial` DSL string.
         */
        DSLCompletions complete(const std::string& partial) const;

        static constexpr size_t MAX_COMPLETIONS = 50;

        /**
         * Cancels event 'id': if Ready, removed outright; if Ongoing, interrupted (retained), cascading to
         * children first if it's a FunctionCallEvent.
         * No-op (returns false) if the id is missing or already Completed/Interrupted.
         */
        bool cancelEvent(unsigned long id);

        /**
         * Replaces a Ready event's DSL text with a new statement, which must resolve to exactly one event.
         * Throws DSLValidationException if 'id' is missing/not-Ready, or the new text fails to validate.
         * Returns the id of the newly-committed event.
         */
        unsigned long replaceEventIfReady(unsigned long id, const std::string& new_dsl_text, const std::string& source_name);

        template<class Archive>
        void serialize(Archive& ar) {
            ar(top_level_scope_, functions_, events_, next_event_id_, value_cache_, period_, initial_script_,
               tag_owners_);
        }

    private:
        void initSubscriptions();
        /**
         * Function to be called when building from a ser20 dump.
         * Re-populates point_queue_/watch_list_ from events_, re-arms watches.
         */
        void postLoadFixup();

        /**
         * Commits a fully-validated batch: inserts every event into events_ and the appropriate queue.
         */
        void commitBatch(std::vector<std::unique_ptr<DSLEvent>>& batch);

        /**
         * Runs due point actions/ramps/conditionals, then reschedules itself period_ later.
         */
        void goToNextTimeStep();

        /**
         * A tag is "completed" once every event that declared it has DSLStatus::Completed.
         * E.g. for a tagged function call, this returns true when all child events of the function are completed
         */
        bool isTagCompleted(const std::string& qualified_tag) const;
        void propagateStatusToParents(unsigned long child_id);

        /**
         * Cancels a Ready event from point_queue_/watch_list_/value_cache_ and erases it from events_.
         * Assumes mutex_ is already held by the caller.
         */
        /**
         * Hand back everything an event that will never run again still holds: its slot in the point queue or the
         * every-tick watch list, and the value-cache refcounts of the ids its condition reads.
         * Leaves it in events_, so a cancelled event is still listable with its Interrupted status.
         */
        void releaseEvent(unsigned long id);
        /**
         * Every event a call owns, through nested calls too, children before their parent. Returns just {id} for
         * anything that is not a call, so a caller can treat both the same way.
         */
        std::vector<unsigned long> collectCallSubtree(unsigned long id) const;
        /**
         * Expand the function call a conditional fired, at 'now'.
         */
        void expandTriggeredCall(unsigned long conditional_id, const std::string& call_source, double now);
        /**
         * Run the point actions due at 'now'.
         */
        void applyDuePointActions(double now);
        /**
         * Recompute the status of a chain of enclosing calls, innermost first. Takes the parent rather than the
         * child, so it still works once the child has been erased from events_.
         */
        void refreshCallsFrom(std::optional<unsigned long> parent_id);
        void removeReadyEvent(unsigned long id);

        ScenarioHandlerInterface& scenario_handler_;
        DynawoInterfaceInterface& dynawo_interface_;
        ClickHouseLoggerInterface& logger_;
        IIDMMapping iidm_mapping_;
        IFLMapping ifl_mapping_;
        DSLValueCache value_cache_;
        DSLReplayLogger replay_logger_;

        std::shared_ptr<Scope> top_level_scope_;
        FunctionTable functions_;
        std::vector<std::string> expansion_stack_;
        struct PendingRamp {
            std::string iidm_id;
            std::string attribute;
            double interval_start = 0.0;
            double interval_end = 0.0;
        };
        /**
         * Ramps created while the current statement is expanded but not yet committed. A function body becomes a
         * single batch, so without these two ramps in one body would never meet, while the same two lines written
         * at top level do: loadScript commits after every statement. Never serialized, it is empty between them.
         */
        std::vector<PendingRamp> pending_ramps_;  // Names of the calls currently being expanded, outermost first. Used to forbid recursive calls
        std::unordered_map<unsigned long, std::shared_ptr<DSLEvent>> events_;
        std::unordered_map<std::string, std::vector<unsigned long>> tag_owners_;  // qualified tag -> event ids sharing it (a tagged function call can generate multiple events with its own tag)
        DSLPointEventQueue point_queue_;
        DSLEveryTickWatchList watch_list_;
        unsigned long next_event_id_ = 0;
        std::string initial_script_;
        double period_;
        double start_time_;
        unsigned long tick_index_;
        double next_tick_time_;  // Not serialized: re-derived from start_time/time and period_ on (re)construction

        mutable std::mutex mutex_;
};
CHECK_SERIALIZABLE(DSLEngine);

#endif // DSL_ENGINE_H
