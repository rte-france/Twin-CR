/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.gm.core.config;
import java.nio.file.Path;

import org.TwinCR.argus_backends.common.core.config.ConfigCommon;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import picocli.CommandLine.Command;

@Command(name = "gm-backend", mixinStandardHelpOptions = true, version = "5.2.0",
        description = "GameMaster Backend for Twin-CR")
public class Config extends ConfigCommon {
    private static final Logger LOGGER = LoggerFactory.getLogger(Config.class);

    @Override
    public Path gridModelPath() {
        try {
            return getPathFromConfig("gm_backend.iidm_file");
        } catch (IllegalStateException e) {
            LOGGER.info("No input_files.gm_backend.iidm_file specified in TOML, using input_files.iidm_file instead");
            return getPathFromConfig("iidm_file");
        }
    }

    public Path gmMappingPath() {
        return getPathFromConfig("game_master_outputs_file");
    }

    public Path gmInputsPath() {
        return getPathFromConfig("game_master_inputs_file");
    }

    @Override
    public void run() {
        super.run();
    }
}
