/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.common.gridmodel;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Last raw value received for each telemetry id (gm_output / scada_output id, TI libelle, tase2 id).
 * Fed by the telemetry consumers, read by the synoptic diagrams (expression function {@code out("id")}).
 */
public final class LatestValues {
    private static final Map<String, Double> VALUES = new ConcurrentHashMap<>();

    private LatestValues() {}

    public static void put(String id, double value) {
        if (id != null) {
            VALUES.put(id, value);
        }
    }

    // NaN when the id never received a value
    public static double get(String id) {
        Double value = VALUES.get(id);
        return value == null ? Double.NaN : value;
    }
}
