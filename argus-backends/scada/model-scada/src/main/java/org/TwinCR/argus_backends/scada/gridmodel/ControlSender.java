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
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;

import org.TwinCR.argus_backends.common.core.util.FileLoader;
import org.TwinCR.argus_backends.common.datamodel.Value;
import org.TwinCR.argus_backends.common.gridmodel.ControlSenderCommon;
import org.TwinCR.argus_backends.scada.config.Config;

import com.fasterxml.jackson.databind.ObjectMapper;

import io.nats.client.Connection;

import java.io.IOException;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public class ControlSender extends ControlSenderCommon {
    private final ObjectMapper mapper = new ObjectMapper();
    private final Map<String, String> id2tase2 = new HashMap<>();
    private final Set<String> controlableIds = new HashSet<>();

    @JsonIgnoreProperties(ignoreUnknown = true)
    static class MappingEntry {
        public String id;
        public String destination;
        @JsonInclude(JsonInclude.Include.NON_NULL)
        public String tase2;
    }

    public ControlSender(Connection nats, Config config) throws IOException {
        super(nats, config);

        String json = FileLoader.load(config.scadaInputsPath());
        List<MappingEntry> entries = mapper.readValue(json, new TypeReference<List<MappingEntry>>() {});

        for (MappingEntry e : entries) {
            controlableIds.add(e.id);
            if (e.tase2 != null) {
                id2tase2.put(e.id, e.tase2);
            }
        }
    }

    public boolean isControllable(String equipmentId, String kind) {
        String id = idMap.get(new Key(equipmentId, kind));
        if (id == null) {
            return false;
        }
        return controlableIds.contains(id);
    }

    @Override
    protected byte[] craftNatsPayload(String id, Value value) throws JsonProcessingException {
        if (!controlableIds.contains(id)) {
            throw new java.util.NoSuchElementException("Mapping found for id='" + id + "', but it is not controllable from the SCADA");
        }

        Map<String, Object> payload = new HashMap<>();
        payload.put("id", id);
        payload.put("value", value);

        String tase2Id = id2tase2.get(id);
        if (tase2Id != null) {
            String signalisationType = (value instanceof Value.BoolValue) ? "TC" : "TVC";
            Map<String, Object> tase2 = new HashMap<>();
            tase2.put("tase2_id", tase2Id);
            tase2.put("signalisation_type", signalisationType);
            tase2.put("cause", 3);  // Spontaneous
            tase2.put("validity", 0);  // Good
            tase2.put("operatorBlocked", false);
            payload.put("tase2", tase2);
        }

        return mapper.writeValueAsBytes(payload);
    }

    protected String natsTopic(String requester) {
        return "HMIControl." + requester;
    }
}
