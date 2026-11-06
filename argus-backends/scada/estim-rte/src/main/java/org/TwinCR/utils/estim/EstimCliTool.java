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

import com.google.auto.service.AutoService;
import com.powsybl.commons.PowsyblException;
import com.powsybl.iidm.network.Exporter;
import com.powsybl.iidm.network.Network;
import com.powsybl.tools.Command;
import com.powsybl.tools.Tool;
import com.powsybl.tools.ToolRunningContext;
import org.apache.commons.cli.CommandLine;
import org.apache.commons.cli.Option;
import org.apache.commons.cli.Options;
import org.apache.commons.lang3.tuple.Pair;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.nio.file.Paths;
import java.util.Properties;

/**
 * itools "estim" command: runs the RTE proprietary state estimator against a case file from the command line.
 *
 * @author Geoffroy Jamgotchian <geoffroy.jamgotchian at rte-france.com>
 * @author Mathieu Bague <mathieu.bague at rte-france.com>
 * @author Olivier Bretteville <olivier.bretteville at rte-france.com>
 */
@AutoService(Tool.class)
public class EstimCliTool implements Tool {

    private static final Logger LOGGER = LoggerFactory.getLogger(EstimCliTool.class);

    private static final String INPUT_FILE = "input-file";
    private static final String OUTPUT_FILE_BASE = "output-file-base";
    private static final String OUTPUT_FORMAT = "output-format";
    private static final String OUTPUT_CASE_FILE = "output-case-file";
    private static final String OUTPUT_CASE_FORMAT = "output-case-format";
    private static final String COMPARE = "compare";
    private static final String IIDM = "iidm";
    private static final String KEEP_CF = "keep-cf";

    @Override
    public Command getCommand() {
        return new Command() {

            @Override
            public String getName() {
                return "estim";
            }

            @Override
            public String getTheme() {
                return "Computation";
            }

            @Override
            public String getDescription() {
                return "Run state estimation";
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
                options.addOption(Option.builder().longOpt(OUTPUT_FILE_BASE)
                        .desc("the output file prefix")
                        .argName("OUTPUT_FILE_BASE")
                        .hasArg()
                        .build());
                options.addOption(Option.builder().longOpt(OUTPUT_FORMAT)
                        .desc("the output file format")
                        .argName("OUTPUT_FORMAT")
                        .hasArg()
                        .build());
                options.addOption(Option.builder().longOpt(OUTPUT_CASE_FILE)
                        .desc("the output case file")
                        .argName("OUTPUT_CASE_FILE")
                        .hasArg()
                        .build());
                options.addOption(Option.builder().longOpt(OUTPUT_CASE_FORMAT)
                        .desc("the output case file format")
                        .argName("OUTPUT_CASE_FORMAT")
                        .hasArg()
                        .build());
                options.addOption(Option.builder().longOpt(COMPARE)
                        .desc("compare results with those already present in base case")
                        .argName("COMPARE")
                        .build());
                options.addOption(Option.builder().longOpt(IIDM)
                        .desc("read case as IIDM")
                        .argName("IIDM")
                        .build());
                options.addOption(Option.builder().longOpt(KEEP_CF)
                        .desc("don't remove fictitious loads before running estim")
                        .argName("KEEP_CF")
                        .build());

                return options;
            }

            @Override
            public String getUsageFooter() {
                return "Where OUTPUT_FORMAT is ?";
            }
        };
    }

    @Override
    public void run(CommandLine line, ToolRunningContext context) throws Exception {
        String inputFile = line.getOptionValue(INPUT_FILE);
        LOGGER.info("{} is {}", INPUT_FILE, inputFile);
        String outputFile = line.getOptionValue(OUTPUT_FILE_BASE);
        LOGGER.info("{} is {}", OUTPUT_FILE_BASE, outputFile);
        String outputFormat = line.getOptionValue(OUTPUT_FORMAT);
        LOGGER.info("{} is {}", OUTPUT_FORMAT, outputFormat);
        String outputCaseFile = line.getOptionValue(OUTPUT_CASE_FILE);
        LOGGER.info("{} is {}", OUTPUT_CASE_FILE, outputCaseFile);
        String outputCaseFormat = line.getOptionValue(OUTPUT_CASE_FORMAT);
        LOGGER.info("{} is {}", OUTPUT_CASE_FORMAT, outputCaseFormat);
        boolean compare = line.hasOption(COMPARE);
        LOGGER.info("{} is {}", COMPARE, compare);
        boolean keepCF = line.hasOption(KEEP_CF);
        LOGGER.info("{} is {}", KEEP_CF, keepCF);

        Exporter caseExporter = null;
        if (outputCaseFormat != null) {
            caseExporter = Exporter.find(outputCaseFormat);
        }
        if (caseExporter == null && outputCaseFormat != null) {
            throw new PowsyblException("Target format " + outputCaseFormat + " not supported");
        } else {
            LOGGER.info("Exporter found for outputFormat {}: {}", outputCaseFormat, caseExporter);
        }
        Properties outputProperties = null; // readProperties(line, TdbfresToolUtils.OptionType.EXPORT, context);
        Network network = Network.read(Paths.get(inputFile));
        Pair<Integer, Integer> nbCF = EstimTool.loadSynthesis(network);
        if ((nbCF.getLeft() != 0.0 || nbCF.getRight() != 0) && !keepCF) {
            System.out.println("Removing " + nbCF.getLeft() + " fictitious loads and resetting " + nbCF.getRight() + " fictitious buses");
            EstimTool.removeFictitiousLoads(network);
        }
        EstimLauncher.launch(network, false);
        System.out.println("Dumping estimated state as iidm to " + outputCaseFile);
        network.write(outputCaseFormat == null ? "XIIDM" : outputCaseFormat, null, Paths.get(outputCaseFile == null ? "out.enrichi.xiidm" : outputCaseFile));
        EstimTool.loadSynthesis(network);
    }
}
