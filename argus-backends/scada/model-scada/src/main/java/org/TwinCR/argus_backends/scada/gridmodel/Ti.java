/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.scada.gridmodel;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.annotation.JsonDeserialize;

import org.TwinCR.argus_backends.common.core.util.PooledString;

// One entry of the TI mapping file, holding only the fields the backend reads (don't store everything as the file is quite large)
@JsonIgnoreProperties(ignoreUnknown = true)
@JsonInclude(JsonInclude.Include.NON_NULL)
public record Ti(
        @JsonProperty("type") @JsonDeserialize(using = PooledString.class) String type,
        @JsonProperty("tase2") String tase2,
        @JsonProperty("id") String id,
        @JsonProperty("libelle") String libelle,
        @JsonProperty("old_lib") String oldLib,
        @JsonProperty("typ") @JsonDeserialize(using = PooledString.class) String typ,
        @JsonProperty("iidm") @JsonDeserialize(using = PooledString.class) String iidm,
        @JsonProperty("bayiidm") @JsonDeserialize(using = PooledString.class) String bayiidm,
        @JsonProperty("iidmdj") @JsonDeserialize(using = PooledString.class) String iidmdj,
        @JsonProperty("bayt") @JsonDeserialize(using = PooledString.class) String bayt,
        @JsonProperty("pointclass") @JsonDeserialize(using = PooledString.class) String pointclass,
        @JsonProperty("side") @JsonDeserialize(using = PooledString.class) String side,
        @JsonProperty("equipmentId") @JsonDeserialize(using = PooledString.class) String equipmentId,
        @JsonProperty("kind") @JsonDeserialize(using = PooledString.class) String kind) {
}
