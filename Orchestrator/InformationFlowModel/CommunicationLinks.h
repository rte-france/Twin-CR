/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef COMMUNICATION_LINKS_H
#define COMMUNICATION_LINKS_H

#include "CommunicationElements.h"

class CommunicationLink : public CommunicationElement {
    public:
        CommunicationLink(std::string source, std::string destination, std::string channel_type);
        CommunicationLink() = default;  // Default constructor needed for deserialization

        std::string getSource() const { return source_; }
        std::string getDestination() const { return destination_; }
        std::string getChannelType() const { return channel_type_; }

        template<class Archive>
        void serialize(Archive& ar) {
            ar(ser20::base_class<CommunicationElement>(this), source_, destination_, channel_type_);
        }

    private:
        std::string source_;
        std::string destination_;
        std::string channel_type_;
};
SER20_REGISTER_TYPE(CommunicationLink);  // Necessary for polymorphic types
CHECK_SERIALIZABLE(CommunicationLink);

#endif // COMMUNICATION_LINKS_H
