/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.common.datamodel;

import java.io.IOException;

import com.fasterxml.jackson.core.JsonGenerator;
import com.fasterxml.jackson.databind.JsonSerializer;
import com.fasterxml.jackson.databind.SerializerProvider;

public class ValueSerializer extends JsonSerializer<Value> {
    @Override
    public void serialize(Value value, JsonGenerator gen, SerializerProvider serializers) throws IOException {
        switch (value) {
            case Value.BoolValue b -> gen.writeBoolean(b.value());
            case Value.IntValue i -> gen.writeNumber(i.value());
            case Value.DoubleValue d -> gen.writeNumber(d.value());
        }
    }
}
