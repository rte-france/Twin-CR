/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.common.core.ifl;

public class Node {
    public final String id;
    public int degree = 0;
    public double x = Double.NaN;
    public double y = Double.NaN;
    public boolean fixed = false;
    public boolean cycosimNode = false;

    public Node(String id) {
        this.id = id;
    }
}
