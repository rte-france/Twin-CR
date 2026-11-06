/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.scada;

import io.nats.client.Connection;

import org.TwinCR.argus_backends.common.api.ClickhouseClient;
import org.TwinCR.argus_backends.common.core.bridge.SseNatsBridge;
import org.TwinCR.argus_backends.common.core.config.NatsConnectionFactory;
import org.TwinCR.argus_backends.common.core.ifl.InformationFlowModelLayout;
import org.TwinCR.argus_backends.common.gridmodel.GridModel;
import org.TwinCR.argus_backends.scada.alarms.AlarmEngine;
import org.TwinCR.argus_backends.scada.alarms.AlarmPublisher;
import org.TwinCR.argus_backends.scada.alarms.AlarmRule;
import org.TwinCR.argus_backends.scada.alarms.AlarmsStreamInitializer;
import org.TwinCR.argus_backends.scada.commands.CommandRequestHandler;
import org.TwinCR.argus_backends.scada.config.Config;
import org.TwinCR.argus_backends.scada.telemetry.SseEstimatedValuesBridge;
import org.TwinCR.argus_backends.scada.telemetry.StateEstimator;
import org.TwinCR.argus_backends.scada.telemetry.TelemetryConsumer;
import org.TwinCR.argus_backends.scada.telemetry.TelemetryStreamInitializer;
import org.TwinCR.argus_backends.scada.api.ApiServer;
import org.TwinCR.argus_backends.scada.gridmodel.ControlSender;
import org.TwinCR.argus_backends.scada.gridmodel.AssetOutputs;
import org.TwinCR.argus_backends.scada.gridmodel.TiMapping;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import picocli.CommandLine;

import java.nio.file.Path;
import java.time.Duration;
import java.time.Instant;
import java.util.Optional;

public class Main {
    private static final Logger LOGGER = LoggerFactory.getLogger(Main.class);

    public static void main(String[] args) throws Exception {
        LOGGER.info("Starting SCADA backend");

        // Parse CLI arguments using picocli
        Config config = new Config();
        int exitCode = new CommandLine(config).execute(args);
        if (exitCode != 0) {
            System.exit(exitCode);
        }

        String appName = "backend_SCADA";

        // Connect to NATS (patterns publish/subscribe and request/reply per NATS Java docs)
        Connection conn = NatsConnectionFactory.connect(config, appName);

        // Initialize streams
        TelemetryStreamInitializer.init(conn);
        AlarmsStreamInitializer.init(conn);

        // Build alarm engine
        AlarmPublisher publisher = new AlarmPublisher(conn);
        AlarmEngine engine = new AlarmEngine(publisher);
        engine.addRule(new AlarmRule("temperature", 80.0, true));

        // Load case
        Instant start = Instant.now();
        Path gridModelPath = config.gridModelPath();
        Path tiMappedPath = config.tiMappingPath();
        Optional<Path> geoDataPath = config.geoDataPath();
        GridModel.load(gridModelPath, tiMappedPath, geoDataPath);
        Instant end = Instant.now();
        long duration = Duration.between(start, end).toMillis();
        LOGGER.info("Grid case {} loaded from {} in {} ms", GridModel.network.getNameOrId(), config.gridModelPath(), duration);

        // Load mappings
        start = Instant.now();
        TiMapping.load(tiMappedPath);
        AssetOutputs.load(config.scadaMappingPath());
        end = Instant.now();
        duration = Duration.between(start, end).toMillis();
        LOGGER.info("{} loaded in {} ms ({} measurements)", tiMappedPath, duration, TiMapping.mapTase2_2_TI.size());

        // On scada side, measurements are mandatory
        if (TiMapping.mapTase2_2_TI.size() == 0 && TiMapping.mapId_2_Output.size() == 0) {
            LOGGER.error("No measurement in case, exiting");
            System.exit(1);
        }

        InformationFlowModelLayout.load(conn, "HMIControl.backend_SCADA", config);

        ControlSender controlSender = new ControlSender(conn, config);

        // Start services
        SseNatsBridge natsBridge = new SseNatsBridge();
        SseEstimatedValuesBridge estimatedValuesBridge = new SseEstimatedValuesBridge();
        ClickhouseClient clickhouseClient = new ClickhouseClient(conn, appName);
        StateEstimator.init(clickhouseClient, estimatedValuesBridge);

        new CommandRequestHandler().start(conn);
        TelemetryConsumer telemetryConsumer = new TelemetryConsumer(conn, natsBridge, engine, config.estimPeriod());
        new ApiServer(config, natsBridge, estimatedValuesBridge, conn, appName, engine, telemetryConsumer, controlSender);
    }
}
