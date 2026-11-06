/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/


package org.TwinCR.argus_backends.scada.commands;

import io.nats.client.Connection;
import io.nats.client.Dispatcher;

public class CommandRequestHandler {
    public void start(Connection conn) {
        Dispatcher d = conn.createDispatcher(msg -> {
            String subject = msg.getSubject();
            // TODO: appeler le driver PLC/edge réel ici
            String response = "{\"status\":\"OK\", \"subject\":\"" + subject + "\"}";
            conn.publish(msg.getReplyTo(), response.getBytes());
        });
        d.subscribe("command.*");
    }
}
