/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef DYNAWO_INTERFACE_INTERFACE_H
#define DYNAWO_INTERFACE_INTERFACE_H

#include <string>
#include <vector>

/**
 * Which half of a dynamic model's mapping a listing is about: what can be written to it, or read from it.
 */
enum class DynamicModelDirection { Input, Output };

/**
 * Interface of the DynawoInterface. Currently implemented by the DynawoInterface itself and by a mock (testing/ExampleDynawoInterface.h)
 */
class DynawoInterfaceInterface {
    public:
        virtual ~DynawoInterfaceInterface() = default;
        virtual std::string getOutputFromIidm(const std::string& iidm_id, const std::string& attribute) const = 0;
        virtual std::vector<std::string> listIidmIds(const std::string& pypowsybl_type) const = 0;

        virtual std::vector<std::string> listInputAttributes(const std::string& iidm_id) const = 0;
        virtual std::vector<std::string> listOutputAttributes(const std::string& iidm_id) const = 0;

        /**
         * Inputs and outputs on purely dynamic models, which have no equipmentId and are keyed on their own name and kind instead.
         */
        virtual std::string getOutputFromDynamicModel(const std::string& dynamic_model, const std::string& kind) const = 0;
        virtual std::vector<std::string> listDynamicModelLibs(DynamicModelDirection direction) const = 0;
        virtual std::vector<std::string> listDynamicModelIds(const std::string& model_lib, DynamicModelDirection direction) const = 0;
        virtual std::vector<std::string> listDynamicModelInputKinds(const std::string& dynamic_model) const = 0;
        virtual std::vector<std::string> listDynamicModelOutputKinds(const std::string& dynamic_model) const = 0;
};

#endif // DYNAWO_INTERFACE_INTERFACE_H
