/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.utils.estim;

import java.util.Optional;
import java.util.ServiceLoader;

public final class StateEstimationProviders {

    public static Optional<StateEstimationProvider> findProvider() {
        return ServiceLoader.load(StateEstimationProvider.class).findFirst();
    }

    private StateEstimationProviders() { }
}
