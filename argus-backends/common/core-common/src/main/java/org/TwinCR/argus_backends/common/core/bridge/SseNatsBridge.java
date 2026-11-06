/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.common.core.bridge;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

public class SseNatsBridge {

    // Keyed by subscription pattern (may contain * or >)
    private final Map<String, Set<SseClient>> topicClients = new ConcurrentHashMap<>();

    public void register(String topic, SseClient client) {
        topicClients
            .computeIfAbsent(topic, k -> ConcurrentHashMap.newKeySet())
            .add(client);
    }

    public void remove(SseClient client) {
        topicClients.values().forEach(set -> set.remove(client));
    }

    public void forward(String subject, byte[] data) {
        // Collect all clients whose subscription pattern matches the incoming subject
        Set<SseClient> matched = new HashSet<>();
        for (Map.Entry<String, Set<SseClient>> entry : topicClients.entrySet()) {
            if (matches(entry.getKey(), subject)) {
                matched.addAll(entry.getValue());
            }
        }
        if (matched.isEmpty()) return;

        // Convert to single-line JSON to avoid SSE breaking
        String payload = new String(data, StandardCharsets.UTF_8)
            .replace("\n", "")
            .replace("\r", "");

        Iterator<SseClient> it = matched.iterator();
        while (it.hasNext()) {
            SseClient client = it.next();
            try {
                client.send(payload);
            } catch (IOException e) {
                // Remove dead clients
                remove(client);
            }
        }
    }

    /**
     * Matches a NATS subject against a subscription pattern.
     *
     * NATS wildcard rules:
     *   *  matches exactly one token  — e.g. "foo.*.bar" matches "foo.x.bar"
     *   >  matches one or more tokens — e.g. "foo.>"  matches "foo.x", "foo.x.y", …
     *      '>' must be the last token in the pattern.
     *
     * @param pattern  subscription pattern (may contain * and >)
     * @param subject  incoming concrete subject (no wildcards)
     */
    static boolean matches(String pattern, String subject) {
        String[] patTokens = pattern.split("\\.");
        String[] subTokens = subject.split("\\.");

        int pi = 0, si = 0;
        while (pi < patTokens.length && si < subTokens.length) {
            String tok = patTokens[pi];
            if (tok.equals(">")) {
                // '>' consumes the rest — valid only as the last pattern token
                return true;
            } else if (tok.equals("*")) {
                // '*' consumes exactly one subject token
                pi++;
                si++;
            } else {
                if (!tok.equals(subTokens[si])) return false;
                pi++;
                si++;
            }
        }

        // Both exhausted simultaneously → exact match (possibly via *)
        return pi == patTokens.length && si == subTokens.length;
    }
}
