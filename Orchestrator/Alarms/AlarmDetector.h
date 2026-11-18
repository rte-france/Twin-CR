/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef ALARM_DETECTOR_H
#define ALARM_DETECTOR_H

#include "Information.h"
#include "../utils/ClickHouseLoggerInterface.h"

#include <functional>
#include <memory>
#include <nlohmann/json.hpp>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>

/**
 * Display of a state of an alarm
 */
struct AlarmStateDisplay {
    std::string label;
    int priority = 0;
    std::string color;
    std::optional<std::string> sound;
    bool alarm = true;  // False: not an alarm, shown in the event list only
};

/**
 * Alarm type: either a state type (the value is the state, e.g. a breaker position), or a threshold type
 * (the state is the most severe threshold level crossed by the absolute value, e.g. a current above its limits, or a
 * voltage below or above its limits)
 */
struct AlarmType {
    bool alarm = true;
    bool persistent = false;
    bool retain = true;
    std::optional<double> normal;  // State types: normal value (required for persistent ones)
    std::unordered_map<std::string, AlarmStateDisplay> states;  // State types: by formatted value
    std::vector<std::string> level_names;  // Threshold types: level i + 1 is level_names[i]
    std::vector<bool> level_low;  // Threshold types: true if level i + 1 is crossed below its threshold, else above
    std::vector<AlarmStateDisplay> levels;  // Threshold types: levels[0] is the normal state (no threshold crossed)
    double hysteresis = 0.0;

    bool isThreshold() const { return !level_names.empty(); }
    bool isNormal(double state) const { return isThreshold() ? state == 0 : (normal.has_value() && normal.value() == state); }
};

struct AlarmEntry {
    std::string id;
    std::string label;
    const AlarmType* type;
    std::optional<std::string> equipment_id;
    std::optional<std::string> substation_id;
    std::optional<std::string> side;  // Side of the equipment (branches, 3 windings transformers): ONE, TWO or THREE
    std::vector<double> thresholds;  // Threshold types: threshold of level i + 1 (NaN if not configured)
};

/**
 * Last state of each alarm id seen by one destination (GameMaster, or a SCADA destination)
 */
struct AlarmSide {
    std::string subject;  // NATS subject, not dumped (recomputed)
    std::unordered_map<std::string, double> states;

    template<class Archive>
    void serialize(Archive& ar) {
        ar(states);
    }
};

/**
 * Detect alarms and events from the state changes of the configured ids and publish them:
 *  - on "Alarms.GameMaster" from the true values (ActualMeasurement) and all the controls sent (ControlSent).
 *    Don't subscribe to ActualControl since they are redundant with ActualMeasurement
 *  - on "Alarms.HMI.<destination>" from the values received by each destination (MeasurementReceived), and the controls
 *    sent from the HMI (ControlSent from the HMI interface) on "Alarms.HMI.<hmi.location>".
 *
 * Done here rather than in the Argus backends, as the GameMaster backend cannot subscribe to all the GameMaster topics.
 * The alarm lifecycle (acknowledgement, clearing, comments) is handled by the backends.
 */
class AlarmDetector {
    public:
        using Publisher = std::function<void(const std::string& subject, const std::string& payload)>;

        /**
         * @param config alarm configuration
         * @param tase2_to_id resolves the "tase2" of the alarms (from the scada outputs)
         * @param hmi_location location of the HMI, origin of the ControlSent of topic "HMI"
         * @param initial_time values up to that time are initial values (no alarm, except for the persistent alarms not
         *        in their normal state): the start time of the run plus one period, as Dynawo publishes its first values
         *        at the end of the first step
         */
        AlarmDetector(const nlohmann::json& config, const std::unordered_map<std::string, std::string>& tase2_to_id,
                      const std::string& hmi_location, double initial_time, Publisher publisher);
        AlarmDetector(const AlarmDetector&) = delete;
        AlarmDetector& operator=(const AlarmDetector&) = delete;

        /**
         * Create the detector from config.toml (nullptr without input_files.alarms_file), subscribe it to the
         * Orchestrator events, and restore its state when restarting from a dump.
         */
        static std::unique_ptr<AlarmDetector> create(ClickHouseLoggerInterface& logger, double start_time, bool from_dump);

        void onActualMeasurement(const ActualMeasurement& info);
        void onMeasurementReceived(const MeasurementReceived& info);
        void onControlSent(const ControlSent& info);

        std::string saveState() const;
        void loadState(const std::string& bin);

        /**
         * Publish again the persistent alarms that are not in their normal state and the thresholds crossed (after a restart from a dump)
         */
        void republishActive(double time);

        /**
         * Threshold level of 'value' (0: no threshold crossed): the last level crossed, high levels (low[i] false) when
         * |value| > threshold, low levels when 0 < |value| < threshold (zero: e.g. a de-energised bus). The levels of each direction are in increasing
         * severity. Stays at the 'current' level while within its hysteresis band, unless a level of the opposite
         * direction is crossed.
         */
        static int computeLevel(const std::vector<double>& thresholds, const std::vector<bool>& low, double hysteresis, int current, double value);

        static std::string formatValue(double value);

        size_t size() const { return alarms_.size(); }

    private:
        void processValue(AlarmSide& side, const std::string& id, const Value& value, double time);
        void publishState(const AlarmSide& side, const AlarmEntry& entry, double state, double value, double time, bool initial);
        void publishCommand(const std::string& subject, const std::string& id, const Value& value, double time);
        AlarmSide& scadaSide(const std::string& destination);
        void onDumpStateEvent(const DumpStateEvent& event);

        AlarmStateDisplay parseDisplay(const nlohmann::json& j, bool alarm) const;
        void resolveDisplay(AlarmStateDisplay& display, const std::optional<std::string>& color, const std::optional<std::optional<std::string>>& sound) const;

        struct PriorityRule {
            int min;
            std::string color;
            std::optional<std::string> sound;
        };
        std::vector<PriorityRule> priorities_;  // Increasing min
        std::unordered_map<std::string, AlarmType> types_;
        std::unordered_map<std::string, AlarmEntry> alarms_;
        bool commands_enabled_ = false;
        std::string command_label_ = "Command";
        AlarmStateDisplay command_display_;

        std::string hmi_subject_;
        double initial_time_;
        Publisher publisher_;
        ClickHouseLoggerInterface* logger_ = nullptr;

        AlarmSide game_master_;
        std::unordered_map<std::string, AlarmSide> scada_;  // By destination
};

#endif // ALARM_DETECTOR_H
