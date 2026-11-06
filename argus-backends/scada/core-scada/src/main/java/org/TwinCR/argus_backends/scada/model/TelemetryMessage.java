/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/


package org.TwinCR.argus_backends.scada.model;

import org.jspecify.annotations.Nullable;

import org.TwinCR.argus_backends.common.datamodel.Value;
import org.TwinCR.argus_backends.common.datamodel.ValueDeserializer;

import com.fasterxml.jackson.databind.annotation.JsonDeserialize;

public class TelemetryMessage {
    public String id;
    @JsonDeserialize(using = ValueDeserializer.class)
    public Value value;  // Boolean, Integer, or Double
    public double time_sent;
    public double time_received;
    @Nullable
    public Tase2Extension tase2;

    public TelemetryMessage() {}

    public static class Tase2Extension {
        public String tase2_id;
        public int cause;
        public int validity;
        @JsonDeserialize(using = ValueDeserializer.class)
        public Value stVal;  // Nullable, for TS only
        @JsonDeserialize(using = ValueDeserializer.class)
        public Value value;  // Nullable, for TM only
        public boolean operatorBlocked;
        public long ts;
        public String tfos;
    }
}
