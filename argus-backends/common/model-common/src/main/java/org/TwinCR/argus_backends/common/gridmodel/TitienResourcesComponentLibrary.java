/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.common.gridmodel;

import com.powsybl.sld.library.SldResourcesComponentLibrary;

public class TitienResourcesComponentLibrary extends SldResourcesComponentLibrary {
    public static final String NAME = "TitienComponentLibrary";

    public TitienResourcesComponentLibrary() {
        // ConvergenceLibrairy + few additional rules
        super(NAME, "/ConvergenceLibrary", "/tit-component");
    }
}
