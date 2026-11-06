/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.utils;

import com.google.auto.service.AutoService;
import com.powsybl.iidm.network.*;
import com.powsybl.contingency.violations.LimitViolations;
import com.powsybl.contingency.violations.LimitViolation;
import com.powsybl.security.Security;
import com.powsybl.tools.Command;
import com.powsybl.tools.Tool;
import com.powsybl.tools.ToolRunningContext;
import org.apache.commons.cli.CommandLine;
import org.apache.commons.cli.Option;
import org.apache.commons.cli.Options;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.nio.file.Paths;
import java.util.List;
import java.util.Properties;

import static com.powsybl.iidm.network.tools.ConversionToolUtils.*;

/**
 *
 * @author Olivier Bretteville <olivier.bretteville at rte-france.com>
 */
@AutoService(Tool.class)
public class CaseCheckTool implements Tool {

    private static final Logger LOGGER = LoggerFactory.getLogger(CaseCheckTool.class);
    private static final String INPUT_FILE = "input-file";

    protected ImportConfig createImportConfig() {
        return ImportConfig.load();
    }

    @Override
    public Command getCommand() {
        return new Command() {

            @Override
            public String getName() {
                return "casecheck";
            }

            @Override
            public String getTheme() {
                return "Data preprocessing and case conversion";
            }

            @Override
            public String getDescription() {
                return "Check case consistency on 'some aspects'";
            }

            @Override
            public Options getOptions() {
                Options options = new Options();
                options.addOption(Option.builder().longOpt(INPUT_FILE)
                        .desc("the input file")
                        .hasArg()
                        .argName("INPUT_FILE")
                        .required()
                        .build());
                options.addOption(createImportParametersFileOption());
                options.addOption(createImportParameterOption());

                return options;
            }

            @Override
            public String getUsageFooter() {
                return null;
            }
        };
    }

    public void process(Network network) throws IOException {
        List<LimitViolation> violations = Security.checkLimits(network);
        for (LimitViolation violation: violations) {
            System.out.println(violation.toString());
        }
    }

    @Override
    public void run(CommandLine line, ToolRunningContext context) throws Exception {
        String inputFile = line.getOptionValue(INPUT_FILE);

        Properties inputParams = readProperties(line, OptionType.IMPORT, context);
        LOGGER.info("Properties used to load case:");
        inputParams.forEach((k, v) -> LOGGER.info("\t{}: {}", k, v));
        Network network = Network.read(Paths.get(inputFile));

        process(network);
    }
}
