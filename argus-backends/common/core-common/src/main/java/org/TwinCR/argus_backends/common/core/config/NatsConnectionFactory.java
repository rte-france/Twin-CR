/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.common.core.config;

import io.nats.client.Connection;
import io.nats.client.Nats;
import io.nats.client.Options;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.time.Duration;
import java.time.Instant;

public class NatsConnectionFactory {
    private static final Logger LOGGER = LoggerFactory.getLogger(NatsConnectionFactory.class);

    // The NATS server may not accept connections yet at startup (e.g. started alongside the backend):
    // the first connection is retried for this long, then the backend stops with an error
    private static final Duration CONNECT_RETRY_DURATION = Duration.ofSeconds(60);
    private static final Duration CONNECT_RETRY_WAIT = Duration.ofSeconds(1);

    public static Connection connect(ConfigCommon config, String appName) throws Exception {
        Options opts = new Options.Builder()
            .server(config.natsUrl())
            .connectionName(appName)
            .reconnectWait(Duration.ofMillis(500))
            .maxReconnects(-1)
            .build();

        Instant deadline = Instant.now().plus(CONNECT_RETRY_DURATION);
        for (int attempt = 1; ; attempt++) {
            try {
                return Nats.connect(opts);
            } catch (IOException e) {
                if (Instant.now().isAfter(deadline)) {
                    throw new IOException("Could not connect to NATS at " + config.natsUrl() + " after "
                        + CONNECT_RETRY_DURATION.toSeconds() + " s (" + attempt + " attempts): is the NATS server started?", e);
                }
                LOGGER.info("NATS at {} not reachable yet (attempt {}: {}), retrying", config.natsUrl(), attempt, e.getMessage());
                Thread.sleep(CONNECT_RETRY_WAIT.toMillis());
            }
        }
    }
}
