/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.scada.gridmodel;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.MappingIterator;
import com.fasterxml.jackson.databind.ObjectMapper;

import org.TwinCR.argus_backends.common.core.util.FileLoader;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Path;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

// The outputs the asset simulator publishes rather than Dynawo.
public final class AssetOutputs {
    private static final String ASSET_SIMULATOR = "asset_simulator";
    private static final Logger LOGGER = LoggerFactory.getLogger(AssetOutputs.class);
    private static final ObjectMapper MAPPER = new ObjectMapper();

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Output(
        @JsonProperty("id") String id,
        @JsonProperty("equipmentId") String equipmentId,
        @JsonProperty("kind") String kind,
        @JsonProperty("side") String side,
        @JsonProperty("simulator") String simulator) {
    }

    private static Map<String, Output> byId = Map.of();

    private AssetOutputs() {
    }

    public static void load(Path scadaOutputsPath) {
        Map<String, Output> outputs = new HashMap<>();
        try (InputStream in = FileLoader.open(scadaOutputsPath);
             MappingIterator<Output> iterator = MAPPER.readerFor(Output.class).readValues(in)) {
            while (iterator.hasNext()) {
                Output output = iterator.next();
                if (ASSET_SIMULATOR.equals(output.simulator()) && output.id() != null && output.equipmentId() != null) {
                    outputs.put(output.id(), output);
                }
            }
        } catch (IOException e) {
            throw new RuntimeException("Failed to parse " + scadaOutputsPath, e);
        }
        byId = Collections.unmodifiableMap(outputs);
        LOGGER.info("{} asset simulator outputs loaded from {}", byId.size(), scadaOutputsPath);
    }

    public static Output get(String id) {
        return byId.get(id);
    }
}
