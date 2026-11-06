/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.utils;

import com.google.auto.service.AutoService;
import com.powsybl.tools.Command;
import com.powsybl.tools.Tool;
import com.powsybl.tools.ToolRunningContext;
import com.rte_france.powsybl.die.BinaryDieFile;
import com.rte_france.powsybl.die.XmlDieFile;
import com.rte_france.powsybl.die.database.DieDatabase;
import com.rte_france.powsybl.die.database.DieSituation;
import org.apache.commons.cli.CommandLine;
import org.apache.commons.cli.Option;
import org.apache.commons.cli.Options;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.FileOutputStream;
import java.nio.file.Files;
import java.time.*;
import java.time.format.DateTimeFormatter;

import static com.powsybl.iidm.network.tools.ConversionToolUtils.*;

/**
 *
 * @author Olivier Bretteville <olivier.bretteville at rte-france.com>
 */
@AutoService(Tool.class)
public class Arc2XmlTool implements Tool {

    private static final Logger LOGGER = LoggerFactory.getLogger(Arc2XmlTool.class);
    private static final String INPUT_FILE = "input-file";
    private static final String OUTPUT_FILE = "output-file";

    @Override
    public Command getCommand() {
        return new Command() {

            @Override
            public String getName() {
                return "arc2xml";
            }

            @Override
            public String getTheme() {
                return "Data preprocessing and case conversion";
            }

            @Override
            public String getDescription() {
                return "Convert the given arcade binary network to an arcade xml one";
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
                options.addOption(Option.builder().longOpt(OUTPUT_FILE)
                        .desc("the optional output file")
                        .hasArg()
                        .argName("OUTPUT_FILE")
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

    public static String removeFileExtension(String filename, boolean removeAllExtensions) {
        if (filename == null || filename.isEmpty()) {
            return filename;
        }

        String extPattern = "(?<!^)[.]" + (removeAllExtensions ? ".*" : "[^.]*$");
        return filename.replaceAll(extPattern, "");
    }

    @Override
    public void run(CommandLine line, ToolRunningContext context) throws Exception {
        String inputFile = line.getOptionValue(INPUT_FILE);
        String outputFile = line.getOptionValue(OUTPUT_FILE);

        DieDatabase dd = BinaryDieFile.readDatabase(Files.newInputStream(context.getFileSystem().getPath(inputFile)));
        File f = new File(inputFile);
        int perim = dd.getInt("SCADA", "CAPERIME");

        DieSituation ds = new DieSituation(removeFileExtension(f.getName(), false), perim, 0, 0);
        ds.setCreateur("");
        int[] theDate = dd.getIntArray("SCADA", "CADATEXE");
        int[] theTime = dd.getIntArray("SCADA", "CAHEUREX");
        ZonedDateTime z = ZonedDateTime.of(theDate[2], theDate[1], theDate[0], theTime[0], theTime[1], theTime[2], 0, ZoneId.systemDefault());
        DateTimeFormatter dtf = DateTimeFormatter.ofPattern("dd/MM/yyyy hh:mm:ss");
        String sDate = z.format(dtf);
        ds.setDtCreation(sDate);
        ds.setDate(sDate);
        ds.setDtModif(sDate);
        ds.setEtatPlate(DieSituation.TypeEtatPlate.INCONNU.name());
        ds.setTypeSituation(DieSituation.TypeSituation.ACTIF_REACTIF.name());
        dd.setDieSituation(ds);
        FileOutputStream fos = new FileOutputStream(outputFile);
        new XmlDieFile(true).write(dd, fos);
    }
}
