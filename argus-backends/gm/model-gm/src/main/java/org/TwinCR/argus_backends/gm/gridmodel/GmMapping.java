/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.gm.gridmodel;

import com.fasterxml.jackson.databind.MappingIterator;
import com.fasterxml.jackson.databind.ObjectMapper;

import org.TwinCR.argus_backends.common.gridmodel.GridModel;

import org.TwinCR.argus_backends.common.core.util.FileLoader;
import org.TwinCR.argus_backends.common.core.util.PooledString;

import java.io.IOException;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

public class GmMapping {
    private static final ObjectMapper MAPPER = new ObjectMapper();

    public static Map<String, GmOutput> id_2_gmOutput = new HashMap<>();
    private static String jsonString;

    public static void load(Path name) {
        // Load an eventually compressed game_master_outputs.json
        jsonString = FileLoader.load(name);

        try (MappingIterator<GmOutput> iterator = MAPPER.readerFor(GmOutput.class).readValues(jsonString)) {
            while (iterator.hasNext()) {
                GmOutput output = iterator.next();
                if (output.id() == null) {
                    continue;
                }
                if (GridModel.isSplitTransformer(output.equipmentId())) {
                    // The GridModel has this transformer as a 3-windings one, but Dynawo publish the data as 3 separate 2-windings ones,
                    // so map each of the 3 transformer to one leg.
                    Optional<GridModel.ThreeWindingsLeg> leg = GridModel.mergedLeg(output.equipmentId(), output.voltageLevel());
                    if (leg.isEmpty()) {
                        // Drop the side that faced the fake bus as it no longer exists in the merged transformer (Dynawo has 3 transformers with 2 sides,
                        // but we only have one transformer with 3 sides)
                        continue;
                    }
                    output = new GmOutput(output.id(), leg.get().transformerId(), output.kind(), leg.get().side(), output.voltageLevel(), output.topic());
                }
                id_2_gmOutput.put(output.id(), output);
            }
        } catch (IOException e) {
            throw new RuntimeException("Failed to parse JSON mapping file " + name, e);
        } finally {
            PooledString.release();
        }
    }

    // The front-end wants the mapping file verbatim.
    public static String getJson() {
        if (jsonString == null) {
            throw new IllegalStateException("Mapping JSON not loaded yet");
        }
        return jsonString;
    }
}
