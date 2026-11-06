/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef RECLOSER_H
#define RECLOSER_H

#include "SerialisationHelper.h"
#include "AssetModel.h"
#include <nlohmann/json.hpp>
#include <vector>

class Recloser : public AssetModel {
    public:
        virtual ~Recloser() = default;

        Recloser() = default;

        Recloser(const std::string& line_name, std::vector<double>& opening_times, std::vector<double>& closing_times);

        Recloser(const nlohmann::json::basic_json::value_type& config);

        // Recloser does not subscribe to events
        virtual void onUpdate(const std::string& id, const Value& value, double time_received) override {
            (void) id;
            (void) value;
            (void) time_received;
        };

        void openLine();

        void closeLine();

        template<class Archive>
        void serialize(Archive& ar) {
            ar(ser20::virtual_base_class<AssetModel>(this), line_name_);
        }

    private:
        void initialize(const std::string& line_name, std::vector<double>& opening_times, std::vector<double>& closing_times);

        std::string line_name_;
        std::vector<double> opening_times_;
        std::vector<double> closing_times_;
};

SER20_REGISTER_TYPE(Recloser);
CHECK_SERIALIZABLE(Recloser);
CHECK_SERIALIZABLE(std::shared_ptr<Recloser>);

#endif // RECLOSER_H
