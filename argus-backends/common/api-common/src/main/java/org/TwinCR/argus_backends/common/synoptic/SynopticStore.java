/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.common.synoptic;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

import org.TwinCR.argus_backends.common.core.config.ConfigCommon;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Synoptic definitions of the directory {@code [input_files.argus] synoptics_dir} of the config.toml:
 * {@code index.json} lists the definition files (array of file names relative to the directory). Loaded at startup.
 */
public class SynopticStore {
    private static final Logger LOGGER = LoggerFactory.getLogger(SynopticStore.class);

    private final ConfigCommon config;
    private final ObjectMapper mapper = new ObjectMapper();
    private final Map<String, SynopticRenderer> renderers;

    public SynopticStore(ConfigCommon config) {
        this.config = config;
        this.renderers = load();
    }

    public List<Map<String, String>> list() {
        List<Map<String, String>> result = new ArrayList<>();
        renderers.forEach((name, r) -> result.add(Map.of("name", name, "title", r.title())));
        return result;
    }

    public SynopticRenderer get(String name) {
        return renderers.get(name);
    }

    private Map<String, SynopticRenderer> load() {
        Map<String, SynopticRenderer> loaded = new LinkedHashMap<>();
        String dir = config.synopticsDir().orElse(null);
        if (dir == null) {
            return loaded;
        }
        String prefix = dir.endsWith("/") ? dir : dir + "/";
        JsonNode index;
        try {
            index = mapper.readTree(config.resolveInputFile(prefix + "index.json").toFile());
        } catch (Exception e) {
            LOGGER.error("Cannot read synoptics index {}index.json: {}", prefix, e.getMessage());
            return loaded;
        }
        for (JsonNode n : index) {
            String file = n.asText();
            try {
                JsonNode def = mapper.readTree(config.resolveInputFile(prefix + file).toFile());
                if (!def.has("name")) {
                    // Use filename if no name specified for the synoptic
                    ((ObjectNode) def).put("name", file.replaceFirst("\\.json$", ""));
                }
                SynopticRenderer renderer = new SynopticRenderer(def);
                loaded.put(renderer.name(), renderer);
                LOGGER.info("Loaded synoptic '{}' from {} ({} elements)", renderer.name(), file, def.path("elements").size());
            } catch (Exception e) {
                LOGGER.error("Cannot load synoptic {}{}: {}", prefix, file, e.getMessage());
            }
        }
        return loaded;
    }
}
