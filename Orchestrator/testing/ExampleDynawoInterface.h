/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef EXAMPLE_DYNAWO_INTERFACE_H
#define EXAMPLE_DYNAWO_INTERFACE_H

#include "../utils/DynawoInterfaceInterface.h"
#include "DynawoHandlers/XmlHandler.h"
#include "DynawoInterface.h"

#include <nlohmann/json.hpp>

#include <filesystem>
#include <fstream>
#include <set>
#include <stdexcept>
#include <unordered_map>

/**
 * A mock of the DynawoInterface to read the dynawo_input and dynawo_output json's without starting Dynawo.
 * The logic is mostly copy-pasted from the actual DynawoInterface.
 */
class ExampleDynawoInterface : public DynawoInterfaceInterface {
    public:
        ExampleDynawoInterface(const std::filesystem::path& network_file, const std::filesystem::path& outputs_file, const std::filesystem::path& inputs_file) :
        network_(network_file) {
            load(outputs_file, iidm_to_dynawo_output_);
            load(inputs_file, iidm_to_dynawo_input_);
            loadDynamicModels(inputs_file, dynamic_model_to_dynawo_input_);
            loadDynamicModels(outputs_file, dynamic_model_to_dynawo_output_);
        }

        std::string getOutputFromIidm(const std::string& iidm_id, const std::string& attribute) const override {
            IIDM_key key(iidm_id, attribute);
            if (iidm_to_dynawo_output_.contains(key)) {
                return iidm_to_dynawo_output_.at(key);
            }
            throw std::invalid_argument("No game master output with iidm " + iidm_id + " and attribute " + attribute);
        }

        std::vector<std::string> listIidmIds(const std::string& pypowsybl_type) const override {
            return network_.getIds(pypowsybl_type);
        }

        std::vector<std::string> listInputAttributes(const std::string& iidm_id) const override {
            return attributesOf(iidm_to_dynawo_input_, iidm_id);
        }

        std::vector<std::string> listOutputAttributes(const std::string& iidm_id) const override {
            return attributesOf(iidm_to_dynawo_output_, iidm_id);
        }

        bool hasInput(const std::string& iidm_id, const std::string& attribute) const {
            return iidm_to_dynawo_input_.contains(IIDM_key(iidm_id, attribute));
        }

        std::string getInputFromDynamicModel(const std::string& dynamic_model, const std::string& kind) const {
            DynamicModel_key key(dynamic_model, kind);
            if (dynamic_model_to_dynawo_input_.contains(key)) {
                return dynamic_model_to_dynawo_input_.at(key);
            }
            throw std::invalid_argument("No game master input with model " + dynamic_model + " and kind " + kind);
        }

        std::vector<std::string> listDynamicModelLibs(DynamicModelDirection direction) const override {
            std::set<std::string> libs;
            for (auto& [key, dynawo_id] : mappingFor(direction)) {
                if (model_lib_by_dynamic_model_.contains(key.dynamic_model)) {
                    libs.insert(model_lib_by_dynamic_model_.at(key.dynamic_model));
                }
            }
            return {libs.begin(), libs.end()};
        }

        std::vector<std::string> listDynamicModelIds(const std::string& model_lib, DynamicModelDirection direction) const override {
            std::set<std::string> dynamic_models;
            for (auto& [key, dynawo_id] : mappingFor(direction)) {
                if (model_lib_by_dynamic_model_.contains(key.dynamic_model)
                    && model_lib_by_dynamic_model_.at(key.dynamic_model) == model_lib) {
                    dynamic_models.insert(key.dynamic_model);
                }
            }
            return {dynamic_models.begin(), dynamic_models.end()};
        }

        std::vector<std::string> listDynamicModelInputKinds(const std::string& dynamic_model) const override {
            return kindsOf(dynamic_model_to_dynawo_input_, dynamic_model);
        }

        std::vector<std::string> listDynamicModelOutputKinds(const std::string& dynamic_model) const override {
            return kindsOf(dynamic_model_to_dynawo_output_, dynamic_model);
        }

        std::string getOutputFromDynamicModel(const std::string& dynamic_model, const std::string& kind) const override {
            DynamicModel_key key(dynamic_model, kind);
            if (dynamic_model_to_dynawo_output_.contains(key)) {
                return dynamic_model_to_dynawo_output_.at(key);
            }
            throw std::invalid_argument("No game master output with model " + dynamic_model + " and kind " + kind);
        }

    private:
        // Mirrors DynawoInterface's own reading of these files
        static void load(const std::filesystem::path& path, std::unordered_map<IIDM_key, std::string, IIDM_key_hash>& mapping) {
            std::ifstream stream(path);
            if (!stream.is_open()) throw std::runtime_error("Cannot open mapping file: " + path.string());
            for (auto entry : nlohmann::json::parse(stream)) {
                if (!entry.contains("equipmentId") || !entry["equipmentId"].is_string()) continue;  // Dynamic model, see loadDynamicModels
                std::string id = entry["id"];
                std::string iidm_id = entry["equipmentId"];
                std::string attribute = entry["kind"];
                if (entry.contains("side")) {
                    std::string side = entry["side"];
                    attribute += sideToNumeric(side);
                }
                mapping[IIDM_key(iidm_id, attribute)] = id;
            }
        }

        /** The entries with no equipmentId, keyed on their own name instead. */
        void loadDynamicModels(const std::filesystem::path& path,
                                std::unordered_map<DynamicModel_key, std::string, DynamicModel_key_hash>& mapping) {
            std::ifstream stream(path);
            if (!stream.is_open()) throw std::runtime_error("Cannot open mapping file: " + path.string());
            for (auto entry : nlohmann::json::parse(stream)) {
                if (entry.contains("equipmentId") && entry["equipmentId"].is_string()) continue;
                if (!entry.contains("model") || !entry.contains("model_lib")) continue;
                std::string dynamic_model = entry["model"];
                std::string attribute = entry["kind"];
                mapping[DynamicModel_key(dynamic_model, attribute)] = entry["id"];
                model_lib_by_dynamic_model_[dynamic_model] = entry["model_lib"];
            }
        }

        static std::string sideToNumeric(const std::string& side) {
            if (side == "ONE") return "1";
            if (side == "TWO") return "2";
            if (side == "THREE") return "3";
            throw std::invalid_argument("Unknown side: " + side);
        }

        IIDMHandler network_;
        static std::vector<std::string> attributesOf(const std::unordered_map<IIDM_key, std::string, IIDM_key_hash>& mapping,
                                                      const std::string& iidm_id) {
            std::vector<std::string> attributes;
            for (auto& [key, dynawo_id] : mapping) {
                if (key.iidm_id == iidm_id) attributes.push_back(key.attribute);
            }
            return attributes;
        }

        std::unordered_map<IIDM_key, std::string, IIDM_key_hash> iidm_to_dynawo_output_;
        std::unordered_map<IIDM_key, std::string, IIDM_key_hash> iidm_to_dynawo_input_;
        const std::unordered_map<DynamicModel_key, std::string, DynamicModel_key_hash>& mappingFor(DynamicModelDirection direction) const {
            return direction == DynamicModelDirection::Input ? dynamic_model_to_dynawo_input_ : dynamic_model_to_dynawo_output_;
        }

        static std::vector<std::string> kindsOf(const std::unordered_map<DynamicModel_key, std::string, DynamicModel_key_hash>& mapping,
                                                 const std::string& dynamic_model) {
            std::vector<std::string> kinds;
            for (auto& [key, dynawo_id] : mapping) {
                if (key.dynamic_model == dynamic_model) kinds.push_back(key.kind);
            }
            return kinds;
        }

        std::unordered_map<DynamicModel_key, std::string, DynamicModel_key_hash> dynamic_model_to_dynawo_input_;
        std::unordered_map<DynamicModel_key, std::string, DynamicModel_key_hash> dynamic_model_to_dynawo_output_;
        std::unordered_map<std::string, std::string> model_lib_by_dynamic_model_;
};

#endif // EXAMPLE_DYNAWO_INTERFACE_H
