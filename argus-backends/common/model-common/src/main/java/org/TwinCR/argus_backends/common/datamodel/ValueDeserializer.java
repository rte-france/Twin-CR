/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.common.datamodel;

import java.io.IOException;

import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.databind.DeserializationContext;
import com.fasterxml.jackson.databind.JsonDeserializer;
import com.fasterxml.jackson.databind.JsonNode;

public class ValueDeserializer extends JsonDeserializer<Value> {
    @Override
    public Value deserialize(JsonParser p, DeserializationContext ctx) throws IOException {
        JsonNode node = p.getCodec().readTree(p);
        if (node.isBoolean()) return new Value.BoolValue(node.booleanValue());
        if (node.isInt())     return new Value.IntValue(node.intValue());
        if (node.isDouble())  return new Value.DoubleValue(node.doubleValue());
        throw new IllegalArgumentException("Unsupported value type: " + node.getNodeType());
    }
}
