/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.utils.estim;

import com.powsybl.iidm.network.Network;

import java.io.IOException;

/**
 * State estimator run against a network in place (bus V/angle, terminal P/Q, ... are updated on the network itself).
 * Implementations are discovered at runtime via {@link StateEstimationProviders}, so that the SCADA module can run
 * without a state estimation implementation on the classpath (e.g. builds without the private powsybl-rte jars).
 */
public interface StateEstimationProvider {
    void runEstim(Network network) throws IOException, InterruptedException;
}
