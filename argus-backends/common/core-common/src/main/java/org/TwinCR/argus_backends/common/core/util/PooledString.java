/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.common.core.util;

import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.databind.DeserializationContext;
import com.fasterxml.jackson.databind.JsonDeserializer;

import java.io.IOException;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Function;

// JsonDeserialize annotation for Strings that make identical string share the same instance.
// Usefull to deserialize mapping files that contain many times the same string.
// Call release() once loading is done, the pool itself is only useful while parsing.
public class PooledString extends JsonDeserializer<String> {
    private static final ConcurrentHashMap<String, String> POOL = new ConcurrentHashMap<>();

    @Override
    public String deserialize(JsonParser parser, DeserializationContext context) throws IOException {
        String value = parser.getValueAsString();
        return value == null ? null : POOL.computeIfAbsent(value, Function.identity());
    }

    public static void release() {
        POOL.clear();
    }
}
