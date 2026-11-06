/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "CommunicationLinks.h"


CommunicationLink::CommunicationLink(std::string source, std::string destination, std::string channel_type) :
source_(source),
destination_(destination),
channel_type_(channel_type) {
    // Seed the element based on the name of the link
    std::hash<std::string> hasher;
    std::stringstream name;
    name << source_ << "_" << destination;
    seed_ = hasher(name.str());
}
