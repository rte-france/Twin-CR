/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/


package org.TwinCR.argus_backends.scada.alarms;

import java.util.UUID;

public class AlarmEvent {
    public String id = UUID.randomUUID().toString();
    public String tag;
    public double value;
    public String severity;
    public String state; // ACTIVE, CLEARED
    public long tsActive;
    public Long tsCleared; // nullable
    public boolean acked;

    public AlarmEvent() {}
    public AlarmEvent(String tag, double value, String severity, String state) {
        this.tag = tag; this.value = value; this.severity = severity; this.state = state;
        this.tsActive = System.currentTimeMillis();
    }
}
