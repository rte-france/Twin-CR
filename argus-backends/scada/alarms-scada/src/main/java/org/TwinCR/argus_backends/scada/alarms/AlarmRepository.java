/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/


package org.TwinCR.argus_backends.scada.alarms;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

public class AlarmRepository {
    private static final Map<String, AlarmEvent> DB = new ConcurrentHashMap<>();

    public static synchronized AlarmEvent upsertActive(String tag, double value, String severity) {
        // one active alarm per tag
        Optional<AlarmEvent> existing = DB.values().stream()
                .filter(a -> a.tag.equals(tag) && "ACTIVE".equals(a.state))
                .findFirst();
        AlarmEvent evt = existing.orElseGet(() -> {
            AlarmEvent e = new AlarmEvent(tag, value, severity, "ACTIVE");
            DB.put(e.id, e);
            return e;
        });
        evt.value = value;
        return evt;
    }

    public static synchronized void clearIfExists(String tag, double value) {
        DB.values().stream()
            .filter(a -> a.tag.equals(tag) && "ACTIVE".equals(a.state))
            .forEach(a -> { a.state = "CLEARED"; a.tsCleared = System.currentTimeMillis(); });
    }

    public static List<AlarmEvent> listAll() { return new ArrayList<>(DB.values()); }

    public static boolean ack(String id) {
        AlarmEvent e = DB.get(id);
        if (e == null) return false;
        e.acked = true; return true;
    }

    public static List<AlarmRule> listRules(List<AlarmRule> rules) {
        return rules.stream().collect(Collectors.toList());
    }
}
