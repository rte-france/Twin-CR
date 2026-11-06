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
package org.TwinCR.utils;

import com.google.auto.service.AutoService;
import com.powsybl.iidm.network.*;
import com.powsybl.tools.Command;
import com.powsybl.tools.Tool;
import com.powsybl.tools.ToolRunningContext;
import org.apache.commons.cli.CommandLine;
import org.apache.commons.cli.Option;
import org.apache.commons.cli.Options;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.nio.file.Paths;

/**
 * @author Olivier Bretteville <olivier.bretteville at rte-france.com>
 */
@AutoService(Tool.class)
public class InjectionTool implements Tool {

    private static final Logger LOGGER = LoggerFactory.getLogger(InjectionTool.class);

    private static final String INPUT_FILE = "input-file";

    protected ImportConfig createImportConfig() {
        return ImportConfig.load();
    }

    @Override
    public Command getCommand() {
        return new Command() {

            @Override
            public String getName() {
                return "showinjs";
            }

            @Override
            public String getTheme() {
                return "Computation";
            }

            @Override
            public String getDescription() {
                return "Show synthetic injection information";
            }

            @Override
            public Options getOptions() {
                Options options = new Options();
                options.addOption(Option.builder().longOpt(INPUT_FILE)
                        .desc("the input file")
                        .argName("INPUT_FILE")
                        .hasArg()
                        .required()
                        .build());

                return options;
            }

            @Override
            public String getUsageFooter() {
                return "NA";
            }
        };
    }

    public static int loadSynthesis(Network network) {
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

        double pGenSum = 0.0, qGenSum = 0.0;
        int nbGen = 0;
        for (Generator gen : network.getGenerators()) {
            pGenSum += gen.getTargetP();
            qGenSum += gen.getTargetQ();
            nbGen++;
        }
        LOGGER.info("Loaded {} loads with a total active power of {} and a total reactive power of {}", loadCount, loadASum, loadRSum);
        LOGGER.info("Loaded {} fictitious loads with a total active power of {} and a total reactive power of {}", floadCount, floadASum, floadRSum);
        LOGGER.info("{} Buses ({} in main connected component) with a total active power of {} and a total reactive power of {} fictitious injections", nbBusIF, nbBusIM, p0sum, q0sum);
        LOGGER.info("Loaded {} generators with a total active power of {} and a total reactive power of {}", nbGen, pGenSum, qGenSum);
        LOGGER.info("PSum: {}, QSum: {}", pGenSum-loadASum-p0sum, qGenSum-loadRSum-q0sum);
        return floadCount;
    }

    @Override
    public void run(CommandLine line, ToolRunningContext context) throws Exception {
        String inputFile = line.getOptionValue(INPUT_FILE);
        LOGGER.info("{} is {}", INPUT_FILE, inputFile);

        Network network =  Network.read(Paths.get(inputFile));
        int nbCF = loadSynthesis(network);
    }
}
