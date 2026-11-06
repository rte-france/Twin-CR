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
import com.powsybl.iidm.network.extensions.Measurement;
import com.powsybl.iidm.network.extensions.Measurements;
import com.powsybl.tools.Command;
import com.powsybl.tools.Tool;
import com.powsybl.tools.ToolRunningContext;
import org.apache.commons.cli.CommandLine;
import org.apache.commons.cli.Option;
import org.apache.commons.cli.Options;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.nio.file.Paths;
import java.util.*;

import static org.ejml.UtilEjml.assertTrue;

/**
 * @author Olivier Bretteville <olivier.bretteville at rte-france.com>
 */
@AutoService(Tool.class)
public class MeasurementTool implements Tool {

    private static final Logger LOGGER = LoggerFactory.getLogger(MeasurementTool.class);

    private static final String INPUT_FILE1 = "input-file1";
    private static final String INPUT_FILE2 = "input-file2";
    private static final String SCOMMON = "show-common";

    public static Map<String, Measurement> libelle2Measurement1 = null;
    public static Map<String, Measurement> libelle2Measurement2 = null;

    @SuppressWarnings("unchecked")
    public static Map<String, Measurement> buildMeasurementsMap(Network network) {
        Map<String, Measurement> result = new HashMap<>();
        for (Connectable obj: network.getConnectables()) {
            if (obj != null) {
                Measurements ms = (Measurements) obj.getExtension(Measurements.class);
                if (ms != null) {
                    for (Measurement m : (Iterable<Measurement>) ms.getMeasurements()) {
                        result.put(m.getId(), m);
                    }
                }
            }
        }
        return result;
    }

    protected ImportConfig createImportConfig() {
        return ImportConfig.load();
    }

    @Override
    public Command getCommand() {
        return new Command() {

            @Override
            public String getName() {
                return "cmpmeas";
            }

            @Override
            public String getTheme() {
                return "Computation";
            }

            @Override
            public String getDescription() {
                return "Compare measurements of two cases";
            }

            @Override
            public Options getOptions() {
                Options options = new Options();
                options.addOption(Option.builder().longOpt(INPUT_FILE1)
                        .desc("the first input file")
                        .argName("INPUT_FILE1")
                        .hasArg()
                        .required()
                        .build());
                options.addOption(Option.builder().longOpt(INPUT_FILE2)
                        .desc("the second input file")
                        .argName("INPUT_FILE2")
                        .hasArg()
                        .required()
                        .build());
                options.addOption(Option.builder().longOpt(SCOMMON)
                        .desc("show common measurements instead off different ones")
                        .argName("SCOMMON")
                        .build());

                return options;
            }

            @Override
            public String getUsageFooter() {
                return "NA";
            }
        };
    }

    public static String toString(Measurement m) {
        return m.getType() + " - " + m.getStandardDeviation() + " - " + m.getSide() + " - " + m.getValue();
    }

    public static boolean equals(Measurement m1, Measurement m2) {
        return m1.getType().equals(m2.getType())
                && m1.getStandardDeviation() == m2.getStandardDeviation()
                && m1.getSide() == m2.getSide()
                && m1.getValue() == m2.getValue()
                && m1.isValid() == m2.isValid();
    }

    private record MeasurementComparison(String id, Measurement m1, Measurement m2, double diffPct) {}

    private static double calculatePct(double v1, double v2) {
        if (Math.abs(v1) < 1e-6) {
            return Math.abs(v2) < 1e-6 ? 0 : 100.0;
        }
        return (Math.abs(v1 - v2) / Math.abs(v1)) * 100.0;
    }

    public static void compare(Network network1, Network network2, boolean showCommon) {
        libelle2Measurement1 = buildMeasurementsMap(network1);
        libelle2Measurement2 = buildMeasurementsMap(network2);

        assertTrue(libelle2Measurement1.keySet().equals(libelle2Measurement2.keySet()));
        LOGGER.info("Comparing {} measurements", libelle2Measurement1.size());
        int same=0, different=0;
        List<MeasurementComparison> results = new ArrayList<>();
        for (Map.Entry<String, Measurement> e1 : libelle2Measurement1.entrySet()) {
            Measurement m1 = e1.getValue();
            Measurement m2 = libelle2Measurement2.get(e1.getKey());

            boolean areEqual = equals(m1, m2);
            if (areEqual) {
                same++;
            } else {
                different++;
            }

            if ((showCommon && areEqual) || (!showCommon && !areEqual)) {
                results.add(new MeasurementComparison(e1.getKey(), m1, m2, calculatePct(m1.getValue(), m2.getValue())));
            }
        }

        results.sort(Comparator.comparingDouble(MeasurementComparison::diffPct).reversed());

        for (MeasurementComparison r : results) {
            if (showCommon) {
                LOGGER.info("Same measurements for {}: {}", r.id(), toString(r.m1()));
            } else {
                LOGGER.info(String.format("Different measurements for %s: %s in network1 and %s in network2 | Écart: %.4f%%", r.id(), toString(r.m1()), toString(r.m2()), r.diffPct()));
            }
        }

        LOGGER.info("{} measurements are the same, {} different", same, different);
    }

    @Override
    public void run(CommandLine line, ToolRunningContext context) throws Exception {
        String inputFile1 = line.getOptionValue(INPUT_FILE1);
        LOGGER.info("{} is {}", INPUT_FILE1, inputFile1);
        String inputFile2 = line.getOptionValue(INPUT_FILE2);
        LOGGER.info("{} is {}", INPUT_FILE2, inputFile2);
        boolean common = line.hasOption(SCOMMON);
        LOGGER.info("{} is {}", SCOMMON, common);

        Network network1 =  Network.read(Paths.get(inputFile1));
        Network network2 =  Network.read(Paths.get(inputFile2));
        compare(network1, network2, common);
    }
}
