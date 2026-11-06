/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/


package org.TwinCR.argus_backends.scada.util;

import com.fasterxml.jackson.databind.ObjectMapper;

public class JsonUtil {
    private static final ObjectMapper MAPPER = new ObjectMapper();
    public static String toJson(Object o) throws Exception { return MAPPER.writeValueAsString(o); }
    public static <T> T fromJson(byte[] bytes, Class<T> type) throws Exception { return MAPPER.readValue(bytes, type); }
    public static <T> T fromJson(String str, Class<T> type) throws Exception { return MAPPER.readValue(str, type); }
}
