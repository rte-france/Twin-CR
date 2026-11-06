/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/


package org.TwinCR.argus_backends.scada.config;
import java.nio.file.Path;

import org.TwinCR.argus_backends.common.core.config.ConfigCommon;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import picocli.CommandLine.Command;
import picocli.CommandLine.Option;

@Command(name = "scada-backend", mixinStandardHelpOptions = true, version = "5.2.0",
        description = "SCADA Backend for Twin-CR")
public class Config extends ConfigCommon {
    private static final Logger LOGGER = LoggerFactory.getLogger(Config.class);

    @Option(names = {"--estim-period"}, description = "Time interval between periodic runs of the state estimator in seconds (default 60)", defaultValue = "60")
    private double estimPeriod;

    @Option(names = {"--stale-measurement-timeout"}, description = "Time in seconds after which a measurement not refreshed is displayed in blue (default 30)", defaultValue = "30")
    private double staleMeasurementTimeout;


    @Override
    public Path gridModelPath() {
        try {
            return getPathFromConfig("scada_backend.iidm_file");
        } catch (IllegalStateException e) {
            LOGGER.warn("No input_file.scada_backend.iidm_file specified in TOML, using input_file.iidm_file instead");
            return getPathFromConfig("iidm_file");
        }
    }

    public double estimPeriod() {
        return estimPeriod;
    }

    public double staleMeasurementTimeout() {
        return staleMeasurementTimeout;
    }

    public Path scadaMappingPath() {
        return getPathFromConfig("scada_outputs_file");
    }

    public Path scadaInputsPath() {
        return getPathFromConfig("scada_inputs_file");
    }

    @Override
    public void run() {
        super.run();
    }
}
