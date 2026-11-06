/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/


package org.TwinCR.argus_backends.scada.alarms;

import org.TwinCR.argus_backends.scada.model.TelemetryMessage;

import java.util.ArrayList;
import java.util.List;

public class AlarmEngine {
    private final List<AlarmRule> rules = new ArrayList<>();
    private final AlarmPublisher publisher;

    public AlarmEngine(AlarmPublisher publisher) {
        this.publisher = publisher;
    }

    public void addRule(AlarmRule rule) { rules.add(rule); }
    public List<AlarmRule> getRules() { return rules; }

    public void evaluate(TelemetryMessage t) throws Exception {
        for (AlarmRule r : rules) {
            if (!r.enabled) continue;
            String telemetryTag = "EMPTY";  // TODO: add tag to tase2 data? or make tag optional?
            if (!telemetryTag.equals(r.tag)) continue;

            double valueDouble = t.value.toDouble();
            if (r.isTriggered(valueDouble)) {
                AlarmEvent evt = AlarmRepository.upsertActive(telemetryTag, valueDouble, r.severity);
                publisher.publish(evt);
            } else if (r.isCleared(valueDouble)) {
                AlarmRepository.clearIfExists(telemetryTag, valueDouble);
            }
        }
    }
}
