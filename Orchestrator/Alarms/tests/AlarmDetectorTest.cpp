/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "AlarmDetector.h"

#include <cmath>
#include <iostream>
#include <nlohmann/json.hpp>
#include <string>
#include <vector>

static int failures = 0;

#define CHECK(condition) do { \
    if (!(condition)) { \
        std::cerr << __FILE__ << ":" << __LINE__ << ": CHECK failed: " #condition << std::endl; \
        failures++; \
    } \
} while (0)

struct Published {
    std::string subject;
    nlohmann::json payload;
};

static const nlohmann::json CONFIG = nlohmann::json::parse(R"({
    "priorities": [
        {"min": 0, "color": "grey", "sound": null},
        {"min": 3, "color": "yellow", "sound": "yellow"},
        {"min": 15, "color": "red", "sound": "red"}
    ],
    "types": {
        "breaker": {
            "mode": "momentary", "retain": false,
            "states": {
                "1": {"label": "Open", "priority": 7, "color": "blue", "sound": "blue"},
                "2": {"label": "Closed", "priority": 6, "color": "grey"}
            }
        },
        "overload": {
            "mode": "persistent", "normal": 0,
            "states": {"1": {"label": "Start", "priority": 19}, "0": {"label": "End", "priority": 4}}
        },
        "current": {
            "hysteresis": 0.1,
            "normal_state": {"label": "Overload end", "priority": 0},
            "levels": [
                {"name": "LIMIT1", "label": "Limit 1 overload", "priority": 10},
                {"name": "LIMIT2", "label": "Limit 2 overload", "priority": 20}
            ]
        },
        "voltage": {
            "hysteresis": 0.01,
            "normal_state": {"label": "Voltage normal", "priority": 0},
            "levels": [
                {"name": "LOW1", "direction": "low", "label": "Low voltage", "priority": 10},
                {"name": "LOW2", "direction": "low", "label": "Very low voltage", "priority": 20},
                {"name": "HIGH1", "direction": "high", "label": "High voltage", "priority": 10}
            ]
        }
    },
    "commands": {"enabled": true, "label": "Command", "priority": 2},
    "alarms": [
        {"id": "breaker", "type": "breaker", "label": "Breaker 1", "substation_id": "S1", "side": "TWO"},
        {"tase2": "S_1", "type": "overload"},
        {"id": "current", "type": "current", "thresholds": {"LIMIT1": 100, "LIMIT2": 200}},
        {"id": "voltage", "type": "voltage", "thresholds": {"LOW1": 210, "LOW2": 200, "HIGH1": 240}}
    ]
})");

static ActualMeasurement gm(const std::string& id, Value value, double time) {
    return ActualMeasurement(id, value, time, "topic");
}

static MeasurementReceived scada(const std::string& id, Value value, double time_sent, const std::string& destination = "SCADA") {
    return MeasurementReceived(MeasurementSent(id, value, time_sent, destination, {}, "topic", std::nullopt), time_sent + 0.5);
}

int main() {
    std::vector<Published> published;
    auto publisher = [&](const std::string& subject, const std::string& payload) {
        published.push_back({subject, nlohmann::json::parse(payload)});
    };
    const double start = 0.0;
    AlarmDetector detector(CONFIG, {{"S_1", "overload"}}, "SCADA", start, publisher);
    CHECK(detector.size() == 4);

    // Initial values: no alarm, except a persistent alarm not in its normal state
    detector.onActualMeasurement(gm("breaker", 2, start));
    detector.onActualMeasurement(gm("current", 50.0, start));
    detector.onActualMeasurement(gm("voltage", 225.0, start));
    detector.onActualMeasurement(gm("unknown", 1, start));
    CHECK(published.empty());
    detector.onActualMeasurement(gm("overload", true, start));
    CHECK(published.size() == 1);
    CHECK(published.back().payload["initial"] == true);
    CHECK(published.back().payload["state"] == "Start");
    CHECK(published.back().payload["color"] == "red");
    CHECK(published.back().payload["label"] == "overload");  // Defaults to the id

    // Breaker change on the GameMaster side
    published.clear();
    detector.onActualMeasurement(gm("breaker", 2, 1.0));  // Same value
    CHECK(published.empty());
    detector.onActualMeasurement(gm("breaker", 1, 2.0));
    CHECK(published.size() == 1);
    const auto& open = published.back();
    CHECK(open.subject == "Alarms.GameMaster");
    CHECK(open.payload["state"] == "Open");
    CHECK(open.payload["label"] == "Breaker 1");
    CHECK(open.payload["color"] == "blue");
    CHECK(open.payload["sound"] == "blue");
    CHECK(open.payload["mode"] == "momentary");
    CHECK(open.payload["retain"] == false);
    CHECK(open.payload["substation_id"] == "S1");
    CHECK(open.payload["side"] == "TWO");
    CHECK(open.payload["initial"] == false);
    detector.onActualMeasurement(gm("breaker", 2, 3.0));
    CHECK(published.back().payload["state"] == "Closed");
    CHECK(published.back().payload["sound"] == "yellow");  // From the priority rule (priority 6)

    // SCADA side: the time sent decides the initial values, per destination
    published.clear();
    detector.onMeasurementReceived(scada("breaker", 2, start));
    CHECK(published.empty());
    detector.onMeasurementReceived(scada("breaker", 1, 4.0, "SCADA 2"));  // First value after the start
    CHECK(published.size() == 1);
    CHECK(published.back().subject == "Alarms.HMI.SCADA_2");
    detector.onMeasurementReceived(scada("breaker", 1, 4.0));
    CHECK(published.size() == 2);
    CHECK(published.back().subject == "Alarms.HMI.SCADA");

    // First value of a persistent alarm after the start (OverloadAlarm only publishes on change)
    published.clear();
    detector.onMeasurementReceived(scada("overload", false, 5.0));  // Normal: nothing to report
    CHECK(published.empty());
    detector.onMeasurementReceived(scada("overload", true, 6.0));
    CHECK(published.size() == 1);
    CHECK(published.back().payload["normal"] == false);
    detector.onMeasurementReceived(scada("overload", false, 7.0));
    CHECK(published.back().payload["normal"] == true);
    CHECK(published.back().payload["state"] == "End");

    // Thresholds, with hysteresis
    published.clear();
    detector.onActualMeasurement(gm("current", -150.0, 1.0));
    CHECK(published.size() == 1);
    CHECK(published.back().payload["state"] == "Limit 1 overload");
    CHECK(published.back().payload["kind"] == "threshold");
    detector.onActualMeasurement(gm("current", 95.0, 2.0));  // Within the hysteresis band
    CHECK(published.size() == 1);
    detector.onActualMeasurement(gm("current", 250.0, 3.0));
    CHECK(published.back().payload["state"] == "Limit 2 overload");
    detector.onActualMeasurement(gm("current", 85.0, 4.0));
    CHECK(published.back().payload["state"] == "Overload end");
    CHECK(published.back().payload["normal"] == true);

    CHECK(AlarmDetector::computeLevel({100, 200}, {false, false}, 0.1, 2, 190) == 2);
    CHECK(AlarmDetector::computeLevel({100, 200}, {false, false}, 0.1, 2, 170) == 1);
    CHECK(AlarmDetector::computeLevel({100, NAN}, {false, false}, 0.0, 0, 300) == 1);

    // Low and high levels (voltage)
    published.clear();
    detector.onActualMeasurement(gm("voltage", 230.0, 4.0));
    CHECK(published.empty());
    detector.onActualMeasurement(gm("voltage", 205.0, 4.5));
    CHECK(published.size() == 1);
    CHECK(published.back().payload["state"] == "Low voltage");
    CHECK(published.back().payload["kind"] == "threshold");
    CHECK(published.back().payload["normal"] == false);
    CHECK(published.back().payload["limit"] == 210);  // Threshold of the level crossed
    detector.onActualMeasurement(gm("voltage", 195.0, 5.0));
    CHECK(published.back().payload["state"] == "Very low voltage");
    detector.onActualMeasurement(gm("voltage", 201.0, 5.5));  // Within the hysteresis band of LOW2 (202)
    CHECK(published.size() == 2);
    detector.onActualMeasurement(gm("voltage", 211.0, 6.0));  // Within the hysteresis band of LOW1 (212.1)
    CHECK(published.size() == 3);
    CHECK(published.back().payload["state"] == "Low voltage");
    detector.onActualMeasurement(gm("voltage", 213.0, 6.5));
    CHECK(published.back().payload["state"] == "Voltage normal");
    CHECK(published.back().payload["normal"] == true);
    detector.onActualMeasurement(gm("voltage", 245.0, 7.0));
    CHECK(published.back().payload["state"] == "High voltage");
    detector.onActualMeasurement(gm("voltage", 205.0, 7.5));  // Straight to a low level: no hysteresis
    CHECK(published.back().payload["state"] == "Low voltage");
    detector.onActualMeasurement(gm("voltage", 0.0, 8.0));  // De-energised: not a low voltage
    CHECK(published.back().payload["state"] == "Voltage normal");
    published.clear();
    detector.onActualMeasurement(gm("voltage", 230.0, 8.5));
    detector.onActualMeasurement(gm("voltage", 0.0, 9.0));
    CHECK(published.empty());

    // First value of a threshold type after the start (periodic measurement, e.g. every 5 s on the SCADA side): initial,
    // published as such when crossed (OverloadMonitor, not an alarm)
    published.clear();
    detector.onMeasurementReceived(scada("voltage", 205.0, 2.0));  // Already low
    CHECK(published.size() == 1);
    CHECK(published.back().payload["initial"] == true);
    CHECK(published.back().payload["state"] == "Low voltage");
    detector.onMeasurementReceived(scada("voltage", 195.0, 7.0));
    CHECK(published.size() == 2);
    CHECK(published.back().payload["initial"] == false);
    CHECK(published.back().payload["state"] == "Very low voltage");
    CHECK(published.back().subject == "Alarms.HMI.SCADA");

    const std::vector<bool> low_high = {true, true, false};
    CHECK(AlarmDetector::computeLevel({210, 200, 240}, low_high, 0.0, 0, 225) == 0);
    CHECK(AlarmDetector::computeLevel({210, 200, 240}, low_high, 0.0, 0, 190) == 2);
    CHECK(AlarmDetector::computeLevel({210, 200, 240}, low_high, 0.0, 0, 250) == 3);
    CHECK(AlarmDetector::computeLevel({210, 200, 240}, low_high, 0.05, 3, 230) == 3);  // High band: > 228
    CHECK(AlarmDetector::computeLevel({210, 200, 240}, low_high, 0.05, 2, 205) == 2);  // Low band: < 210
    CHECK(AlarmDetector::computeLevel({210, 200, 240}, low_high, 0.05, 2, 212) == 1);
    CHECK(AlarmDetector::computeLevel({NAN, NAN, 240}, low_high, 0.0, 0, 100) == 0);  // Low levels not configured
    CHECK(AlarmDetector::computeLevel({210, 200, 240}, low_high, 0.05, 2, 0) == 0);
    CHECK(AlarmDetector::formatValue(2.0) == "2");
    CHECK(AlarmDetector::formatValue(2.5) == "2.5");

    // Commands
    published.clear();
    detector.onControlSent(ControlSent("breaker", 2, 9.0, "RTU", {}, "HMI", std::nullopt));
    CHECK(published.size() == 2);  // GameMaster sees all controls, the HMI its own
    CHECK(published[0].subject == "Alarms.GameMaster");
    CHECK(published[1].subject == "Alarms.HMI.SCADA");
    CHECK(published.back().payload["kind"] == "command");
    CHECK(published.back().payload["state"] == "Command 2");
    CHECK(published.back().payload["label"] == "Breaker 1");
    CHECK(published.back().payload["alarm"] == false);
    published.clear();
    detector.onControlSent(ControlSent("breaker", 2, 9.0, "RTU", {}, "Scenario", std::nullopt));
    CHECK(published.size() == 1);

    // Restart from a dump: same states, the persistent alarms still on and the thresholds crossed are published again
    detector.onMeasurementReceived(scada("overload", true, 10.0));
    std::string dump = detector.saveState();
    std::vector<Published> restored_published;
    AlarmDetector restored(CONFIG, {{"S_1", "overload"}}, "SCADA", 10.0, [&](const std::string& subject, const std::string& payload) {
        restored_published.push_back({subject, nlohmann::json::parse(payload)});
    });
    restored.loadState(dump);
    restored.republishActive(10.0);
    CHECK(restored_published.size() == 3);  // Overload on in the GameMaster and in the SCADA, very low SCADA voltage
    int overloads = 0;
    for (const auto& p : restored_published) {
        overloads += p.payload["id"] == "overload";
        CHECK(p.payload["initial"] == true);
        if (p.payload["id"] == "voltage") {
            CHECK(p.payload["state"] == "Very low voltage");
            CHECK(p.payload["value"] == 200);  // The measured value is not dumped: republished as the threshold of the level
            CHECK(p.payload["limit"] == 200);
        }
    }
    CHECK(overloads == 2);
    restored_published.clear();
    restored.onActualMeasurement(gm("breaker", 2, 10.0));  // Same as before the dump
    restored.onMeasurementReceived(scada("overload", true, 10.0));
    CHECK(restored_published.empty());

    if (failures > 0) {
        std::cerr << failures << " check(s) failed" << std::endl;
        return 1;
    }
    std::cout << "All alarm checks passed" << std::endl;
    return 0;
}
