/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.gm;

import io.nats.client.Connection;
import picocli.CommandLine;

import java.nio.file.Path;
import java.time.Duration;
import java.time.Instant;
import java.util.Optional;

import org.TwinCR.argus_backends.common.core.bridge.SseNatsBridge;
import org.TwinCR.argus_backends.common.core.config.NatsConnectionFactory;
import org.TwinCR.argus_backends.common.core.ifl.InformationFlowModelLayout;
import org.TwinCR.argus_backends.common.gridmodel.GridModel;
import org.TwinCR.argus_backends.gm.api.ApiServer;
import org.TwinCR.argus_backends.gm.core.config.Config;
import org.TwinCR.argus_backends.gm.gridmodel.ControlSender;
import org.TwinCR.argus_backends.gm.gridmodel.GmMapping;
import org.TwinCR.argus_backends.gm.telemetry.TelemetryConsumer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class Main {
    private static final Logger LOGGER = LoggerFactory.getLogger(Main.class);

    public static void main(String[] args) throws Exception {
        // Parse CLI arguments using picocli
        Config config = new Config();
        int exitCode = new CommandLine(config).execute(args);
        if (exitCode != 0) {
            System.exit(exitCode);
        }

        String appName = "backend_GM";

        // Connect to NATS (patterns publish/subscribe and request/reply per NATS Java docs)
        Connection conn = NatsConnectionFactory.connect(config, appName);

        // Load case
        Instant start = Instant.now();
        Path gridModelPath = config.gridModelPath();
        Path tiMappedPath = config.tiMappingPath();
        Optional<Path> geoDataPath = config.geoDataPath();
        GridModel.load(gridModelPath, tiMappedPath, geoDataPath);
        Instant end = Instant.now();
        long duration = Duration.between(start, end).toMillis();
        LOGGER.info("Grid case loaded {} in {} ms", GridModel.network.getNameOrId(), duration);

        // Load mappinngs
        start = Instant.now();
        Path gmMappedPath = config.gmMappingPath();
        GmMapping.load(gmMappedPath);
        end = Instant.now();
        duration = Duration.between(start, end).toMillis();
        LOGGER.info("{} loaded in {} ms", gmMappedPath, duration);

        InformationFlowModelLayout.load(conn, "GameMasterControl.backend_GM", config);

        ControlSender controlSender = new ControlSender(conn, config);

        // Start services
        SseNatsBridge bridge = new SseNatsBridge();
        TelemetryConsumer telemetryConsumer = new TelemetryConsumer(conn, bridge, config);
        new ApiServer(config, bridge, conn, appName, telemetryConsumer, controlSender);
    }
}
