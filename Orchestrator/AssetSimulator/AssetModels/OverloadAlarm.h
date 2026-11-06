/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef OVERLOAD_ALARM_H
#define OVERLOAD_ALARM_H

#include "AssetModelWithCommunications.h"
#include "InformationFlowModel.h"

#include <nlohmann/json.hpp>


class OverloadAlarm : public AssetModelWithCommunications {
    public:
        virtual ~OverloadAlarm() = default;

        OverloadAlarm() = default;

        OverloadAlarm(const InformationFlowModel& information_flow_model, const nlohmann::json::basic_json::value_type& config);

        virtual void onUpdate(const std::string& id, const Value& value, double time_received) override;

        virtual std::vector<std::string> getSubscriptions() override;

        template<class Archive>
        void serialize(Archive& ar) {
            ar(ser20::base_class<AssetModelWithCommunications>(this), current_key_, alarm_key_, max_current_, armed_);
        }
    private:
        void updateCurrent(double current, double time);

        std::string current_key_;
        std::string alarm_key_;
        double max_current_;
        bool armed_ = false;
};

SER20_REGISTER_TYPE(OverloadAlarm);
CHECK_SERIALIZABLE(OverloadAlarm);
CHECK_SERIALIZABLE(std::shared_ptr<OverloadAlarm>);

#endif // OVERLOAD_ALARM_H
