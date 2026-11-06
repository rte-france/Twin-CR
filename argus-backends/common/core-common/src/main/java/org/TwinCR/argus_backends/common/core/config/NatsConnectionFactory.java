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

import java.time.Duration;

public class NatsConnectionFactory {
    public static Connection connect(ConfigCommon config, String appName) throws Exception {
        Options opts = new Options.Builder()
                .server(config.natsUrl())
                .connectionName(appName)
                .reconnectWait(Duration.ofMillis(500))
                .maxReconnects(-1)
                .build();
        return Nats.connect(opts);
    }
}
