/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.common.api;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.IOException;
import java.util.Optional;

public record EstimatedVariable(
    String equipmentId,
    String kind,
    Optional<String> side,
    String topic
) {
    private static final ObjectMapper MAPPER = new ObjectMapper();

    public String toJson() throws IOException {
        ObjectNode node = MAPPER.createObjectNode();
        node.put("equipmentId", equipmentId);
        node.put("kind",        kind);
        node.put("topic",       topic);
        side.ifPresentOrElse(
            s  -> node.put("side", s),
            () -> node.putNull("side")
        );
        return MAPPER.writeValueAsString(node);
    }
}
