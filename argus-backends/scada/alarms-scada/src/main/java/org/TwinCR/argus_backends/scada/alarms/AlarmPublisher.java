/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/


package org.TwinCR.argus_backends.scada.alarms;

import org.TwinCR.argus_backends.scada.util.JsonUtil;
import io.nats.client.Connection;

public class AlarmPublisher {
    private final Connection conn;
    public AlarmPublisher(Connection conn) { this.conn = conn; }

    public void publish(AlarmEvent e) throws Exception {
        String json = JsonUtil.toJson(e);
        conn.publish("alarms.events", json.getBytes());
    }
}
