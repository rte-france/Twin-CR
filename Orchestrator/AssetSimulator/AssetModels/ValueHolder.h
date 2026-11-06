/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef VALUE_HOLER_H
#define VALUE_HOLER_H

#include "AssetModelWithCommunications.h"
#include "InformationFlowModel.h"

#include <nlohmann/json.hpp>


/**
 * Simple class that stores a single value and republish it when it receives a new value
 */
class ValueHolder : public AssetModelWithCommunications {
    public:
        virtual ~ValueHolder() = default;

        ValueHolder() = default;  // For deserialisation

        ValueHolder(const InformationFlowModel& information_flow_model, const nlohmann::json::basic_json::value_type& config);
    protected:
        // Constructor for SubstationAlarm (reads id from config["substation_name"] instead of config["id"])
        ValueHolder(const InformationFlowModel& information_flow_model, const nlohmann::json::basic_json::value_type& config,
            std::string id,
            std::string class_name = "ValueHolder");

    public:
        virtual void onUpdate(const std::string& id, const Value& value, double time_received) override;

        virtual std::vector<std::string> getSubscriptions() override;

        template<class Archive>
        void serialize(Archive& ar) {
            ar(ser20::base_class<AssetModelWithCommunications>(this), key_, class_name_, value_);
        }

    private:
        std::string key_;
        std::string class_name_;
        Value value_;
};

SER20_REGISTER_TYPE(ValueHolder);
CHECK_SERIALIZABLE(ValueHolder);
CHECK_SERIALIZABLE(std::shared_ptr<ValueHolder>);

#endif // VALUE_HOLER_H
