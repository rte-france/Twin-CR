/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/


package org.TwinCR.argus_backends.scada.alarms;

import io.nats.client.Connection;
import io.nats.client.JetStreamManagement;
import io.nats.client.api.RetentionPolicy;
import io.nats.client.api.StorageType;
import io.nats.client.api.StreamConfiguration;

import java.time.Duration;

public class AlarmsStreamInitializer {
    public static void init(Connection conn) throws Exception {
        JetStreamManagement jsm = conn.jetStreamManagement();
        boolean exists = jsm.getStreamNames().contains("ALARMS");
        if (!exists) {
            StreamConfiguration cfg = StreamConfiguration.builder()
                    .name("ALARMS")
                    .subjects("alarms.events")
                    .storageType(StorageType.File)
                    .retentionPolicy(RetentionPolicy.Limits)
                    .maxAge(Duration.ofDays(180))
                    .build();
            jsm.addStream(cfg);
        }
    }
}
