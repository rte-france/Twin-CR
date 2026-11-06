/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef ASSET_MODEL_H
#define ASSET_MODEL_H

#include <ser20/types/polymorphic.hpp>
#include <ser20/archives/binary.hpp>
#include <string>

#include "Value.h"
#include "SerialisationHelper.h"

class AssetModel {
    public:
        virtual ~AssetModel() = default;

        virtual void onUpdate(const std::string& id, const Value& value, double time_received) = 0;

        template<class Archive>
        void serialize(Archive& ar) {
            ar();
        }

    private:
};

SER20_REGISTER_TYPE(AssetModel);
CHECK_SERIALIZABLE(AssetModel);
CHECK_SERIALIZABLE(std::shared_ptr<AssetModel>);

#endif // ASSET_MODEL_H
