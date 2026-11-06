/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.common.datamodel;

import com.fasterxml.jackson.databind.annotation.JsonDeserialize;
import com.fasterxml.jackson.databind.annotation.JsonSerialize;

@JsonSerialize(using = ValueSerializer.class)
@JsonDeserialize(using = ValueDeserializer.class)
public sealed interface Value permits Value.BoolValue, Value.IntValue, Value.DoubleValue {
    record BoolValue(boolean value) implements Value {
        @Override
        public String toString() {
            return Boolean.toString(value);
        }
    }
    record IntValue(int value) implements Value {
        @Override
        public String toString() {
            return Integer.toString(value);
        }
    }
    record DoubleValue(double value) implements Value {
        @Override
        public String toString() {
            return Double.toString(value);
        }
    }

    default double toDouble() {
        return switch (this) {
            case BoolValue b   -> b.value() ? 1.0 : 0.0;
            case IntValue i    -> (double) i.value();
            case DoubleValue d -> d.value();
        };
    }

    static Value parse(String s) {
        if ("true".equalsIgnoreCase(s) || "false".equalsIgnoreCase(s)) {
            return new BoolValue(Boolean.parseBoolean(s));
        }
        try {
            return new IntValue(Integer.parseInt(s));
        } catch (NumberFormatException e) {
            // not an int, fall through to double
        }
        try {
            return new DoubleValue(Double.parseDouble(s));
        } catch (NumberFormatException e) {
            return null;
        }
    }
}
