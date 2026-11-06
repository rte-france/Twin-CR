/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.gm.gridmodel;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.annotation.JsonDeserialize;

import org.TwinCR.argus_backends.common.core.util.PooledString;

// One entry of the game master output mapping, holding only the fields the backend reads.
@JsonIgnoreProperties(ignoreUnknown = true)
public record GmOutput(
        @JsonProperty("id") String id,
        @JsonProperty("equipmentId") @JsonDeserialize(using = PooledString.class) String equipmentId,
        @JsonProperty("kind") @JsonDeserialize(using = PooledString.class) String kind,
        @JsonProperty("side") @JsonDeserialize(using = PooledString.class) String side,
        @JsonProperty("voltage_level") @JsonDeserialize(using = PooledString.class) String voltageLevel) {
}
