/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.common.core.config;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

public class ConfiguratorClient {
    private static final Logger LOGGER = LoggerFactory.getLogger(ConfiguratorClient.class);
    private final String host;
    private final int port;

    public ConfiguratorClient(String host, int port) {
        this.host = host;
        this.port = port;
    }

    public String getSimulationId() {
        waitUntilReady();

        try {
            var url = new java.net.URI("http://" + host + ":" + port + "/simulation_id");

            var request = java.net.http.HttpRequest.newBuilder(url).header("accept", "application/json").GET().build();
            var client = java.net.http.HttpClient.newHttpClient();
            var response = client.send(request, java.net.http.HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() != 200) {
                throw new IllegalStateException("Configurator error");
            }

            ObjectMapper mapper = new ObjectMapper();
            JsonNode node = mapper.readTree(response.body());
            return node.path("simulation_id").asText();

        } catch (Exception e) {
            throw new IllegalStateException("Failed to get simulation_id", e);
        }
    }

    public String getConfigPath() {
        waitUntilReady();

        try {
            var url = new java.net.URI("http://" + host + ":" + port + "/config_path");

            var request = java.net.http.HttpRequest.newBuilder(url).header("accept", "application/json").GET().build();
            var client = java.net.http.HttpClient.newHttpClient();
            var response = client.send(request, java.net.http.HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() != 200) {
                throw new IllegalStateException("Configurator error");
            }

            ObjectMapper mapper = new ObjectMapper();
            JsonNode node = mapper.readTree(response.body());
            return node.path("config_path").asText();

        } catch (Exception e) {
            throw new IllegalStateException("Failed to get config_path", e);
        }
    }

    private void waitUntilReady() {
        ObjectMapper mapper = new ObjectMapper();
        while (true) {
            try {
                var url = new java.net.URI("http://" + host + ":" + port + "/status");

                var request = java.net.http.HttpRequest.newBuilder(url).header("accept", "application/json").GET().build();
                var client = java.net.http.HttpClient.newHttpClient();
                var response = client.send(request, java.net.http.HttpResponse.BodyHandlers.ofString());

                JsonNode node = mapper.readTree(response.body());
                if (!"NOT READY".equals(node.path("status").asText())) {
                    break;
                }

                LOGGER.info("Waiting for configurator: {}", node);
                Thread.sleep(1000);

            } catch (Exception ignored) {
                try { Thread.sleep(1000); } catch (InterruptedException ignored2) {}
            }
        }
    }
}
