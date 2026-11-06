/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.gm.gridmodel;

import com.fasterxml.jackson.core.JsonProcessingException;

import org.TwinCR.argus_backends.common.core.config.ConfigCommon;
import org.TwinCR.argus_backends.common.datamodel.Value;
import org.TwinCR.argus_backends.common.gridmodel.ControlSenderCommon;

import com.fasterxml.jackson.databind.ObjectMapper;

import io.nats.client.Connection;

import java.io.IOException;
import java.util.Map;

public class ControlSender extends ControlSenderCommon {
    private final ObjectMapper mapper = new ObjectMapper();

    public ControlSender(Connection nats, ConfigCommon config) throws IOException {
        super(nats, config);
    }

    public boolean isControllable(String equipmentId, String kind) {
        return idMap.containsKey(new Key(equipmentId, kind));
    }

    @Override
    protected byte[] craftNatsPayload(String id, Value value) throws JsonProcessingException {
        Map<String, Object> payload = Map.of(
            "id", id,
            "value", value
        );
        return mapper.writeValueAsBytes(payload);
    }

    protected String natsTopic(String requester) {
        return "GameMasterControl." + requester;
    }
}
