/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "XmlHandler.h"
#include "DynawoHandlers/DynawoEvents.h"

#include <optional>
#include <spdlog/spdlog.h>

#include <cstddef>
#include <unordered_set>


/**
 * Make an XPath query based on a list of parts.
 * [local-name()] is used to disregard namespaces
 */
std::string make_xpath_query(const std::vector<std::string>& parts) {
    std::ostringstream xpath;
    for (const auto& name : parts) {
        xpath << "/*[local-name()='" << name << "']";
    }
    return xpath.str();
}

XMLHandler::XMLHandler(const std::filesystem::path &xml_file) {
    pugi::xml_parse_result result = doc_.load_file(xml_file.c_str());
    if (result) {
        // Success
    } else {
        spdlog::critical("{} parsed with errors, attr value: []", xml_file.string(), doc_.child("node").attribute("attr").value());
        throw std::runtime_error("Failed to read XML file: " + std::string(result.description()));
    }
    path_ = xml_file;
}

std::unordered_map<std::string, std::unique_ptr<DynawoEvent>> DydHandler::getEvents() {
    pugi::xpath_node_set models = doc_.select_nodes("//*[local-name()='blackBoxModel'][starts-with(@lib, 'Event') or starts-with(@lib, 'DYNModelUpdatable')] | //*[local-name()='blackBoxModel'][@lib='SetPoint']");
    std::unordered_map<std::string, std::unique_ptr<DynawoEvent>> events;

    for (auto node: models) {
        std::string id = node.node().attribute("id").value();
        std::string lib = node.node().attribute("lib").value();
        switch (stringToDynawoEventClass(lib)) {
            case DynawoEventClasses::EventQuadripoleDisconnection:
                events[id] = std::make_unique<EventQuadripoleDisconnection>(id);
                break;
            case DynawoEventClasses::EventConnectedStatus:
                events[id] = std::make_unique<EventConnectedStatus>(id);
                break;
            case DynawoEventClasses::EventQuadripoleConnection:
                events[id] = std::make_unique<EventQuadripoleConnection>(id);
                break;
            case DynawoEventClasses::EventSetPointBoolean:
                events[id] = std::make_unique<EventSetPointBoolean>(id);
                break;
            case DynawoEventClasses::EventSetPointReal:
                events[id] = std::make_unique<EventSetPointReal>(id);
                break;
            case DynawoEventClasses::SetPoint:
                events[id] = std::make_unique<SetPoint>(id);
                break;
            case DynawoEventClasses::UpdatableBoolean:
                events[id] = std::make_unique<UpdatableBoolean>(id);
                break;
            case DynawoEventClasses::UpdatableInteger:
                events[id] = std::make_unique<UpdatableInteger>(id);
                break;
            case DynawoEventClasses::UpdatableDiscrete:
                events[id] = std::make_unique<UpdatableDiscrete>(id);
                break;
            case DynawoEventClasses::UpdatableContinuous:
                events[id] = std::make_unique<UpdatableContinuous>(id);
                break;
            default:
                throw std::runtime_error(lib + " not in DynawoEventClasses");
        }
    }
    return events;
}

std::unordered_set<std::filesystem::path> DydHandler::getReferencedParFiles() {
    std::unordered_set<std::filesystem::path> paths;

    for (auto black_box_model : doc_.select_nodes(make_xpath_query({"dynamicModelsArchitecture", "blackBoxModel"}).c_str())) {
        std::string par_file = black_box_model.node().attribute("parFile").value();
        if (!par_file.empty()) {  // Some blackbox models don't have a parFile (e.g. DYNModelUpdatables)
            paths.insert(getWorkingDir() / par_file);
        }
    }

    return paths;
}

std::filesystem::path JobHandler::getIidm() {
    pugi::xpath_node network_node = doc_.select_node(make_xpath_query({"jobs", "job", "modeler", "network"}).c_str());
    if (network_node != nullptr)
        return getWorkingDir() / network_node.node().attribute("iidmFile").value();

    throw std::runtime_error("Iidm field not found in job file");
}

std::optional<std::filesystem::path> JobHandler::getOutputDir() {
    pugi::xpath_node outputs_node = doc_.select_node(make_xpath_query({"jobs", "job", "outputs"}).c_str());
    if (outputs_node == nullptr)
        return std::nullopt;

    return getWorkingDir() / outputs_node.node().attribute("directory").value();
}

std::vector<std::filesystem::path> JobHandler::getLogPaths() {
    auto output_dir = getOutputDir();
    if (!output_dir.has_value())
        return {};

    std::vector<std::filesystem::path> log_paths;
    pugi::xpath_node_set log_nodes = doc_.select_nodes(make_xpath_query({"jobs", "job", "outputs", "logs", "appender"}).c_str());
    for (auto log_node : log_nodes) {
        log_paths.push_back((*output_dir) / "logs" / log_node.node().attribute("file").value());
    }

    return log_paths;
}

std::optional<std::filesystem::path> JobHandler::getOutputIidmPath() {
    auto output_dir = getOutputDir();
    if (!output_dir.has_value())
        return std::nullopt;

    pugi::xpath_node final_state_node = doc_.select_node(make_xpath_query({"jobs", "job", "outputs", "finalState"}).c_str());
    if (final_state_node == nullptr)
        return std::nullopt;

    std::string exported = final_state_node.node().attribute("exportIIDMFile").value();
    if (exported == "true")
        return (*output_dir) / "finalState/outputIIDM.xml";
    else
        return std::nullopt;
}

/**
 * Set a string to lower case
 */
inline void to_lower(std::string& s) {
    std::transform(s.begin(), s.end(), s.begin(),
        [](unsigned char c){ return std::tolower(c); });
}

std::optional<std::filesystem::path> JobHandler::getOutputFinalStateValuesPath() {
    auto output_dir = getOutputDir();
    if (!output_dir.has_value())
        return std::nullopt;

    pugi::xpath_node fsv_node = doc_.select_node(make_xpath_query({"jobs", "job", "outputs", "finalStateValues"}).c_str());
    if (fsv_node == nullptr) {
        return std::nullopt;
    } else {
        std::string export_mode = fsv_node.node().attribute("exportMode").value();
        to_lower(export_mode);

        return (*output_dir) / fmt::format("finalStateValues/finalStateValues.{}", export_mode);
    }
}

// Does not include the dyd file which itself has references
const std::vector<std::pair<std::string, std::string>> jobFileReferences = {
    {"solver", "parFile"},
    {"network", "parFile"},
    {"network", "iidmFile"},
    {"criteria", "criteriaFile"},
    {"curves", "inputFile"},
};

/**
 * Return working_dir / attribute value for every element named `tag` that has a
 * non-empty `attribute_name` attribute, searching the whole document (e.g. multiple
 * jobs in the same jobs file each get their own solver/network/criteria/curves).
 */
std::unordered_set<std::filesystem::path> find_referenced_paths(const pugi::xml_document& doc, const std::filesystem::path& working_dir,
                                                                const std::string& tag, const std::string& attribute_name) {
    std::unordered_set<std::filesystem::path> paths;
    for (auto node : doc.select_nodes(("//*[local-name()='" + tag + "']").c_str())) {
        std::string value = node.node().attribute(attribute_name.c_str()).value();
        if (!value.empty())
            paths.insert(working_dir / value);
    }
    return paths;
}

std::unordered_set<std::filesystem::path> JobHandler::getAllInputPaths() {
    std::unordered_set<std::filesystem::path> paths;
    std::filesystem::path working_dir = getWorkingDir();
    // Jobs
    paths.insert(getPath());

    // Solver par file, network par file, criteria file, curve file
    for (const auto& [tag, attribute_name] : jobFileReferences) {
        auto referenced_paths = find_referenced_paths(doc_, working_dir, tag, attribute_name);
        paths.insert(referenced_paths.begin(), referenced_paths.end());
    }

    // Dyd files and the par files referenced in those dyd files
    for (auto dyn_node : doc_.select_nodes(make_xpath_query({"jobs", "job", "modeler", "dynModels"}).c_str())) {
        std::filesystem::path dyn_path = working_dir / dyn_node.node().attribute("dydFile").value();
        paths.insert(dyn_path);

        for (auto& par_file : DydHandler(dyn_path).getReferencedParFiles()) {
            paths.insert(par_file);
        }
    }

    return paths;
}


double JobHandler::getStartTime() {
    pugi::xpath_node simulation_node = doc_.select_node(make_xpath_query({"jobs", "job", "simulation"}).c_str());
    if (simulation_node != nullptr)
        return std::stod(simulation_node.node().attribute("startTime").value());

    throw std::runtime_error("Start time not found in job file");
}

double JobHandler::getStopTime() {
    pugi::xpath_node simulation_node = doc_.select_node(make_xpath_query({"jobs", "job", "simulation"}).c_str());
    if (simulation_node != nullptr)
        return std::stod(simulation_node.node().attribute("stopTime").value());

    throw std::runtime_error("Stop time not found in job file");
}

bool JobHandler::hasTimeline() {
    pugi::xpath_node model = doc_.select_node("//*[local-name()='timeline']");
    return model != nullptr;
}

bool JobHandler::hasConstraints() {
    pugi::xpath_node model = doc_.select_node("//*[local-name()='constraints']");
    return model != nullptr;
}

static const std::unordered_map<std::string, std::string> PYPOWSYBL_TYPE_TO_IIDM_TAG = {
    {"2_windings_transformer", "twoWindingsTransformer"},
    {"3_windings_transformer", "threeWindingsTransformer"},
    {"battery", "battery"},
    {"dangling_line", "danglingLine"},
    {"generator", "generator"},
    {"hvdc_line", "hvdcLine"},
    {"lcc_converter_station", "lccConverterStation"},
    {"line", "line"},
    {"load", "load"},
    {"shunt_compensator", "shunt"},
    {"static_var_compensator", "staticVarCompensator"},
    {"substation", "substation"},
    {"switch", "switch"},
    {"voltage_level", "voltageLevel"},
    {"vsc_converter_station", "vscConverterStation"},
    {"tie_line", "tieLine"},
};

// Phase/ratio tap changers require separate handling from PYPOWSYBL_TYPE_TO_IIDM_TAG since they do not have
// an id of their own but inherit the id from their parent transformer
static const std::unordered_map<std::string, std::string> TAP_CHANGER_TYPE_TO_IIDM_TAG = {
    {"phase_tap_changer", "phaseTapChanger"},
    {"ratio_tap_changer", "ratioTapChanger"},
};

// Reverse of PYPOWSYBL_TYPE_TO_IIDM_TAG
static const std::unordered_map<std::string, std::string> IIDM_TAG_TO_PYPOWSYBL_TYPE = [] {
    std::unordered_map<std::string, std::string> reversed;
    for (auto& [type, tag] : PYPOWSYBL_TYPE_TO_IIDM_TAG) reversed[tag] = type;
    return reversed;
}();

// Reverse of TAP_CHANGER_TYPE_TO_IIDM_TAG
static const std::unordered_map<std::string, std::string> IIDM_TAG_TO_TAP_CHANGER_TYPE = [] {
    std::unordered_map<std::string, std::string> reversed;
    for (auto& [type, tag] : TAP_CHANGER_TYPE_TO_IIDM_TAG) reversed[tag] = type;
    return reversed;
}();

// Get the node name without the xml namespace
static std::string localName(const pugi::xml_node& node) {
    std::string name = node.name();
    auto colon = name.find(':');
    return colon == std::string::npos ? name : name.substr(colon + 1);
}

// Single recursive walk of the whole document, use to precomputed IIDMHandler::getIds(pypowsybl_type)
static void collectIds(const pugi::xml_node& node, std::unordered_map<std::string, std::vector<std::string>>& ids_by_type) {
    std::string local_name = localName(node);

    if (IIDM_TAG_TO_PYPOWSYBL_TYPE.contains(local_name)) {
        std::string id = node.attribute("id").value();
        if (!id.empty()) ids_by_type[IIDM_TAG_TO_PYPOWSYBL_TYPE.at(local_name)].push_back(id);
    } else if (IIDM_TAG_TO_TAP_CHANGER_TYPE.contains(local_name)) {
        // Phase/ratio tap changers have no id of their own; use the owning transformer's id.
        std::string id = node.parent().attribute("id").value();
        if (!id.empty()) ids_by_type[IIDM_TAG_TO_TAP_CHANGER_TYPE.at(local_name)].push_back(id);
    }

    for (auto child : node.children()) {
        collectIds(child, ids_by_type);
    }
}

IIDMHandler::IIDMHandler(const std::filesystem::path& xml_file) : XMLHandler(xml_file) {
    collectIds(doc_, ids_by_type_);
    // Handler only used for getIds(), so the doc memory can be freed
    doc_.reset();
}

std::vector<std::string> IIDMHandler::getIds(const std::string& pypowsybl_type) const {
    if (!PYPOWSYBL_TYPE_TO_IIDM_TAG.contains(pypowsybl_type) && !TAP_CHANGER_TYPE_TO_IIDM_TAG.contains(pypowsybl_type)) {
        throw std::invalid_argument("Unknown/unsupported grid element type for IIDM lookup: " + pypowsybl_type);
    }

    if (ids_by_type_.contains(pypowsybl_type)) {
        return ids_by_type_.at(pypowsybl_type);
    } else {
        // Type can be absent from ids_by_type_ if the grid has no element of this type
        return {};
    }
}
