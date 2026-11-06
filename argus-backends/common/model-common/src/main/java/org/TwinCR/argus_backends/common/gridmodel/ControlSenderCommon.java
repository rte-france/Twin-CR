/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.common.gridmodel;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.exc.StreamReadException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.DatabindException;

import org.TwinCR.argus_backends.common.core.config.ConfigCommon;
import org.TwinCR.argus_backends.common.core.util.FileLoader;
import org.TwinCR.argus_backends.common.datamodel.Value;

import com.fasterxml.jackson.databind.ObjectMapper;

import io.nats.client.Connection;
import io.nats.client.Message;

import java.io.IOException;
import java.time.Duration;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.TimeoutException;

public abstract class ControlSenderCommon {

    @JsonIgnoreProperties(ignoreUnknown = true)
    static class EquipmentEntry {
        public String equipmentId;
        public String kind;
        public String id;
    }

    protected static class Key {
        final String equipmentId;
        final String kind;

        public Key(String equipmentId, String kind) {
            this.equipmentId = equipmentId;
            this.kind = kind;
        }

        @Override
        public boolean equals(Object o) {
            if (this == o) return true;
            if (!(o instanceof Key)) return false;
            Key key = (Key) o;
            return Objects.equals(equipmentId, key.equipmentId)
                    && Objects.equals(kind, key.kind);
        }

        @Override
        public int hashCode() {
            return Objects.hash(equipmentId, kind);
        }
    }

    protected final Map<Key, String> idMap = new HashMap<>();
    private final Connection nats;
    private final ObjectMapper mapper = new ObjectMapper();

    public ControlSenderCommon(Connection nats, ConfigCommon config) throws IOException {
        this.nats = nats;

        String json = FileLoader.load(config.GmControlsPath());
        List<EquipmentEntry> entries = mapper.readValue(json, new TypeReference<List<EquipmentEntry>>() {});

        for (EquipmentEntry e : entries) {
            Key k = new Key(e.equipmentId, e.kind);
            idMap.put(k, e.id);
        }
    }

    public void sendControl(String id, Value value, String requester) throws InterruptedException, TimeoutException, StreamReadException, DatabindException, IOException {
        byte[] reqBytes = craftNatsPayload(id, value);

        Message msg = nats.request(
            natsTopic(requester),
            reqBytes,
            Duration.ofSeconds(5)
        );

        if (msg == null) {
            throw new java.util.concurrent.TimeoutException("No response from the Orchestrator");
        }

        Map<String, Object> resp = mapper.readValue(msg.getData(), new TypeReference<Map<String, Object>>() {});

        String status = String.valueOf(resp.get("status"));

        if ("OK".equals(status)) {
            return;
        } else {
            throw new RuntimeException("Control failed for id='" + id + "': " + status);
        }
    }

    public void sendControl(String equipmentId, String kind, Value value, String requester) throws InterruptedException, TimeoutException, StreamReadException, DatabindException, IOException {
        String id = idMap.get(new Key(equipmentId, kind));
        if (id == null) {
            throw new java.util.NoSuchElementException("Mapping not found for equipmentId='" + equipmentId + "', kind='" + kind + "'");
        }

        sendControl(id, value, requester);
    }

    public abstract boolean isControllable(String equipmentId, String kind);
    protected abstract byte[] craftNatsPayload(String id, Value value) throws JsonProcessingException;
    protected abstract String natsTopic(String requester);
}
