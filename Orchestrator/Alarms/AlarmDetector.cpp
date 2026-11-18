/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "AlarmDetector.h"

#include "Broker.h"
#include "NatsHelper.h"
#include "Orchestrator.h"
#include "../utils/JsonExtension.h"
#include "../utils/TomlExtension.h"

#include <cmath>
#include <filesystem>
#include <fstream>
#include <limits>
#include <ser20/archives/binary.hpp>
#include <ser20/types/string.hpp>
#include <ser20/types/unordered_map.hpp>
#include <spdlog/spdlog.h>
#include <sstream>

static constexpr const char* GAME_MASTER_SUBJECT = "Alarms.GameMaster";
static constexpr const char* HMI_SUBJECT_PREFIX = "Alarms.HMI.";
static constexpr const char* DUMP_NAME = "AlarmDetector";

static std::string hmiSubject(const std::string& location) {
    std::string sanitized = location;
    sanitizeNatsTopicName(sanitized);
    return HMI_SUBJECT_PREFIX + sanitized;
}

/** Equipment, substation and side of the alarm (for Locate), when configured */
static void addLocation(nlohmann::json& j, const AlarmEntry& entry) {
    if (entry.equipment_id.has_value()) {
        j["equipment_id"] = entry.equipment_id.value();
    }
    if (entry.substation_id.has_value()) {
        j["substation_id"] = entry.substation_id.value();
    }
    if (entry.side.has_value()) {
        j["side"] = entry.side.value();
    }
}

AlarmDetector::AlarmDetector(const nlohmann::json& config, const std::unordered_map<std::string, std::string>& tase2_to_id,
                             const std::string& hmi_location, double initial_time, Publisher publisher) :
    hmi_subject_(hmiSubject(hmi_location)),
    initial_time_(initial_time),
    publisher_(std::move(publisher)) {
    game_master_.subject = GAME_MASTER_SUBJECT;

    if (config.contains("priorities")) {
        for (const auto& rule : config["priorities"]) {
            std::optional<std::string> sound = get_optional<std::string>(rule, {"sound"});
            priorities_.push_back({rule.at("min").get<int>(), rule.at("color").get<std::string>(), sound});
        }
    } else {
        priorities_ = {{0, "grey", std::nullopt}, {3, "yellow", "yellow"}, {15, "red", "red"}, {40, "violet", "violet"}};
    }
    std::sort(priorities_.begin(), priorities_.end(), [](const auto& a, const auto& b) { return a.min < b.min; });

    for (const auto& [name, j] : config.at("types").items()) {
        try {
            AlarmType type;
            type.alarm = j.value("alarm", true);
            std::string mode = j.value("mode", "momentary");
            if (mode != "momentary" && mode != "persistent") {
                throw std::invalid_argument("unknown mode " + mode);
            }
            type.persistent = mode == "persistent";
            type.retain = j.value("retain", true);
            if (j.contains("normal")) {
                type.normal = j["normal"].get<double>();
            }
            type.hysteresis = j.value("hysteresis", 0.0);
            if (j.contains("levels")) {
                type.levels.push_back(parseDisplay(j.value("normal_state", nlohmann::json{{"label", "Normal"}, {"priority", 0}}), type.alarm));
                for (const auto& level : j["levels"]) {
                    type.level_names.push_back(level.at("name").get<std::string>());
                    std::string direction = level.value("direction", "high");
                    if (direction != "high" && direction != "low") {
                        throw std::invalid_argument("unknown direction " + direction);
                    }
                    type.level_low.push_back(direction == "low");
                    type.levels.push_back(parseDisplay(level, type.alarm));
                }
            } else if (type.persistent && !type.normal.has_value()) {
                throw std::invalid_argument("a persistent type needs a normal value");
            }
            if (j.contains("states")) {
                for (const auto& [value, state] : j["states"].items()) {
                    type.states[value] = parseDisplay(state, type.alarm);
                }
            }
            types_[name] = std::move(type);
        } catch (const std::exception& e) {
            throw std::invalid_argument("Invalid alarm type " + name + ": " + e.what() + " in:\n" + j.dump());
        }
    }

    for (const auto& j : config.at("alarms")) {
        try {
            AlarmEntry entry;
            if (j.contains("id")) {
                entry.id = j["id"].get<std::string>();
            } else {
                std::string tase2 = j.at("tase2").get<std::string>();
                if (!tase2_to_id.contains(tase2)) {
                    spdlog::warn("AlarmDetector: no scada output with tase2 {}, alarm ignored", tase2);
                    continue;
                }
                entry.id = tase2_to_id.at(tase2);
            }
            std::string type_name = j.at("type").get<std::string>();
            if (!types_.contains(type_name)) {
                throw std::invalid_argument("unknown type " + type_name);
            }
            entry.type = &types_.at(type_name);
            entry.label = j.value("label", entry.id);
            entry.equipment_id = get_optional<std::string>(j, {"equipment_id"});
            entry.substation_id = get_optional<std::string>(j, {"substation_id"});
            entry.side = get_optional<std::string>(j, {"side"});
            if (entry.type->isThreshold()) {
                const auto& names = entry.type->level_names;
                entry.thresholds.assign(names.size(), std::numeric_limits<double>::quiet_NaN());
                nlohmann::json thresholds = j.value("thresholds", nlohmann::json::object());
                for (const auto& [name, threshold] : thresholds.items()) {
                    auto level = std::find(names.begin(), names.end(), name);
                    if (level == names.end()) {
                        throw std::invalid_argument("unknown level " + name + " for type " + type_name);
                    }
                    entry.thresholds[level - names.begin()] = threshold.get<double>();
                }
            }
            std::string id = entry.id;
            if (!alarms_.emplace(id, std::move(entry)).second) {
                throw std::invalid_argument("duplicate alarm id " + id);
            }
        } catch (const std::exception& e) {
            throw std::invalid_argument("Invalid alarm: " + std::string(e.what()) + " in:\n" + j.dump());
        }
    }

    if (config.contains("commands")) {
        const auto& commands = config["commands"];
        commands_enabled_ = commands.value("enabled", true);
        command_label_ = commands.value("label", "Command");
        command_display_ = parseDisplay(nlohmann::json{{"label", command_label_}, {"priority", commands.value("priority", 0)}}, false);
    }
}

AlarmStateDisplay AlarmDetector::parseDisplay(const nlohmann::json& j, bool alarm) const {
    AlarmStateDisplay display;
    display.label = j.at("label").get<std::string>();
    display.priority = j.at("priority").get<int>();
    display.alarm = j.value("alarm", alarm);
    std::optional<std::optional<std::string>> sound;
    if (j.contains("sound")) {
        sound = get_optional<std::string>(j, {"sound"});  // null: no sound
    }
    resolveDisplay(display, get_optional<std::string>(j, {"color"}), sound);
    return display;
}

void AlarmDetector::resolveDisplay(AlarmStateDisplay& display, const std::optional<std::string>& color, const std::optional<std::optional<std::string>>& sound) const {
    const PriorityRule* rule = nullptr;
    for (const auto& r : priorities_) {
        if (r.min <= display.priority) {
            rule = &r;
        }
    }
    display.color = color.value_or(rule ? rule->color : "grey");
    display.sound = sound.has_value() ? sound.value() : (rule ? rule->sound : std::nullopt);
}

std::unique_ptr<AlarmDetector> AlarmDetector::create(ClickHouseLoggerInterface& logger, double start_time, bool from_dump) {
    const auto& config = Orchestrator::get().getConfig();
    const auto& working_dir = Orchestrator::get().getWorkingDir();
    std::optional<std::string> alarms_file = get_or_continue<std::string>(config, {"input_files", "alarms_file"});
    if (!alarms_file.has_value()) {
        spdlog::info("AlarmDetector: no alarms_file in config.toml, alarm detection disabled");
        return nullptr;
    }
    const std::filesystem::path alarms_path = working_dir / alarms_file.value();

    nlohmann::json alarm_config;
    std::ifstream alarms_stream(alarms_path);
    if (!alarms_stream.is_open()) {
        throw std::invalid_argument("AlarmDetector: cannot open the alarm config " + alarms_path.string() + " (input_files.alarms_file)");
    }
    try {
        alarm_config = nlohmann::json::parse(alarms_stream);
    } catch (const nlohmann::json::parse_error& e) {
        throw std::invalid_argument("AlarmDetector: failed to parse the alarm config " + alarms_path.string() + ": " + e.what());
    }

    std::string hmi_location;
    try {
        hmi_location = get_or_throw<std::string>(config, {"hmi", "location"});
    } catch (const std::exception&) {
        throw std::invalid_argument("AlarmDetector: the alarm detection (input_files.alarms_file) needs hmi.location in "
                                    "config.toml: the SCADA destination whose alarms the HMI shows (e.g. \"SCADA\")");
    }

    std::unordered_map<std::string, std::string> tase2_to_id;
    bool uses_tase2 = false;
    for (const auto& alarm : alarm_config.value("alarms", nlohmann::json::array())) {
        uses_tase2 |= !alarm.contains("id") && alarm.contains("tase2");
    }
    if (uses_tase2) {
        // Config uses tase2 indexing, map it to id (tase2_to_id) through the scada_outputs_file
        std::string scada_outputs_file = get_or_throw<std::string>(config, {"input_files", "scada_outputs_file"});
        nlohmann::json scada_outputs;
        try {
            scada_outputs = nlohmann::json::parse(std::ifstream(working_dir / scada_outputs_file));
        } catch (const nlohmann::json::parse_error& e) {
            throw std::invalid_argument("AlarmDetector: failed to parse " + (working_dir / scada_outputs_file).string() +
                                        " (input_files.scada_outputs_file, for the tase2 ids of the alarm config): " + e.what());
        }
        for (const auto& output : scada_outputs) {
            if (output.contains("tase2") && output["tase2"].is_string() && output.contains("id")) {
                tase2_to_id[output["tase2"].get<std::string>()] = output["id"].get<std::string>();
            }
        }
    }

    double period = get_or_throw<double>(config, {"master", "period"});
    std::unique_ptr<AlarmDetector> detector;
    try {
        detector = std::make_unique<AlarmDetector>(alarm_config, tase2_to_id, hmi_location, start_time + period,
            [](const std::string& subject, const std::string& payload) { Broker::get().publish(subject, payload); });
    } catch (const std::exception& e) {
        throw std::invalid_argument("AlarmDetector: invalid alarm config " + alarms_path.string() + ": " + e.what());
    }
    detector->logger_ = &logger;
    spdlog::info("AlarmDetector: {} alarms", detector->size());

    if (from_dump) {
        try {
            detector->loadState(logger.loadDump(DUMP_NAME, start_time));
        } catch (const std::exception& e) {
            // e.g. a dump made without alarm detection: start from the values received after the restart
            spdlog::warn("AlarmDetector: no state restored from the dump at {} ({}), starting without active alarms",
                         start_time, e.what());
        }
        // Published once the run starts, so that the backends restarted with the Orchestrator get them
        Orchestrator::get().scheduleEvent(start_time, makeCallback<&AlarmDetector::republishActive>(detector.get(), start_time));
    }

    auto* d = detector.get();
    Orchestrator::get().subscribeTo<ActualMeasurement, &AlarmDetector::onActualMeasurement>(d);
    Orchestrator::get().subscribeTo<MeasurementReceived, &AlarmDetector::onMeasurementReceived>(d);
    Orchestrator::get().subscribeTo<ControlSent, &AlarmDetector::onControlSent>(d);
    Orchestrator::get().subscribeTo<DumpStateEvent, &AlarmDetector::onDumpStateEvent>(d);
    return detector;
}

void AlarmDetector::onActualMeasurement(const ActualMeasurement& info) {
    processValue(game_master_, info.id, info.value, info.time);
}

void AlarmDetector::onMeasurementReceived(const MeasurementReceived& info) {
    if (!alarms_.contains(info.id)) {  // Hot path: most ids have no alarm
        return;
    }
    // The time sent tells the initial values apart (the time received depends on the delays of the IFM)
    processValue(scadaSide(info.destination), info.id, info.value, info.time_sent);
}

void AlarmDetector::onControlSent(const ControlSent& info) {
    // Gamemaster sees all ControlSent
    publishCommand(game_master_.subject, info.id, info.value, info.time_sent);
    if (info.topic == "HMI") {
        // HMI/SCADA only sees its own ControlSent
        publishCommand(hmi_subject_, info.id, info.value, info.time_sent);
    }
}

AlarmSide& AlarmDetector::scadaSide(const std::string& destination) {
    if (!scada_.contains(destination)) {
        // First value received by this destination
        scada_[destination].subject = hmiSubject(destination);
    }
    return scada_.at(destination);
}

int AlarmDetector::computeLevel(const std::vector<double>& thresholds, const std::vector<bool>& low, double hysteresis, int current, double value) {
    double v = std::abs(value);
    int count = static_cast<int>(std::min(thresholds.size(), low.size()));
    // Level i + 1 crossed, its threshold moved by 'margin' towards the normal state (hysteresis band)
    auto crossed = [&](int i, double margin) {
        double threshold = thresholds[i];
        if (std::isnan(threshold)) {
            return false;
        }
        // A zero value (e.g. a de-energised bus) does not cross low levels
        return low[i] ? v != 0.0 && v < threshold * (1 + margin) : v > threshold * (1 - margin);
    };
    int level = 0;
    for (int i = 0; i < count; i++) {
        if (crossed(i, 0.0)) {
            level = i + 1;
        }
    }
    // A level is only left beyond its hysteresis band, or for a level of the opposite direction
    if (current > level && current <= count) {
        bool direction = low[current - 1];
        if (level == 0 || low[level - 1] == direction) {
            for (int i = current; i > level; i--) {
                if (low[i - 1] == direction && crossed(i - 1, hysteresis)) {
                    return i;
                }
            }
        }
    }
    return level;
}

std::string AlarmDetector::formatValue(double value) {
    if (std::isfinite(value) && value == std::floor(value) && std::abs(value) < 1e15) {
        return std::to_string(static_cast<long long>(value));
    }
    std::ostringstream ss;
    ss << value;
    return ss.str();
}

void AlarmDetector::processValue(AlarmSide& side, const std::string& id, const Value& value, double time) {
    if (!alarms_.contains(id)) {
        return;
    }
    const AlarmEntry& entry = alarms_.at(id);
    const AlarmType& type = *entry.type;
    double v = value.to_double();
    if (std::isnan(v)) {
        return;  // No value (NaN never equals the last state: each one would be a change)
    }

    bool known = side.states.contains(id);  // A previous value was seen on this side
    double state = v;
    if (type.isThreshold()) {
        int current = known ? static_cast<int>(side.states.at(id)) : 0;
        state = computeLevel(entry.thresholds, type.level_low, type.hysteresis, current, v);
    }

    if (known) {
        double& previous = side.states.at(id);
        if (previous == state) {
            return;
        }
        previous = state;
    } else {
        side.states.emplace(id, state);
        // Initial value: at start, or the first value of a threshold type at any time (measurements are published
        // periodically, e.g. every 5 s on the SCADA side, so the first one may come after the start)
        if (time <= initial_time_ || type.isThreshold()) {
            // Only the conditions still on are published (initial): the persistent alarms, and the thresholds crossed
            // (OverloadMonitor; a momentary threshold is not an alarm at start)
            if ((type.persistent || type.isThreshold()) && !type.isNormal(state)) {
                publishState(side, entry, state, v, time, true);
            }
            return;
        }
        if (type.normal.has_value()) {
            // First value of a state type after the start (e.g. an OverloadAlarm only publishes when it changes): a change from normal
            if (type.isNormal(state)) {
                return;
            }
        }
    }
    publishState(side, entry, state, v, time, false);
}

void AlarmDetector::publishState(const AlarmSide& side, const AlarmEntry& entry, double state, double value, double time, bool initial) {
    const AlarmType& type = *entry.type;
    AlarmStateDisplay fallback;
    const AlarmStateDisplay* display;
    if (type.isThreshold()) {
        display = &type.levels.at(static_cast<size_t>(state));
    } else {
        std::string key = formatValue(state);
        if (type.states.contains(key)) {
            display = &type.states.at(key);
        } else {
            fallback.label = key;
            fallback.alarm = type.alarm;
            resolveDisplay(fallback, std::nullopt, std::nullopt);
            display = &fallback;
        }
    }

    nlohmann::json j = {
        {"id", entry.id},
        {"label", entry.label},
        {"time", time},
        {"value", value},
        {"state", display->label},
        {"kind", type.isThreshold() ? "threshold" : "state"},
        {"alarm", display->alarm},
        {"priority", display->priority},
        {"color", display->color},
        {"sound", display->sound.has_value() ? nlohmann::json(display->sound.value()) : nlohmann::json(nullptr)},
        {"mode", type.persistent ? "persistent" : "momentary"},
        {"retain", type.retain},
        {"normal", type.isNormal(state)},
        {"initial", initial},
    };
    if (type.isThreshold() && state > 0) {
        j["limit"] = entry.thresholds.at(static_cast<size_t>(state) - 1);  // Threshold of the level crossed
    }
    addLocation(j, entry);
    publisher_(side.subject, j.dump());
}

void AlarmDetector::publishCommand(const std::string& subject, const std::string& id, const Value& value, double time) {
    if (!commands_enabled_) {
        return;
    }
    bool configured = alarms_.contains(id);
    double v = value.to_double();
    nlohmann::json j = {
        {"id", id},
        {"label", configured ? alarms_.at(id).label : id},
        {"time", time},
        {"value", v},
        {"state", command_label_ + " " + formatValue(v)},
        {"kind", "command"},
        {"alarm", false},
        {"priority", command_display_.priority},
        {"color", command_display_.color},
        {"sound", nullptr},
        {"mode", "momentary"},
        {"retain", true},
        {"normal", false},
        {"initial", false},
    };
    if (configured) {
        addLocation(j, alarms_.at(id));
    }
    publisher_(subject, j.dump());
}

void AlarmDetector::republishActive(double time) {
    auto republish = [&](const AlarmSide& side) {
        for (const auto& [id, state] : side.states) {
            if (!alarms_.contains(id)) {
                continue;
            }
            const AlarmEntry& entry = alarms_.at(id);
            if ((entry.type->persistent || entry.type->isThreshold()) && !entry.type->isNormal(state)) {
                // The measured value is not dumped: the threshold of the level for threshold types
                double value = state;
                if (entry.type->isThreshold() && state > 0) {
                    value = entry.thresholds.at(static_cast<size_t>(state) - 1);
                }
                publishState(side, entry, state, value, time, true);
            }
        }
    };
    republish(game_master_);
    for (const auto& [destination, side] : scada_) {
        republish(side);
    }
}

std::string AlarmDetector::saveState() const {
    std::ostringstream bin(std::ios::binary);
    {
        ser20::BinaryOutputArchive archive(bin);
        archive(game_master_, scada_);
    }
    return bin.str();
}

void AlarmDetector::loadState(const std::string& bin) {
    std::istringstream ss(bin);
    ser20::BinaryInputArchive archive(ss);
    archive(game_master_, scada_);
    game_master_.subject = GAME_MASTER_SUBJECT;
    for (auto& [destination, side] : scada_) {
        side.subject = hmiSubject(destination);
    }
}

void AlarmDetector::onDumpStateEvent(const DumpStateEvent& event) {
    if (logger_ != nullptr) {
        logger_->saveDump(DUMP_NAME, event.time, saveState());
    }
}
