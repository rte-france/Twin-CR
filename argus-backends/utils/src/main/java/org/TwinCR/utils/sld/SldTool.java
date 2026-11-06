/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.utils.sld;

import com.google.auto.service.AutoService;
import com.google.common.base.Supplier;
import com.google.common.base.Suppliers;
import com.powsybl.commons.PowsyblException;
import com.powsybl.commons.datasource.DataSource;
import com.powsybl.commons.datasource.DataSourceObserver;
import com.powsybl.commons.datasource.DataSourceUtil;
import com.powsybl.iidm.network.*;
import com.powsybl.iidm.network.tools.ConversionToolUtils;
import com.powsybl.nad.NetworkAreaDiagram;
import com.powsybl.sld.SingleLineDiagram;
import com.powsybl.tools.Command;
import com.powsybl.tools.Tool;
import com.powsybl.tools.ToolRunningContext;
import org.apache.commons.cli.CommandLine;
import org.apache.commons.cli.Option;
import org.apache.commons.cli.Options;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import java.util.Objects;
import java.util.Properties;

import static com.powsybl.iidm.network.tools.ConversionToolUtils.*;


/**
 * @author Olivier Bretteville <olivier.bretteville at rte-france.com>
 */
@AutoService(Tool.class)
public class SldTool implements Tool {

    private static final Logger LOGGER = LoggerFactory.getLogger(SldTool.class);

    private static final String INPUT_FILE = "input-file";
    private static final String OUTPUT_DIR = "output-dir";
    private static final String SUBSTATIONS = "substations";
    private static final String AREA = "area";
    private static final String DEPTH = "depth";

    protected ImportConfig createImportConfig() {
        return ImportConfig.load();
    }

    @Override
    public Command getCommand() {
        return new Command() {

            @Override
            public String getName() {
                return "sld";
            }

            @Override
            public String getTheme() {
                return "Visualisation";
            }

            @Override
            public String getDescription() {
                return "Build substation's SVG";
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
                options.addOption(Option.builder().longOpt(OUTPUT_DIR)
                        .desc("the output dir")
                        .hasArg()
                        .argName("OUTPUT_DIR")
                        .build());
                options.addOption(Option.builder().longOpt(AREA)
                        .desc("generate an area image, not individual substations images")
                        .build());
                options.addOption(Option.builder().longOpt(DEPTH)
                        .desc("depth for network area")
                        .hasArg()
                        .argName("DEPTH")
                        .build());
                Option option = new Option("s", "substations to draw");
                option.setArgs(Option.UNLIMITED_VALUES);
                option.setArgName("SUBSTATIONS");
                option.setLongOpt(SUBSTATIONS);
                option.hasArgs();
                options.addOption(option);
                options.addOption(createImportParametersFileOption());
                options.addOption(createImportParameterOption());

                return options;
            }

            @Override
            public String getUsageFooter() {
                return "Where OUTPUT_FORMAT is ?";
            }
        };
    }


    public void run(CommandLine line, ToolRunningContext context) throws Exception {
        String inputFile = line.getOptionValue(INPUT_FILE);
        String outputFile = line.getOptionValue(OUTPUT_DIR);

        Properties inputParams = readProperties(line, ConversionToolUtils.OptionType.IMPORT, context);
        inputParams.put("iidm.die.transform-low-voltage-capacitors", "false");
        LOGGER.info("Properties used to load case:");
        inputParams.forEach((k, v) -> LOGGER.info("\t{}: {}", k, v));
        Network network = Network.read(Paths.get(inputFile));

        boolean area = line.hasOption(AREA);
        String[] substations = line.getOptionValues(SUBSTATIONS);

        if (area) {
            int depth = 1;
            if (line.hasOption(DEPTH)) {
                depth = Integer.parseInt(line.getOptionValue(DEPTH));
            }
            // Construction d'une image de zone à partir des postes spécifiés
            NetworkAreaDiagram.draw(network, Path.of("diagramme.svg"), List.of(substations), depth);
        } else {
            // Construction des postes individuels
            for (String substation : substations) {
                LOGGER.info("Handling {}", substation);
                SingleLineDiagram.draw(network, substation, substation + ".svg");
            }
        }
    }
}
