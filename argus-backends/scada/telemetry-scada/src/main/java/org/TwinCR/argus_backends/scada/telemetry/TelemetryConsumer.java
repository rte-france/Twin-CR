/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.scada.telemetry;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.powsybl.iidm.network.extensions.DiscreteMeasurement;
import com.powsybl.iidm.network.extensions.Measurement;

import org.TwinCR.argus_backends.scada.gridmodel.Ti;
import org.TwinCR.argus_backends.scada.gridmodel.TiHandler;
import org.TwinCR.argus_backends.scada.gridmodel.AssetOutputs;
import org.TwinCR.argus_backends.scada.gridmodel.TiMapping;
import org.TwinCR.argus_backends.scada.model.TelemetryMessage;
import org.TwinCR.argus_backends.scada.model.TelemetryMessage.Tase2Extension;
import org.TwinCR.argus_backends.scada.util.JsonUtil;
import org.TwinCR.argus_backends.common.core.bridge.SseNatsBridge;
import org.TwinCR.argus_backends.common.datamodel.Value;
import org.TwinCR.argus_backends.common.gridmodel.GridModel;
import org.TwinCR.argus_backends.common.telemetry.TelemetryConsumerCommon;
import org.TwinCR.argus_backends.scada.alarms.AlarmEngine;
import io.nats.client.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.LongAdder;

public class TelemetryConsumer extends TelemetryConsumerCommon {
    private static final Logger LOGGER = LoggerFactory.getLogger(TelemetryConsumer.class);
    private final Map<String, AbstractMap.SimpleEntry<Integer, Integer>> mapSubject2Count = new HashMap<>();
    private final Set<String> updatedMeasurements = Collections.synchronizedSet(new HashSet<>());
    private final Map<String, Double> mapMeasurementId2LastUpdateTime = new ConcurrentHashMap<>();
    private volatile double currentTime = 0;
    private final double estimPeriod;
    private double lastEstimTime = 0;
    private boolean estimRunnning = false;
    private final ExecutorService estimExecutor = Executors.newSingleThreadExecutor();
    private final Set<String> mappingNotFound = Collections.synchronizedSet(new HashSet<>());

    public double getSecondsSinceLastEstimTime() {
        return currentTime-lastEstimTime;
    }

    public double getProportionBeforeNextEstim() {
        double elapsed = currentTime-lastEstimTime;

        if (elapsed > estimPeriod) {
            return 0.0;
        }
        return (estimPeriod-elapsed)/estimPeriod;
    }

    public double getCurrentTime() {
        return currentTime;
    }

    public boolean isMeasurementStale(String measurementId, double timeout) {
        Double lastUpdateTime = mapMeasurementId2LastUpdateTime.get(measurementId);
        if (lastUpdateTime == null) {
            return true;
        }
        return currentTime - lastUpdateTime > timeout;
    }

    public void runEstim() throws IOException, InterruptedException {
        StateEstimator.runEstim(currentTime);
    }

    private void handleTelemetry(TelemetryMessage t) {
        String id;
        boolean validity;
        String equipmentId;
        String kind;
        String side;  // Nullable

        Measurement measurement = null;
        DiscreteMeasurement discreteMeasurement = null;

        final Tase2Extension tase2Extension = t.tase2;
        if (tase2Extension != null) {
            id = tase2Extension.tase2_id;
            validity = tase2Extension.validity == 0 ? true : false;  // Valid if 0

            Ti tiMapping = TiMapping.mapTase2_2_TI.get(id);
            if (tiMapping == null) {
                LOGGER.warn("No mapping foud for {}", id);
                return;
            }

            // Equipment the asset simulator drives, which the TI mapping cannot name
            AssetOutputs.Output assetOutput = AssetOutputs.get(tiMapping.libelle());
            if (assetOutput != null) {
                equipmentId = assetOutput.equipmentId();
                kind = assetOutput.kind();
                side = assetOutput.side();
            } else {
                TiHandler handler = new TiHandler(tiMapping);
                equipmentId = handler.getEquipmentId();
                kind = handler.getKind();
                side = handler.getSide();

                if (handler.getType().equals("TS")) {
                    // TS
                    String libelle = equipmentId + "_" + tiMapping.typ();
                    discreteMeasurement = TiMapping.libelle2DiscreteMeasurement.get(libelle);
                    if (discreteMeasurement == null && !mappingNotFound.contains(id)) {
                        LOGGER.debug("Handle TS - no discrete measurement found for {} ({}): valid={}, value={}", id, libelle, validity, t.value);
                        mappingNotFound.add(id);
                    }
                } else {
                    // TM
                    String libelle = tiMapping.oldLib();
                    String libelle2 = equipmentId + "_" + tiMapping.typ();
                    measurement = TiMapping.libelle2Measurement.get(libelle);
                    if (measurement == null)
                        measurement = TiMapping.libelle2Measurement.get(libelle2);
                    if (measurement == null) {
                        if (!mappingNotFound.contains(id)) {
                            LOGGER.warn("Handle TM - no mapping found for {} ({} or {}): valid={}, value={}", id, libelle, libelle2, validity, t.value);
                            mappingNotFound.add(id);
                        }
                        return;
                    }
                    if (TiMapping.initiallyInvalidMeasurements.contains(id)) {
                        // If a measurement is initially invalid, we do not update it
                        // Reason: if a measurement is initially invalid, it may be because the measurement plan
                        // doesn't handle this TM correctly (in other words, it has been invalidated for "structural reason")
                        LOGGER.debug("TM - measurement {} with value {} is previously invalid, not updating it with value {} and validity {}",
                            libelle, measurement.getValue(), t.value, validity
                        );
                        return;
                    }
                }
            }

        } else {
            id = t.id;
            validity = true;
            AssetOutputs.Output assetOutput = AssetOutputs.get(id);
            if (assetOutput != null) {
                equipmentId = assetOutput.equipmentId();
                kind = assetOutput.kind();
                side = assetOutput.side();
            } else {
                Ti measurementMapping = TiMapping.mapId_2_Output.get(id);
                if (measurementMapping == null) {
                    if (mappingNotFound.add(id)) {
                        LOGGER.warn("No mapping found for {}", id);
                    }
                    return;
                }
                kind = measurementMapping.kind();
                equipmentId = measurementMapping.equipmentId();
                side = measurementMapping.side();
            }

            measurement = TiMapping.libelle2Measurement.get(id);
            discreteMeasurement = TiMapping.libelle2DiscreteMeasurement.get(id);
        }
        updatedMeasurements.add(id);

        // Directly update the network for element status change (e.g. breaker open/close)
        if (validity && "state".equals(kind) && equipmentId != null) {
            synchronized (GridModel.network) {
                GridModel.updatePhysicalValue(equipmentId, side, kind, t.value.toDouble());
            }
        }

        // Update measurement extensions (not the actual network, the actual network model is updated by the state estimation)
        if (measurement != null) {
            synchronized (GridModel.network) {
                measurement.setValueAndValidity(t.value.toDouble(), validity);
            }
            mapMeasurementId2LastUpdateTime.put(measurement.getId(), currentTime);
        }
        if (discreteMeasurement != null) {
            synchronized (GridModel.network) {
                switch (t.value) {
                    case Value.BoolValue b -> discreteMeasurement.setValue(b.value());
                    case Value.IntValue i -> discreteMeasurement.setValue(i.value());
                    case Value.DoubleValue d -> LOGGER.warn("Unexpected double value for discrete measurement: " + d.value());
                }
                discreteMeasurement.setValid(validity);
            }
        }
        if (measurement == null && discreteMeasurement == null && !"state".equals(kind)) {
            if (!mappingNotFound.contains(id)) {
                LOGGER.warn("HandleTelemetry - no measurement/discrete measurement found for {}: value={}", id, t.value);
                mappingNotFound.add(id);
            }
        }
    }

    public TelemetryConsumer(Connection conn, SseNatsBridge bridge, AlarmEngine alarmEngine, double estimPeriod) throws Exception {
        super(conn, bridge);
        this.estimPeriod = estimPeriod;
        this.lastEstimTime = 0;
        this.estimRunnning = false;

        ObjectMapper mapper = new ObjectMapper();

        LongAdder totalCounter = new LongAdder();
        LongAdder perSecondCounter = new LongAdder();

        ScheduledExecutorService scheduler = Executors.newSingleThreadScheduledExecutor();

        scheduler.scheduleAtFixedRate(() -> {
            long perSecond = perSecondCounter.sumThenReset();
            long total = totalCounter.sum();
            LOGGER.info("SCADA messages received: {} - {} last second", total, perSecond);
        }, 1, 1, TimeUnit.SECONDS);

        Dispatcher dispatcher = conn.createDispatcher(msg -> {
            totalCounter.increment();
            perSecondCounter.increment();

            String subject = msg.getSubject();

            // TODO Make a "Controle General"

            try {
                TelemetryMessage t = JsonUtil.fromJson(msg.getData(), TelemetryMessage.class);
                boolean isProtectionTelemetry = GridModel.protectionEquipmentModel.updateByLibelle(t.id, t.value);
                if (isProtectionTelemetry) {
                    return;
                }
                if (alarmEngine != null) alarmEngine.evaluate(t);
                handleTelemetry(t);
                incrementGoodTelemetryMessage(subject);
            } catch (Exception e) {
                LOGGER.warn("Failed to parse {}: {}", new String(msg.getData(), StandardCharsets.UTF_8), e.getMessage());
                incrementBadTelemetryMessage(subject);
            }
        });

        dispatcher.subscribe("HMI.SCADA.>");

        Dispatcher forwarder = conn.createDispatcher(msg -> {
            String subject = msg.getSubject();
            bridge.forward(subject, msg.getData());
        });
        // TODO: remove Dynawo.Constraints subscription from SCADA once alarms are implemented
        forwarder.subscribe("Dynawo.Constraints");
        // HMI.SCADA.> subscription common with dispatcher to avoid lagging on synchronized called during state estimation
        forwarder.subscribe("HMI.SCADA.>");
        forwarder.subscribe("HMIControl.>");
        forwarder.subscribe("time");

        Dispatcher clock = conn.createDispatcher(msg -> {
            try {
                JsonNode node = mapper.readTree(msg.getData());
                currentTime = node.path("current_time").asDouble();
                LOGGER.info("Current time: {}", currentTime);
            } catch (IOException e) {
                LOGGER.warn("Invalid time message", e);
                return;
            }

            // Periodically run state estimation
            double nextEstimTime = lastEstimTime + estimPeriod;
            if (currentTime >= nextEstimTime && !estimRunnning) {
                LOGGER.info("At time {}, launching state estim", currentTime);
                estimRunnning = true;
                estimExecutor.submit(() -> {
                    try {
                        runEstim();
                        lastEstimTime = currentTime;
                        estimRunnning = false;
                    } catch (IOException | InterruptedException e) {
                        LOGGER.error("Exception while running estim: {}", currentTime, e.toString());
                        estimRunnning = false;
                    }
                });
            }
        });
        clock.subscribe("time");
    }

    private void incrementGoodTelemetryMessage(String subject) {
        AbstractMap.SimpleEntry<Integer, Integer> p = mapSubject2Count.get(subject);
        if (p == null) {
            p = new AbstractMap.SimpleEntry<Integer, Integer>(1, 0);
        } else {
            p = new AbstractMap.SimpleEntry<Integer, Integer>(p.getKey()+1, p.getValue());
        }
        mapSubject2Count.put(subject, p);
    }

    private void incrementBadTelemetryMessage(String subject) {
        AbstractMap.SimpleEntry<Integer, Integer> p = mapSubject2Count.get(subject);
        if (p == null) {
            p = new AbstractMap.SimpleEntry<Integer, Integer>(0, 1);
        } else {
            p.setValue(p.getValue()+1);
        }
        mapSubject2Count.put(subject, p);
    }

    public String getMapSubject2Count() throws Exception {
        return JsonUtil.toJson(mapSubject2Count);
    }

    public String getUnchangedMeasurements() throws Exception {
        List<Ti> notUpdated = new ArrayList<>();
        // Check TASE2 mappings
        for (Ti ti : TiMapping.mapTase2_2_TI.values()) {
            TiHandler handler = new TiHandler(ti);
            if ("TM".equals(handler.getType())) {
                String tase2 = handler.getTase2();
                if (tase2 != null && !updatedMeasurements.contains(tase2)) {
                    notUpdated.add(ti);
                }
            }
        }
        // Check non-TASE2 mappings
        for (Ti ti : TiMapping.mapId_2_Output.values()) {
            TiHandler handler = new TiHandler(ti);
            if ("TM".equals(handler.getType())) {
                String id = ti.id();
                if (id != null && !updatedMeasurements.contains(id)) {
                    // Check if not already added via tase2 (some items might be in both maps)
                    if (notUpdated.stream().noneMatch(n -> n.equals(ti))) {
                        notUpdated.add(ti);
                    }
                }
            }
        }

        notUpdated.sort(Comparator.comparing(ti -> new TiHandler(ti).getKind(), Comparator.nullsLast(Comparator.naturalOrder())));
        return JsonUtil.toJson(notUpdated);
    }

    @Override
    public void acquireSubTopic(String subTopic) {
        // Always subscribe to the full "HMI.SCADA.>" -> Nothing to do
    }

    @Override
    public void releaseSubTopic(String subTopic) {
        // Always subscribe to the full "HMI.SCADA.>" -> Nothing to do
    }

    @Override
    public void updateNetwork(Optional<String> subject) {
        // Network is always up to date -> Nothing to do
    }
}
