/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.gm.api;

import org.TwinCR.argus_backends.common.api.ApiServerCommon;
import org.TwinCR.argus_backends.common.api.ControllableSwitchStyleProvider;
import org.TwinCR.argus_backends.common.core.bridge.SseNatsBridge;
import org.TwinCR.argus_backends.common.core.config.ConfigCommon;
import org.TwinCR.argus_backends.common.gridmodel.ControlSenderCommon;
import org.TwinCR.argus_backends.common.telemetry.TelemetryConsumerCommon;
import org.TwinCR.argus_backends.gm.core.config.Config;
import org.TwinCR.argus_backends.gm.gridmodel.GmMapping;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

import io.nats.client.Connection;
import io.nats.client.Message;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.enums.ParameterIn;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.servlet.AsyncContext;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

public class ApiServer extends ApiServerCommon {
    private final ObjectMapper mapper = new ObjectMapper();

    public ApiServer(Config config, SseNatsBridge bridge, Connection conn, String appName, TelemetryConsumerCommon telemetryConsumer, ControlSenderCommon controlSender) throws Exception {
        super(config, bridge, conn, appName, telemetryConsumer, controlSender,
            new ControllableSwitchStyleProvider(parseControllableSwitches(config))
        );
    }

    private static Set<String> parseControllableSwitches(Config config) throws Exception {
        JsonNode scadaInputs = new ObjectMapper().readTree(config.gmInputsPath().toFile());
        Set<String> ids = new HashSet<>();
        for (JsonNode entry : scadaInputs) {
            if ("state".equals(entry.path("kind").asText())) {
                ids.add(entry.path("equipmentId").asText());
            }
        }
        return ids;
    }

    @Override
    protected void registerEndpoints(RouteRegistry registry) {
        registry.add(new MappingHandler());
        registry.add(new SubDynawoTimelineHandler());
        registry.add(new HistoryDynawoTimelineHandler());
        registry.add(new SubGmCommandsHandler());
        registry.add(new HistoryGmCommandsHandler());
        registry.add(new InitHandler());
        registry.add(new StartHandler());
        registry.add(new PauseHandler());
        registry.add(new ResumeHandler());
        registry.add(new StopHandler());
        registry.add(new FastForwardHandler());
        registry.add(new ChangeNetworkCharacteristicsHandler());
        registry.add(new SetLinkCharacteristicsHandler());
        registry.add(new SetNodeCharacteristicsHandler());
        super.registerEndpoints(registry);
    }

    // -------------------------------------------------------------------------
    // Mapping / streaming / history
    // -------------------------------------------------------------------------

    @Path("/mapping")
    class MappingHandler extends RouteHandler {
        @Override public String path() { return "/mapping"; }

        @GET
        @Tag(name = "Mapping")
        @Operation(summary = "Get GM variable mapping")
        @ApiResponse(responseCode = "200", description = "Variable mapping as JSON")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if (!"GET".equalsIgnoreCase(req.getMethod())) {
                respondError(resp, 405, "Method Not Allowed");
                return;
            }
            respondjson(resp, 200, GmMapping.getJson());
        }
    }

    @Path("/sub-dynawo-timeline")
    class SubDynawoTimelineHandler extends RouteHandler {
        @Override public String path() { return "/sub-dynawo-timeline"; }

        @GET
        @Tag(name = "Streaming")
        @Operation(summary = "Subscribe to Dynawo timeline events via SSE")
        @ApiResponse(responseCode = "200", description = "SSE stream of Dynawo timeline events")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if (!"GET".equalsIgnoreCase(req.getMethod())) {
                respondError(resp, 405, "Method Not Allowed");
                return;
            }
            AsyncContext async = req.startAsync();
            async.setTimeout(0);
            respondSse(resp);
            bridge.register("Dynawo.Timeline", sseClient(resp));
        }
    }

    @Path("/history-dynawo-timeline")
    class HistoryDynawoTimelineHandler extends RouteHandler {
        @Override public String path() { return "/history-dynawo-timeline"; }

        @GET
        @Tag(name = "History")
        @Operation(summary = "Query historical Dynawo timeline events")
        @Parameter(name = "min", in = ParameterIn.QUERY, required = true, description = "Start of time range")
        @Parameter(name = "max", in = ParameterIn.QUERY, required = true, description = "End of time range")
        @ApiResponse(responseCode = "200", description = "JSON array of Dynawo timeline history")
        @ApiResponse(responseCode = "400", description = "Invalid min/max parameters")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if (!"GET".equalsIgnoreCase(req.getMethod())) {
                respondError(resp, 405, "Method Not Allowed");
                return;
            }
            try {
                Map<String, String> params = splitQuery(req.getQueryString());
                double min = Double.parseDouble(params.get("min"));
                double max = Double.parseDouble(params.get("max"));
                respondjson(resp, 200, clickhouseClient.queryDynawoTimeline(min, max));
            } catch (NumberFormatException e) {
                respondError(resp, 400, "Invalid min/max parameters");
            }
        }
    }

    @Path("/sub-gm-commands")
    class SubGmCommandsHandler extends RouteHandler {
        @Override public String path() { return "/sub-gm-commands"; }

        @GET
        @Tag(name = "Streaming")
        @Operation(summary = "Subscribe to game master commands via SSE")
        @ApiResponse(responseCode = "200", description = "SSE stream of game master commands")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if (!"GET".equalsIgnoreCase(req.getMethod())) {
                respondError(resp, 405, "Method Not Allowed");
                return;
            }
            AsyncContext async = req.startAsync();
            async.setTimeout(0);
            respondSse(resp);
            bridge.register("GameMasterControl.>", sseClient(resp));
        }
    }

    @Path("/history-gm-commands")
    class HistoryGmCommandsHandler extends RouteHandler {
        @Override public String path() { return "/history-gm-commands"; }

        @GET
        @Tag(name = "History")
        @Operation(summary = "Query historical commands sent from Gm clients")
        @Parameter(name = "min", in = ParameterIn.QUERY, required = true, description = "Start of time range")
        @Parameter(name = "max", in = ParameterIn.QUERY, required = true, description = "End of time range")
        @ApiResponse(responseCode = "200", description = "JSON array of Gm commands (time, command, command_source)")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if (!"GET".equalsIgnoreCase(req.getMethod())) {
                respondError(resp, 405, "Method Not Allowed");
                return;
            }
            Map<String, String> params = splitQuery(req.getQueryString());
            double min = Double.parseDouble(params.get("min"));
            double max = Double.parseDouble(params.get("max"));
            respondjson(resp, 200, clickhouseClient.queryGmCommands(min, max));
        }
    }

    // -------------------------------------------------------------------------
    // Simulation control
    // -------------------------------------------------------------------------

    @Path("/init")
    class InitHandler extends RouteHandler {
        @Override public String path() { return "/init"; }

        @POST
        @Tag(name = "Simulation")
        @Operation(summary = "Initialize the simulation from filesystem config")
        @ApiResponse(responseCode = "200", description = "Command accepted")
        @ApiResponse(responseCode = "400", description = "Only available in FILESYSTEM mode")
        @ApiResponse(responseCode = "500", description = "Command rejected or no response")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if (!"POST".equalsIgnoreCase(req.getMethod())) {
                respondError(resp, 405, "Method Not Allowed");
                return;
            }
            if (config.getInputSource() != ConfigCommon.InputSource.FILESYSTEM) {
                respondError(resp, 400, "This endpoint is only available in FILESYSTEM mode");
                return;
            }
            String requestJson = "{\"config_path\": \"" + config.configPath() + "\"}";
            Message reply = conn.request(
                "Start",
                requestJson.getBytes(StandardCharsets.UTF_8),
                Duration.ofSeconds(10)
            );
            if (reply == null) {
                respondError(resp, 500, "No response from the Orchestrator");
                return;
            }
            JsonNode replyJson = mapper.readTree(reply.getData());
            JsonNode status = replyJson.get("status");
            if (status != null && "READY".equals(status.asText())) {
                respondjson(resp, 200, mapper.writeValueAsString(replyJson));
            } else {
                respondjson(resp, 500, mapper.writeValueAsString(replyJson));
            }
        }
    }

    @Path("/start")
    class StartHandler extends RouteHandler {
        @Override public String path() { return "/start"; }

        @POST
        @Tag(name = "Simulation")
        @Operation(summary = "Start the simulation")
        @ApiResponse(responseCode = "200", description = "Command accepted")
        @ApiResponse(responseCode = "500", description = "Command rejected or no response")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if (!"POST".equalsIgnoreCase(req.getMethod())) {
                respondError(resp, 405, "Method Not Allowed");
                return;
            }
            String requestJson = "{\"command\": \"start\"}";
            Message reply = conn.request(
                "Start",
                requestJson.getBytes(StandardCharsets.UTF_8),
                Duration.ofSeconds(10)
            );
            if (reply == null) {
                respondError(resp, 500, "No response from the Orchestrator");
                return;
            }
            JsonNode replyJson = mapper.readTree(reply.getData());
            JsonNode status = replyJson.get("status");
            if (status != null && "STARTED".equals(status.asText())) {
                respondjson(resp, 200, mapper.writeValueAsString(replyJson));
            } else {
                respondjson(resp, 500, mapper.writeValueAsString(replyJson));
            }
        }
    }

    @Path("/resume") class ResumeHandler      extends SimulationControlHandler { ResumeHandler()      { super("resume"); } }
    @Path("/pause")  class PauseHandler        extends SimulationControlHandler { PauseHandler()       { super("pause"); } }
    @Path("/stop")   class StopHandler         extends SimulationControlHandler { StopHandler()        { super("stop"); } }
    @Path("/fast-forward") class FastForwardHandler extends SimulationControlHandler { FastForwardHandler() { super("fast-forward"); } }

    class SimulationControlHandler extends RouteHandler {
        private final String command;

        SimulationControlHandler(String command) { this.command = command; }

        @Override public String path() { return "/" + command; }

        @POST
        @Tag(name = "Simulation")
        @Operation(summary = "Send a simulation control command")
        @Parameter(name = "requester", in = ParameterIn.QUERY, required = true, description = "Requester identifier")
        @ApiResponse(responseCode = "200", description = "Command accepted")
        @ApiResponse(responseCode = "400", description = "Missing requester")
        @ApiResponse(responseCode = "500", description = "Command rejected or no response")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if (!"POST".equalsIgnoreCase(req.getMethod())) {
                respondError(resp, 405, "Method Not Allowed");
                return;
            }
            Map<String, String> params = splitQuery(req.getQueryString());
            String requester = params.get("requester");
            if (requester == null || requester.isEmpty()) {
                respondError(resp, 400, "Missing requester");
                return;
            }
            String requestJson = "{\"command\": \"" + command + "\"}";
            Message reply = conn.request(
                "GameMasterControl." + requester,
                requestJson.getBytes(StandardCharsets.UTF_8),
                Duration.ofSeconds(10)
            );
            if (reply == null) {
                respondError(resp, 500, "No response from the Orchestrator");
                return;
            }
            JsonNode replyJson = mapper.readTree(reply.getData());
            JsonNode status = replyJson.get("status");
            if (status != null && "OK".equals(status.asText())) {
                respondjson(resp, 200, mapper.writeValueAsString(replyJson));
            } else {
                respondjson(resp, 500, mapper.writeValueAsString(replyJson));
            }
        }
    }

    @Path("/change-network-characteristics")
    class ChangeNetworkCharacteristicsHandler extends RouteHandler {
        @Override public String path() { return "/change-network-characteristics"; }

        @POST
        @Tag(name = "Information Flow")
        @Operation(summary = "Change network characteristics (delay, drop, corruption) for nodes and/or links",
                   requestBody = @io.swagger.v3.oas.annotations.parameters.RequestBody(
                       description = "Characteristics to apply (e.g. delay, drop, corruption)",
                       content = @io.swagger.v3.oas.annotations.media.Content(
                           mediaType = "application/json",
                           schema = @io.swagger.v3.oas.annotations.media.Schema(example =
                               "{\"drop_function\": {\"type\": \"fixed\", \"value\": false}, \"corruption_functions\": [{\"type\": \"RandomNoiseMeasurementCorruption\", \"likelihood\": 0.01, \"noise_min\": -0.01, \"noise_max\": 0.01}], \"delay_function\": {\"type\": \"fixed\", \"delay\": 0.1}}"
                           )
                       )
                   ))
        @Parameter(name = "nodes", in = ParameterIn.QUERY, description = "Comma-separated list of node names to modify")
        @Parameter(name = "links", in = ParameterIn.QUERY, description = "Comma-separated list of links to modify, each as 'from:to'")
        @Parameter(name = "t_start", in = ParameterIn.QUERY, description = "Simulation time at which to apply the change")
        @Parameter(name = "requester", in = ParameterIn.QUERY, required = true, description = "Requester identifier")
        @ApiResponse(responseCode = "200", description = "Characteristics updated")
        @ApiResponse(responseCode = "400", description = "Missing parameters")
        @ApiResponse(responseCode = "500", description = "No response from the Orchestrator")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if (!"POST".equalsIgnoreCase(req.getMethod())) {
                respondError(resp, 405, "Method Not Allowed");
                return;
            }
            Map<String, String> params = splitQuery(req.getQueryString());
            String requester = getRequiredParam(params, "requester", resp); if (requester == null) return;

            // Read extra characteristics from request body
            String body = new String(req.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
            JsonNode bodyJson = body.isBlank() ? mapper.createObjectNode() : mapper.readTree(body);

            // Build scenario
            com.fasterxml.jackson.databind.node.ObjectNode scenario = mapper.createObjectNode();
            scenario.put("command", "change_network_characteristics");

            // Optional nodes list
            String nodesParam = params.get("nodes");
            if (nodesParam != null && !nodesParam.isEmpty()) {
                List<String> nodes = Arrays.stream(nodesParam.split(","))
                    .map(n -> n.trim())
                    .collect(Collectors.toList());
                scenario.set("nodes", mapper.valueToTree(nodes));
            }

            // Optional links list (format: "from:to,from:to,...")
            String linksParam = params.get("links");
            if (linksParam != null && !linksParam.isEmpty()) {
                com.fasterxml.jackson.databind.node.ArrayNode links = mapper.createArrayNode();
                for (String link : linksParam.split(",")) {
                    String[] parts = link.trim().split(":");
                    if (parts.length == 2) {
                        links.add(mapper.createObjectNode()
                            .put("from", parts[0])
                            .put("to", parts[1]));
                    }
                }
                scenario.set("links", links);
            }

            // Optional t_start
            String tStart = params.get("t_start");
            if (tStart != null && !tStart.isEmpty()) {
                scenario.put("t_start", Double.parseDouble(tStart));
            }

            // Merge body fields (characteristics like delay, drop, corruption)
            bodyJson.fields().forEachRemaining(e -> scenario.set(e.getKey(), e.getValue()));

            JsonNode replyJson = requestOrchestratorControl(requester, scenario);
            JsonNode status = replyJson != null ? replyJson.get("status") : null;
            if (status != null && "OK".equals(status.asText())) {
                respondjson(resp, 200, mapper.writeValueAsString(replyJson));
            } else {
                respondjson(resp, 500, mapper.writeValueAsString(replyJson));
            }
        }
    }

    @Path("/set-link-characteristics")
    class SetLinkCharacteristicsHandler extends RouteHandler {
        @Override public String path() { return "/set-link-characteristics"; }

        @POST
        @Tag(name = "Information Flow")
        @Operation(summary = "Set characteristics of a link between two nodes")
        @Parameter(name = "from", in = ParameterIn.QUERY, required = true, description = "Source node name")
        @Parameter(name = "to", in = ParameterIn.QUERY, required = true, description = "Destination node name")
        @Parameter(name = "requester", in = ParameterIn.QUERY, required = true, description = "Requester identifier")
        @ApiResponse(responseCode = "200", description = "OK")
        @ApiResponse(responseCode = "400", description = "Missing parameters")
        @ApiResponse(responseCode = "500", description = "No response from the Orchestrator")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if (!"POST".equalsIgnoreCase(req.getMethod())) {
                respondError(resp, 405, "Method Not Allowed");
                return;
            }
            Map<String, String> params = splitQuery(req.getQueryString());
            String from = getRequiredParam(params, "from", resp);
            String to = getRequiredParam(params, "to", resp);
            String requester = getRequiredParam(params, "requester", resp);

            JsonNode body = MAPPER.readTree(req.getInputStream());
            ObjectNode scenario = MAPPER.createObjectNode();
            scenario.put("command", "change_network_characteristics");
            scenario.set("links", MAPPER.valueToTree(List.of(Map.of("from", from, "to", to))));
            // Merge characteristics fields directly into the scenario object
            scenario.setAll((ObjectNode) body);

            JsonNode reply = requestOrchestratorControl(requester, scenario);
            JsonNode status = reply.get("status");
            if (status != null && "OK".equals(status.asText())) {
                respondjson(resp, 200, MAPPER.writeValueAsString(reply));
            } else {
                respondjson(resp, 500, MAPPER.writeValueAsString(reply));
            }
        }
    }

    @Path("/set-node-characteristics")
    class SetNodeCharacteristicsHandler extends RouteHandler {
        @Override public String path() { return "/set-node-characteristics"; }

        @POST
        @Tag(name = "Information Flow")
        @Operation(summary = "Set characteristics of a node")
        @Parameter(name = "node", in = ParameterIn.QUERY, required = true, description = "Node name")
        @Parameter(name = "requester", in = ParameterIn.QUERY, required = true, description = "Requester identifier")
        @ApiResponse(responseCode = "200", description = "OK")
        @ApiResponse(responseCode = "400", description = "Missing parameters")
        @ApiResponse(responseCode = "500", description = "No response from the Orchestrator")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if (!"POST".equalsIgnoreCase(req.getMethod())) {
                respondError(resp, 405, "Method Not Allowed");
                return;
            }
            Map<String, String> params = splitQuery(req.getQueryString());
            String node = getRequiredParam(params, "node", resp);
            String requester = getRequiredParam(params, "requester", resp);

            JsonNode body = MAPPER.readTree(req.getInputStream());
            ObjectNode scenario = MAPPER.createObjectNode();
            scenario.put("command", "change_network_characteristics");
            scenario.set("nodes", MAPPER.valueToTree(List.of(node)));
            // Merge characteristics fields directly into the scenario object
            scenario.setAll((ObjectNode) body);

            JsonNode reply = requestOrchestratorControl(requester, scenario);
            JsonNode status = reply.get("status");
            if (status != null && "OK".equals(status.asText())) {
                respondjson(resp, 200, MAPPER.writeValueAsString(reply));
            } else {
                respondjson(resp, 500, MAPPER.writeValueAsString(reply));
            }
        }
    }

    @Override
    protected String orchestratorControlTopic() {
        return "GameMasterControl";
    }
}
