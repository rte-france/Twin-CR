/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef SUBSTATION_ALARM_H
#define SUBSTATION_ALARM_H

#include "ValueHolder.h"
#include "InformationFlowModel.h"

#include <nlohmann/json.hpp>

/**
 * ValueHolder with the key_ defined as "operator_in_" + config["substation_name"];
 */
class SubstationAlarm : public ValueHolder {
    public:
        virtual ~SubstationAlarm() = default;

        SubstationAlarm() = default;

        SubstationAlarm(const InformationFlowModel& information_flow_model, const nlohmann::json::basic_json::value_type& config);

        template<class Archive>
        void serialize(Archive& ar) {
            ar(ser20::base_class<ValueHolder>(this));
        }
};

SER20_REGISTER_TYPE(SubstationAlarm);
CHECK_SERIALIZABLE(SubstationAlarm);
CHECK_SERIALIZABLE(std::shared_ptr<SubstationAlarm>);

#endif // SUBSTATION_ALARM_H
