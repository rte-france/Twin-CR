/*
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
*/

/**
 * Copyright (c) 2016, All partners of the iTesla project (http://www.itesla-project.eu/consortium)
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/.
 */
package org.TwinCR.utils.estim;

import com.powsybl.iidm.network.Bus;
import com.powsybl.iidm.network.Load;
import com.powsybl.iidm.network.LoadType;
import com.powsybl.iidm.network.Network;
import org.apache.commons.lang3.tuple.Pair;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.HashSet;
import java.util.Set;

/**
 * Fictitious load bookkeeping shared by every {@link StateEstimationProvider} implementation. Kept free of any
 * RTE-private dependency so it stays available in public (no private jars) builds.
 *
 * @author Geoffroy Jamgotchian <geoffroy.jamgotchian at rte-france.com>
 * @author Mathieu Bague <mathieu.bague at rte-france.com>
 * @author Olivier Bretteville <olivier.bretteville at rte-france.com>
 */
public final class EstimTool {

    private static final Logger LOGGER = LoggerFactory.getLogger(EstimTool.class);

    public static void removeFictitiousLoads(Network network) {
        int floadCount = 0;
        double floadASum = 0.0, floadRSum = 0.0;
        Set<Load> fictitiousLoads = new HashSet<>();

        for (Load load : network.getLoads()) {
            if (load.getLoadType() == LoadType.FICTITIOUS) {
                floadASum += load.getP0();
                floadRSum += load.getQ0();
                floadCount++;
                fictitiousLoads.add(load);
            }
        }
        for (Load load : fictitiousLoads) {
            load.remove();
        }
        LOGGER.info("Removed {} fictitious loads with a total active power of {} and a total reactive power of {}", floadCount, floadASum, floadRSum);

        int nbBusIF=0;
        double p0sum=0.0, q0sum=0.0;
        for (Bus b : network.getBusBreakerView().getBuses()) {
            if (b.isFictitious()) {
                nbBusIF++;
                p0sum += b.getFictitiousP0();
                b.setFictitiousP0(0.0);
                q0sum += b.getFictitiousQ0();
                b.setFictitiousQ0(0.0);
            }
        }
        LOGGER.info("Removed {} fictitious buses with a total active power of {} and a total reactive power of {}", nbBusIF, p0sum, q0sum);
    }

    public static Pair<Integer, Integer> loadSynthesis(Network network) {
        int loadCount = 0;
        double loadASum = 0.0, loadRSum = 0.0;
        int floadCount = 0;
        double floadASum = 0.0, floadRSum = 0.0;

        for (Load load : network.getLoads()) {
            loadASum += load.getP0();
            loadRSum += load.getQ0();
            loadCount++;
            if (load.getLoadType() == LoadType.FICTITIOUS) {
                floadCount++;
                floadASum += load.getP0();
                floadRSum += load.getQ0();
            }
        }

        double p0sum=0.0, q0sum=0.0;
        int nbBusIF=0, nbBusIM=0;
        for (Bus b : network.getBusBreakerView().getBuses()) {
            double p0 = b.getFictitiousP0();
            double q0 = b.getFictitiousQ0();
            if (p0 != 0.0 || q0 != 0.0) {
                if (b.isInMainConnectedComponent())
                    nbBusIM++;
                assert(b.isFictitious());
                p0sum += p0;
                q0sum += q0;
                nbBusIF++;
            } else {
                assert(!b.isFictitious());
            }
        }
        LOGGER.info("Loaded {} loads with a total active power of {} and a total reactive power of {}", loadCount, loadASum, loadRSum);
        LOGGER.info("Loaded {} fictitious loads with a total active power of {} and a total reactive power of {}", floadCount, floadASum, floadRSum);
        LOGGER.info("{} Buses ({} in main connected component) with a total active power of {} and a total reactive power of {} fictitious injections", nbBusIF, nbBusIM, p0sum, q0sum);

        return Pair.of(floadCount, nbBusIF);
    }

    private EstimTool() { }
}
