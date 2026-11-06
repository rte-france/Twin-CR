/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef ASSET_MODEL_WITH_COMMUNICATIONS_H
#define ASSET_MODEL_WITH_COMMUNICATIONS_H

#include "AssetModel.h"
#include "InformationFlowModel.h"
#include "Tase2.h"

#include "graaflib/types.h"
#include <nlohmann/json.hpp>

#include <optional>
#include <string>
#include <vector>


class AssetModelWithCommunications : public AssetModel {
    public:
        AssetModelWithCommunications() = default;
        AssetModelWithCommunications(const InformationFlowModel& information_flow_model, const nlohmann::json::basic_json::value_type& config);

        virtual void onUpdate(const std::string& id, const Value& value, double time_received) = 0;

        virtual std::vector<std::string> getSubscriptions() = 0;

        std::string getLocation() { return location_; }

        template<class Archive>
        void serialize(Archive& ar) {
            ar(ser20::virtual_base_class<AssetModel>(this), location_, destination_, topic_, routing_, tase2_extension_);
        }
    protected:
        std::string location_;
        std::string destination_;
        std::string topic_;
        std::vector<graaf::vertex_id_t> routing_;
        std::optional<tase2::Tase2Extension> tase2_extension_;
};

SER20_REGISTER_TYPE(AssetModelWithCommunications);
CHECK_SERIALIZABLE(AssetModelWithCommunications);
CHECK_SERIALIZABLE(std::shared_ptr<AssetModelWithCommunications>);

#endif // ASSET_MODEL_WITH_COMMUNICATIONS_H
