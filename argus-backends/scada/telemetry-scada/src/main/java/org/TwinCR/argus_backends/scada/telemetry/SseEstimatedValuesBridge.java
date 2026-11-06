/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.scada.telemetry;

import org.TwinCR.argus_backends.common.api.EstimatedValue;
import org.TwinCR.argus_backends.common.core.bridge.SseClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

public class SseEstimatedValuesBridge {
    private static final Logger LOGGER = LoggerFactory.getLogger(SseEstimatedValuesBridge.class);

    private final Map<String, Set<SseClient>> topicClients = new ConcurrentHashMap<>();

    public void register(String topic, SseClient client) {
        topicClients
            .computeIfAbsent(topic, k -> ConcurrentHashMap.newKeySet())
            .add(client);
    }

    public void remove(SseClient client) {
        topicClients.values().forEach(set -> set.remove(client));
    }

    /**
     * Called after each estimation run. Dispatches each EstimatedValue
     * to all clients subscribed to its topic.
     */
    public void forward(List<EstimatedValue> rows) {
        for (EstimatedValue row : rows) {
            Set<SseClient> clients = topicClients.get(row.topic());
            if (clients == null || clients.isEmpty()) continue;

            String payload;
            try {
                payload = row.toJson();
            } catch (IOException e) {
                LOGGER.error("Failed to serialize EstimatedValue for topic {}", row.topic(), e);
                continue;
            }

            clients.removeIf(client -> {
                try {
                    client.send(payload);
                    return false;
                } catch (IOException e) {
                    LOGGER.debug("Removing dead SSE client for topic {}", row.topic());
                    return true;
                }
            });
        }
    }
}
