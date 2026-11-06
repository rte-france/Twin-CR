/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.common.api;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Base64;
import java.util.List;
import java.util.Optional;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

import io.nats.client.Connection;
import io.nats.client.Message;

public class ClickhouseClient {
    private final Connection conn;
    private final HttpClient httpClient;
    private final ObjectMapper mapper = new ObjectMapper();

    private final String clickhouseUrl;
    private final String clickhouseUsername;
    private final String clickhousePassword;
    private final String appName;

    private String simulationName = null;

    public ClickhouseClient(Connection conn, String appName) {
        this.conn = conn;
        this.httpClient = HttpClient.newHttpClient();
        this.appName = appName;

        String host = getEnvOrDefault("CLICKHOUSE_HOST", "localhost");
        String port = getEnvOrDefault("CLICKHOUSE_PORT", "8123");

        this.clickhouseUrl = "http://" + host + ":" + port + "/";
        this.clickhouseUsername = getEnvOrDefault("CLICKHOUSE_USERNAME", "");
        this.clickhousePassword = getEnvOrDefault("CLICKHOUSE_PASSWORD", "");
    }

    private String getSimulationName() {
        if (simulationName != null) {
            return simulationName;
        }
        while (true) {
            try {
                simulationName = fetchSimulationName();
                return simulationName;
            } catch (Exception e) {
                try {
                    Thread.sleep(1000); // 1 second backoff
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    return null; // exit cleanly if interrupted
                }
            }
        }
    }

    private void sqlProtection(String s) {
        // Basic SQL injection protection
        if (!s.matches("[A-Za-z0-9_.]+")) {
            throw new IllegalArgumentException("Invalid topic");
        }
    }

    private String performClickhouseRequest(String query) throws IOException, InterruptedException {
        HttpRequest.Builder builder = HttpRequest.newBuilder()
            .uri(URI.create(clickhouseUrl))
            .timeout(Duration.ofSeconds(10))
            .header("Content-Type", "text/plain; charset=UTF-8")
            .POST(HttpRequest.BodyPublishers.ofString(query));

        if (!clickhouseUsername.isEmpty()) {
            String auth = clickhouseUsername + ":" + clickhousePassword;
            String encoded = Base64.getEncoder().encodeToString(auth.getBytes(StandardCharsets.UTF_8));
            builder.header("Authorization", "Basic " + encoded);
        }

        HttpResponse<String> response = httpClient.send(builder.build(), HttpResponse.BodyHandlers.ofString());

        if (response.statusCode() != 200) {
            throw new RuntimeException("ClickHouse query failed: " + response.body());
        }

        JsonNode root = mapper.readTree(response.body());
        return mapper.writeValueAsString(root.get("data"));
    }

    private String buildFullTableName(String tableName) {
        String simName = getSimulationName();
        return "`" + simName + "`.`" + tableName + "`";
    }

    public String queryHistory(Optional<String> topic, double minTime, double maxTime) throws IOException, InterruptedException {
        if (topic.isPresent()) {
            sqlProtection(topic.get());
        }

        String tableName;
        String timeField;
        if (appName.equals("backend_GM")) {
            tableName = "ActualMeasurement";
            timeField = "time";
        } else if (appName.equals("backend_SCADA")) {
            tableName = "MeasurementReceived";
            timeField = "time_received";
        } else {
            throw new IllegalArgumentException("appName should be backend_GM or backend_SCADA");
        }
        String fullTableName = buildFullTableName(tableName);

        String query =
            "SELECT id, value, " + timeField + " FROM " + fullTableName + " " +
            "WHERE ";
        if (topic.isPresent()) {
            query +=
                "topic='" + topic.get() + "' AND ";
        }
        query +=
            timeField + " >= " + minTime + " AND " +
            timeField + " < " + maxTime + " " +
            "ORDER BY " + timeField + " FORMAT JSON";

        return performClickhouseRequest(query);
    }

    public String queryLatestActualMeasurements(Optional<String> topic) throws IOException, InterruptedException {
        if (topic.isPresent()) {
            sqlProtection(topic.get());
        }

        if (!appName.equals("backend_GM")) {
            throw new IllegalArgumentException("Only backend_GM can fetch ActualMeasurement");
        }
        String fullTableName = buildFullTableName("Latest_ActualMeasurement");

        String query =
                "SELECT id, value, time FROM " + fullTableName + " FINAL ";
        if (topic.isPresent()) {
            query += "WHERE topic='" + topic.get() + "' ";
        }
        query += "FORMAT JSON";

        return performClickhouseRequest(query);
    }

    public String queryDynawoConstraints(double minTime, double maxTime) throws IOException, InterruptedException {
        String fullTableName = buildFullTableName("DynawoConstraintEvent");

        String query =
                "SELECT description, modelName, time, eventType FROM " + fullTableName + " " +
                "WHERE time >= " + minTime + " " +
                "AND time < " + maxTime + " " +
                "ORDER BY time FORMAT JSON";

        return performClickhouseRequest(query);
    }

    public String queryDynawoTimeline(double minTime, double maxTime) throws IOException, InterruptedException {
        String fullTableName = buildFullTableName("DynawoTimelineEvent");

        String query =
                "SELECT time, modelName, message FROM " + fullTableName + " " +
                "WHERE time >= " + minTime + " " +
                "AND time < " + maxTime + " " +
                "ORDER BY time FORMAT JSON";

        return performClickhouseRequest(query);
    }

    public String queryScadaCommands(double minTime, double maxTime) throws IOException, InterruptedException {
        String fullTableName = buildFullTableName("SCADACommand");

        String query =
                "SELECT time, command, command_source FROM " + fullTableName + " " +
                "WHERE time >= " + minTime + " " +
                "AND time < " + maxTime + " " +
                "ORDER BY time FORMAT JSON";

        return performClickhouseRequest(query);
    }

    public String queryGmCommands(double minTime, double maxTime) throws IOException, InterruptedException {
        String fullTableName = buildFullTableName("GameMasterCommand");

        String query =
                "SELECT time, command, command_source FROM " + fullTableName + " " +
                "WHERE time >= " + minTime + " " +
                "AND time < " + maxTime + " " +
                "ORDER BY time FORMAT JSON";

        return performClickhouseRequest(query);
    }

    private String fetchSimulationName() throws Exception {
        ObjectNode request = mapper.createObjectNode();
        request.put("command", "get_simulation_name");

        Message response = conn.request(
                "GameMasterControl." + appName,
                mapper.writeValueAsBytes(request),
                Duration.ofSeconds(2)
        );

        if (response == null) {
            throw new RuntimeException("No response from Orchestrator");
        }

        JsonNode node = mapper.readTree(response.getData());
        if (!"OK".equals(node.get("status").asText())) {
            throw new RuntimeException("Simulation name request failed");
        }

        return node.get("reply").asText();
    }

    private static String getEnvOrDefault(String key, String defaultValue) {
        String value = System.getenv(key);
        return value != null ? value : defaultValue;
    }

    public void createEstimatedValuesTableIfNotExists() throws IOException, InterruptedException {
        String fullTableName = buildFullTableName("EstimatedValues");
        String query =
            "CREATE TABLE IF NOT EXISTS " + fullTableName + " (" +
            "    equipmentId String," +
            "    kind        String," +
            "    side        Nullable(String)," +
            "    value       Float64," +
            "    time        Float64," +
            "    topic       String" +
            ") ENGINE = MergeTree()" +
            " ORDER BY time";
        performClickhouseRequest(query);
    }

    public void insertEstimatedValues(List<EstimatedValue> rows) throws IOException, InterruptedException {
        if (rows.isEmpty()) return;
        createEstimatedValuesTableIfNotExists();

        String fullTableName = buildFullTableName("EstimatedValues");

        StringBuilder sb = new StringBuilder();
        sb.append("INSERT INTO ").append(fullTableName)
        .append(" (equipmentId, kind, side, value, time, topic) FORMAT JSONEachRow\n");

        for (EstimatedValue row : rows) {
            sb.append("{")
            .append("\"equipmentId\":\"").append(row.equipmentId()).append("\",")
            .append("\"kind\":\"").append(row.kind()).append("\",")
            .append("\"side\":").append(row.side().map(s -> "\"" + s + "\"").orElse("null")).append(",")
            .append("\"value\":").append(row.value()).append(",")
            .append("\"time\":").append(row.time()).append(",")
            .append("\"topic\":\"").append(row.topic()).append("\"")
            .append("}\n");
        }

        performClickhouseRequest(sb.toString());
    }

    public String queryEstimatedValues(Optional<String> topic, double minTime, double maxTime) throws IOException, InterruptedException {
        createEstimatedValuesTableIfNotExists();
        if (topic.isPresent()) {
            sqlProtection(topic.get());
        }

        String fullTableName = buildFullTableName("EstimatedValues");

        String query = "SELECT equipmentId, kind, side, value, time, topic FROM " + fullTableName + " WHERE ";
        if (topic.isPresent()) {
            query += "topic='" + topic.get() + "' AND ";
        }
        query += "time >= " + minTime + " AND time < " + maxTime + " ORDER BY time FORMAT JSON";

        return performClickhouseRequest(query);
    }
}
