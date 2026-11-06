/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/


package org.TwinCR.argus_backends.scada.alarms;

public class AlarmRule {
    public String tag;
    public double threshold;
    public boolean high; // true: trigger when value > threshold, false: value < threshold
    public double hysteresis = 0.0; // optional
    public String severity = "MAJOR"; // INFO, MINOR, MAJOR, CRITICAL
    public boolean enabled = true;

    public AlarmRule() {}
    public AlarmRule(String tag, double threshold, boolean high) {
        this.tag = tag; this.threshold = threshold; this.high = high;
    }

    public boolean isTriggered(double v) {
        return high ? v > threshold : v < threshold;
    }
    public boolean isCleared(double v) {
        if (hysteresis <= 0) return !isTriggered(v);
        double clearTh = high ? (threshold - hysteresis) : (threshold + hysteresis);
        return high ? v < clearTh : v > clearTh;
    }
}
