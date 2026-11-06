/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/


package org.TwinCR.argus_backends.scada.commands;

import io.nats.client.Connection;
import io.nats.client.Message;

import java.time.Duration;

public class CommandSender {
    private final Connection conn;
    public CommandSender(Connection conn) { this.conn = conn; }

    public String send(String deviceId, String jsonCommand) throws Exception {
        Message reply = conn.request("command." + deviceId, jsonCommand.getBytes(), Duration.ofSeconds(2));
        return new String(reply.getData());
    }
}
