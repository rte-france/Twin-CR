/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.scada.api;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.util.RawValue;
import com.powsybl.commons.datasource.MemDataSource;
import com.powsybl.sld.svg.styles.DefaultStyleProviderFactory;
import com.powsybl.sld.svg.styles.StyleProvidersList;
import org.TwinCR.argus_backends.scada.alarms.AlarmRepository;
import org.TwinCR.argus_backends.scada.alarms.AlarmRule;
import org.TwinCR.argus_backends.common.api.ApiServerCommon;
import org.TwinCR.argus_backends.common.api.ControllableSwitchStyleProvider;
import org.TwinCR.argus_backends.common.api.EstimatedVariable;
import org.TwinCR.argus_backends.common.core.bridge.SseNatsBridge;
import org.TwinCR.argus_backends.common.gridmodel.ControlSenderCommon;
import org.TwinCR.argus_backends.common.gridmodel.GridModel;
import org.TwinCR.argus_backends.scada.alarms.AlarmEngine;
import org.TwinCR.argus_backends.scada.config.Config;
import org.TwinCR.argus_backends.scada.telemetry.SseEstimatedValuesBridge;
import org.TwinCR.argus_backends.scada.telemetry.StateEstimator;
import org.TwinCR.argus_backends.scada.telemetry.TelemetryConsumer;
import org.TwinCR.argus_backends.scada.util.JsonUtil;

import io.nats.client.Connection;
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

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

public class ApiServer extends ApiServerCommon {
    private final static Logger LOGGER = LoggerFactory.getLogger(ApiServer.class);
    private final AlarmEngine engine;
    private final TelemetryConsumer telemetryConsumer;
    private final String mappingString;
    private final SseEstimatedValuesBridge estimatedValuesBridge;
    private final double staleMeasurementTimeout;

    public ApiServer(Config config, SseNatsBridge natsBridge, SseEstimatedValuesBridge estimatedValuesBridge, Connection conn, String appName, AlarmEngine engine, TelemetryConsumer telemetryConsumer, ControlSenderCommon controlSender) throws Exception {
        super(config, natsBridge, conn, appName, telemetryConsumer, controlSender,
            new ControllableSwitchStyleProvider(parseControllableSwitches(config))
        );
        this.engine = engine;
        this.telemetryConsumer = telemetryConsumer;
        this.staleMeasurementTimeout = config.staleMeasurementTimeout();

        java.nio.file.Path path = config.scadaMappingPath();
        JsonNode node = MAPPER.readTree(path.toFile());
        this.mappingString = MAPPER.writeValueAsString(node);
        this.estimatedValuesBridge = estimatedValuesBridge;
    }

    private static Set<String> parseControllableSwitches(Config config) throws Exception {
        JsonNode scadaInputs = new ObjectMapper().readTree(config.scadaInputsPath().toFile());
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
        registry.add(new AlarmsAckHandler());
        registry.add(new AlarmsGetHandler());
        registry.add(new RulesHandler());
        registry.add(new CountHandler());
        registry.add(new UnchangedMeasurementsHandler());
        registry.add(new EstimHandler());
        registry.add(new IidmEstimHandler());
        registry.add(new SubEstimHandler());
        registry.add(new HistoryEstimHandler());
        registry.add(new EstimVariablesHandler());
        super.registerEndpoints(registry);
    }

    @Path("/mapping")
    class MappingHandler extends RouteHandler {
        @Override public String path() { return "/mapping"; }

        @GET
        @Tag(name = "Mapping")
        @Operation(summary = "Get SCADA variable mapping")
        @ApiResponse(responseCode = "200", description = "Variable mapping as JSON")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if (!"GET".equalsIgnoreCase(req.getMethod())) {
                respondError(resp, 405, "Method Not Allowed");
                return;
            }
            respondjson(resp, 200, mappingString);
        }
    }

    @Path("/alarms")
    class AlarmsGetHandler extends RouteHandler {
        @Override public String path() { return "/alarms"; }

        @GET
        @Tag(name = "Alarms")
        @Operation(summary = "List all active alarms")
        @ApiResponse(responseCode = "200", description = "JSON array of alarms")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if ("GET".equalsIgnoreCase(req.getMethod())) {
                respondjson(resp, 200, JsonUtil.toJson(AlarmRepository.listAll()));
            } else if ("POST".equalsIgnoreCase(req.getMethod()) && target.endsWith("/ack")) {
                String body = new String(req.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
                Map<?, ?> m = JsonUtil.fromJson(body, Map.class);
                boolean ok = AlarmRepository.ack((String) m.get("id"));
                respondjson(resp, ok ? 200 : 404, ok ? "{\"status\": \"ACKED\"}" : "{\"status\": \"NOT_FOUND\"}");
            } else {
                respondError(resp, 405, "Method Not Allowed");
            }
        }
    }

    @Path("/alarms/ack")
    class AlarmsAckHandler extends RouteHandler {
        @Override public String path() { return "/alarms/ack"; }

        @POST
        @Tag(name = "Alarms")
        @Operation(summary = "Acknowledge an alarm")
        @ApiResponse(responseCode = "200", description = "Alarm acknowledged")
        @ApiResponse(responseCode = "404", description = "Alarm not found")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            String body = new String(req.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
            Map<?, ?> m = JsonUtil.fromJson(body, Map.class);
            boolean ok = AlarmRepository.ack((String) m.get("id"));
            respondjson(resp, ok ? 200 : 404, ok ? "{\"status\": \"ACKED\"}" : "{\"status\": \"NOT_FOUND\"}");
        }
    }

    @Path("/rules")
    class RulesHandler extends RouteHandler {
        @Override public String path() { return "/rules"; }

        @GET
        @Tag(name = "Alarms")
        @Operation(summary = "List alarm rules")
        @ApiResponse(responseCode = "200", description = "JSON array of alarm rules")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if (!"GET".equalsIgnoreCase(req.getMethod())) {
                respondError(resp, 405, "Method Not Allowed");
                return;
            }
            List<AlarmRule> rules = engine.getRules();
            respondjson(resp, 200, JsonUtil.toJson(rules));
        }
    }

    @Path("/count")
    class CountHandler extends RouteHandler {
        @Override public String path() { return "/count"; }

        @GET
        @Tag(name = "SCADA")
        @Operation(summary = "Get per-subject message counts")
        @ApiResponse(responseCode = "200", description = "JSON map of subject to count")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if (!"GET".equalsIgnoreCase(req.getMethod())) {
                respondError(resp, 405, "Method Not Allowed");
                return;
            }
            respondjson(resp, 200, telemetryConsumer.getMapSubject2Count());
        }
    }

    @Path("/unchanged-measurements")
    class UnchangedMeasurementsHandler extends RouteHandler {
        @Override public String path() { return "/unchanged-measurements"; }

        @GET
        @Tag(name = "SCADA")
        @Operation(summary = "Get unchanged measurements list")
        @ApiResponse(responseCode = "200", description = "JSON unchanged measurements list")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if (!"GET".equalsIgnoreCase(req.getMethod())) {
                respondError(resp, 405, "Method Not Allowed");
                return;
            }
            respondjson(resp, 200, telemetryConsumer.getUnchangedMeasurements());
        }
    }

    @Path("/estim")
    class EstimHandler extends RouteHandler {
        @Override public String path() { return "/estim"; }

        @GET
        @Tag(name = "SCADA")
        @Operation(summary = "Run state estimation")
        @ApiResponse(responseCode = "200", description = "Estimation completed")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if (!"GET".equalsIgnoreCase(req.getMethod())) {
                respondError(resp, 405, "Method Not Allowed");
                return;
            }
            telemetryConsumer.runEstim();
            respondjson(resp, 200, "{\"status\": \"OK\"}");
        }
    }

    @Path("/iidmestim")
    class IidmEstimHandler extends RouteHandler {
        @Override public String path() { return "/iidmestim"; }

        @GET
        @Tag(name = "SCADA")
        @Operation(summary = "Run state estimation and export result as IIDM")
        @ApiResponse(responseCode = "200", description = "XIIDM file of estimated state")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if (!"GET".equalsIgnoreCase(req.getMethod())) {
                respondError(resp, 405, "Method Not Allowed");
                return;
            }
            telemetryConsumer.runEstim();
            LOGGER.info("Dumping estimated state as iidm");
            MemDataSource ds = writeIidm(GridModel.network);
            respondXml(resp, 200, ds);
        }
    }

    @Path("/sub-estim/{topic}")
    class SubEstimHandler extends RouteHandler {
        @Override public String path() { return "/sub-estim"; }

        @GET
        @Tag(name = "Streaming")
        @Operation(summary = "Subscribe to estimated values for a topic via SSE")
        @Parameter(name = "topic", in = ParameterIn.PATH, required = true, description = "Substation (or equipment id) to subscribe to")
        @ApiResponse(responseCode = "200", description = "SSE stream of topic messages")
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
            String topic = target.substring("/sub-estim/".length());
            estimatedValuesBridge.register(topic, sseClient(resp));
        }
    }

    @Path("/history-estim/{topic}")
    class HistoryEstimHandler extends RouteHandler {
        @Override public String path() { return "/history-estim"; }

        @GET
        @Tag(name = "History")
        @Operation(summary = "Query historical estimated values for a topic")
        @Parameter(name = "topic", in = ParameterIn.PATH, required = true, description = "Topic to query")
        @Parameter(name = "min", in = ParameterIn.QUERY, required = true, description = "Start of time range")
        @Parameter(name = "max", in = ParameterIn.QUERY, required = true, description = "End of time range")
        @ApiResponse(responseCode = "200", description = "JSON array of historical samples")
        @ApiResponse(responseCode = "400", description = "Invalid min/max parameters")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if (!"GET".equalsIgnoreCase(req.getMethod())) {
                respondError(resp, 405, "Method Not Allowed");
                return;
            }
            try {
                String topic = target.substring("/history-estim/".length());

                Map<String, String> params = splitQuery(req.getQueryString());
                double min = Double.parseDouble(params.get("min"));
                double max = Double.parseDouble(params.get("max"));

                String json = clickhouseClient.queryEstimatedValues(Optional.of(topic), min, max);
                respondjson(resp, 200, json);
            } catch (NumberFormatException e) {
                respondError(resp, 400, "Invalid min/max parameters");
            }
        }
    }

    @Path("/estim-variables")
    class EstimVariablesHandler extends RouteHandler {
        @Override public String path() { return "/estim-variables"; }
        @GET
        @Tag(name = "SCADA")
        @Operation(summary = "List all variables published by the state estimator")
        @ApiResponse(responseCode = "200", description = "JSON array of estimated variables")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if (!"GET".equalsIgnoreCase(req.getMethod())) {
                respondError(resp, 405, "Method Not Allowed");
                return;
            }
            List<EstimatedVariable> vars = StateEstimator.listVariables();
            ArrayNode array = MAPPER.createArrayNode();
            for (EstimatedVariable v : vars) {
                array.addRawValue(new RawValue(v.toJson()));
            }
            respondjson(resp, 200, MAPPER.writeValueAsString(array));
        }
    }

    @Override
    protected boolean showMeasurementsOnSld() {
        return true;
    }

    @Override
    protected String orchestratorControlTopic() {
        return "HMIControl";
    }

    @Override
    protected Optional<String> outputTopic(String outputId) {
        return Optional.empty();  // The SCADA telemetry consumer always subscribes to the full "HMI.SCADA.>"
    }

    protected com.powsybl.sld.svg.LegendWriterFactory getSldLegendWriterFactory() {
        return (network, svgParameters) -> new SCADASVGLegendWriter(network, svgParameters, telemetryConsumer);
    }

    @Override
    protected com.powsybl.sld.svg.styles.StyleProviderFactory getSldStyleProviderFactory() {
        return (network, svgParameters) -> new StyleProvidersList(
            new DefaultStyleProviderFactory().create(network, svgParameters),
            controllableSwitchStyleProvider,
            new StaleMeasurementStyleProvider(telemetryConsumer, staleMeasurementTimeout)
        );
    }
}
