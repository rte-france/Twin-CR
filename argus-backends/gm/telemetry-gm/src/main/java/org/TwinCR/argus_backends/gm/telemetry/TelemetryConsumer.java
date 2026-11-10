/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.gm.telemetry;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import org.TwinCR.argus_backends.common.api.ApiServerCommon;
import org.TwinCR.argus_backends.common.api.ClickhouseClient;
import org.TwinCR.argus_backends.common.core.bridge.SseNatsBridge;
import org.TwinCR.argus_backends.common.core.config.ConfigCommon;
import org.TwinCR.argus_backends.common.datamodel.Value;
import org.TwinCR.argus_backends.common.gridmodel.GridModel;
import org.TwinCR.argus_backends.common.gridmodel.LatestValues;
import org.TwinCR.argus_backends.common.telemetry.TelemetryConsumerCommon;
import org.TwinCR.argus_backends.gm.gridmodel.GmMapping;
import org.TwinCR.argus_backends.gm.gridmodel.GmOutput;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import io.nats.client.*;

import java.io.IOException;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.LongAdder;

public class TelemetryConsumer extends TelemetryConsumerCommon {
    private final Logger LOGGER = LoggerFactory.getLogger(TelemetryConsumer.class);
    private final Dispatcher dispatcher;
    private final Map<String, AtomicInteger> refCounts = new ConcurrentHashMap<>();
    private final ClickhouseClient clickhouseClient;
    private double currentTime = 0;

    private static void recordLatestValue(String id, JsonNode node) {
        JsonNode rawValue = node.get("value");
        if (rawValue != null && (rawValue.isNumber() || rawValue.isBoolean())) {
            LatestValues.put(id, rawValue.isBoolean() ? (rawValue.asBoolean() ? 1 : 0) : rawValue.asDouble());
        }
    }

    public void handleMsg(JsonNode natsNode, GmOutput gmOutput) {
        if (gmOutput.equipmentId() == null || gmOutput.kind() == null) {
            return;
        }

        double value = natsNode.get("value").asDouble();
        String equipmentId = gmOutput.equipmentId();
        String kind = gmOutput.kind();
        String side = gmOutput.side();

        synchronized (GridModel.network) {
            GridModel.updatePhysicalValue(equipmentId, side, kind, value);
        }
    }

    public TelemetryConsumer(Connection conn, SseNatsBridge bridge, ConfigCommon config) {
        super(conn, bridge);
        this.clickhouseClient = new ClickhouseClient(conn, "backend_GM");

        ObjectMapper mapper = new ObjectMapper();

        LongAdder totalCounter = new LongAdder();
        LongAdder perSecondCounter = new LongAdder();

        ScheduledExecutorService scheduler = Executors.newSingleThreadScheduledExecutor();
        scheduler.scheduleAtFixedRate(() -> {
            long perSecond = perSecondCounter.sumThenReset();
            long total = totalCounter.sum();
            LOGGER.info("Messages received: {} - {} last second", total, perSecond);
        }, 1, 1, TimeUnit.SECONDS);


        this.dispatcher = conn.createDispatcher(msg -> {
            totalCounter.increment();
            perSecondCounter.increment();

            String subject = msg.getSubject();
            bridge.forward(subject, msg.getData());

            String data = new String(msg.getData());
            JsonNode node;
            Value value;
            try {
                node = mapper.readTree(data);
                value = mapper.treeToValue(node.get("value"), Value.class);
            } catch (JsonProcessingException e) {
                e.printStackTrace();
                return;
            }

            String id = node.get("id").asText();
            recordLatestValue(id, node);
            GmOutput gmOutput = GmMapping.id_2_gmOutput.get(id);
            if (gmOutput != null) {
                handleMsg(node, gmOutput);
            }

            GridModel.protectionEquipmentModel.updateByLibelle(id, value);
        });
        // No subscription by default, too expensive to subscribe to the full "GameMaster.>" topic, so subscriptions must be acquired individually
        // dispatcher.subscribe("GameMaster.>");

        Dispatcher forwarder = conn.createDispatcher(msg -> {
            String subject = msg.getSubject();
            bridge.forward(subject, msg.getData());
        });
        forwarder.subscribe("time");
        forwarder.subscribe("Dynawo.Timeline");
        forwarder.subscribe("Dynawo.Constraints");
        forwarder.subscribe("HMIControl.>");
        forwarder.subscribe("GameMasterControl.>");

        Dispatcher clock = conn.createDispatcher(msg -> {
            try {
                JsonNode node = mapper.readTree(msg.getData());
                currentTime = node.path("current_time").asDouble();
                LOGGER.info("Current time: {}", currentTime);
            } catch (IOException e) {
                LOGGER.warn("Invalid time message", e);
            }
        });
        clock.subscribe("time");
    }

    @Override
    public void acquireSubTopic(String subject) {
        refCounts.compute(subject, (s, counter) -> {
            if (counter == null) {
                // Add subscription
                String sanitizedTopic = ApiServerCommon.sanitizeNatsTopicName(subject);
                dispatcher.subscribe("GameMaster." + sanitizedTopic);
                updateNetwork(Optional.of(subject));
                return new AtomicInteger(1);
            }
            counter.incrementAndGet();
            return counter;
        });
    }

    @Override
    public void releaseSubTopic(String subject) {
        refCounts.computeIfPresent(subject, (s, counter) -> {
            if (counter.decrementAndGet() <= 0) {
                String sanitizedTopic = ApiServerCommon.sanitizeNatsTopicName(subject);
                dispatcher.unsubscribe("GameMaster." + sanitizedTopic);
                return null;
            }
            return counter;
        });
    }

    @Override
    public void updateNetwork(Optional<String> subject) {
        // Fetch latest values from Clickhouse to update network model (used to catch up before creating a new subscription)
        try {
            String data = clickhouseClient.queryLatestActualMeasurements(subject);
            ObjectMapper mapper = new ObjectMapper();
            JsonNode[] array = mapper.readValue(data, JsonNode[].class);
            for (JsonNode item : array) {
                String id = item.get("id").asText();
                Value value = mapper.treeToValue(item.get("value"), Value.class);
                recordLatestValue(id, item);

                GmOutput gmOutput = GmMapping.id_2_gmOutput.get(id);
                if (gmOutput != null) {
                    handleMsg(item, gmOutput);
                }

                GridModel.protectionEquipmentModel.updateByLibelle(id, value);
            }
        } catch (Exception e) {
            LOGGER.error("Error while fetching history for topic {}: {}", subject, e);
        }
    }
}
