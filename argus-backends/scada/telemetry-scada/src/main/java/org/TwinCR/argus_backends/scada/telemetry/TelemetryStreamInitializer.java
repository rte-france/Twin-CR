/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.scada.telemetry;

import io.nats.client.Connection;
import io.nats.client.JetStreamManagement;
import io.nats.client.api.RetentionPolicy;
import io.nats.client.api.StorageType;
import io.nats.client.api.StreamConfiguration;

import java.time.Duration;

public class TelemetryStreamInitializer {
    public static void init(Connection conn) throws Exception {
        JetStreamManagement jsm = conn.jetStreamManagement();
        System.out.println(jsm.getStreamNames().toString());

        // On supprime le stream
        try {
            jsm.deleteStream("TELEMETRY");
        }
        catch (Exception ignore) {}

        boolean exists = jsm.getStreamNames().contains("TELEMETRY");
        if (!exists) {
            StreamConfiguration cfg = StreamConfiguration.builder()
                    .name("TELEMETRY")
                    .subjects("telemetry.*")
                    .storageType(StorageType.File)
                    .retentionPolicy(RetentionPolicy.Limits)
                    .maxAge(Duration.ofDays(30))
                    .build();
            jsm.addStream(cfg);
        }
    }
}
