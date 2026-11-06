/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.common.api;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.powsybl.commons.PowsyblException;
import com.powsybl.commons.datasource.MemDataSource;
import com.powsybl.iidm.network.Network;
import com.powsybl.iidm.network.VoltageLevel;
import com.powsybl.nad.NadParameters;
import com.powsybl.nad.NetworkAreaDiagram;
import com.powsybl.nad.build.iidm.VoltageLevelFilter;
import com.powsybl.nad.layout.BasicForceLayout;
import com.powsybl.nad.layout.GeographicalLayoutFactory;
import com.powsybl.nad.svg.iidm.DefaultLabelProvider;
import com.powsybl.nad.svg.iidm.LabelProviderFactory;
import com.powsybl.iidm.network.Substation;
import com.powsybl.sld.SingleLineDiagram;
import com.powsybl.sld.SldParameters;
import com.powsybl.sld.svg.styles.DefaultStyleProviderFactory;
import com.powsybl.sld.svg.styles.StyleProvidersList;

import org.TwinCR.argus_backends.common.core.bridge.SseClient;
import org.TwinCR.argus_backends.common.core.bridge.SseNatsBridge;
import org.TwinCR.argus_backends.common.core.config.ConfigCommon;
import org.TwinCR.argus_backends.common.core.ifl.InformationFlowModelLayout;
import org.TwinCR.argus_backends.common.core.ifl.SvgRenderer;
import org.TwinCR.argus_backends.common.datamodel.Value;
import org.TwinCR.argus_backends.common.gridmodel.ControlSenderCommon;
import org.TwinCR.argus_backends.common.gridmodel.GridModel;
import org.TwinCR.argus_backends.common.gridmodel.NetworkTableExtractor;
import org.TwinCR.argus_backends.common.gridmodel.TitienDiagramLabelProvider;
import org.TwinCR.argus_backends.common.gridmodel.TitienResourcesComponentLibrary;
import org.TwinCR.argus_backends.common.telemetry.TelemetryConsumerCommon;
import org.eclipse.jetty.http2.server.HTTP2CServerConnectionFactory;
import org.eclipse.jetty.io.EofException;
import org.eclipse.jetty.server.HttpConfiguration;
import org.eclipse.jetty.server.HttpConnectionFactory;
import org.eclipse.jetty.server.Request;
import org.eclipse.jetty.server.Server;
import org.eclipse.jetty.server.ServerConnector;
import org.eclipse.jetty.server.handler.AbstractHandler;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import io.nats.client.Connection;
import io.nats.client.Message;
import io.swagger.v3.core.util.Json;
import io.swagger.v3.jaxrs2.Reader;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.enums.ParameterIn;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import jakarta.servlet.AsyncContext;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;

import java.io.*;
import java.net.URLConnection;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.NoSuchElementException;
import java.util.Optional;
import java.util.Properties;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.stream.Collectors;

public abstract class ApiServerCommon {
    private static final Logger LOGGER = LoggerFactory.getLogger(ApiServerCommon.class);
    protected final ObjectMapper MAPPER = new ObjectMapper();
    protected final ConfigCommon config;
    protected final ClickhouseClient clickhouseClient;
    protected final SseNatsBridge bridge;
    protected final Connection conn;
    protected final TelemetryConsumerCommon telemetryConsumer;
    protected final String appName;
    protected final boolean scada;
    protected final ControlSenderCommon controlSender;
    protected final String iidmVersion;
    protected final ControllableSwitchStyleProvider controllableSwitchStyleProvider;

    private static final Set<SseTopicSubscriber> clients = ConcurrentHashMap.newKeySet();
    private static final ScheduledExecutorService sseClientsManager = Executors.newSingleThreadScheduledExecutor();

    public abstract static class RouteHandler {
        public abstract String path();
        public abstract void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception;
    }

    public static class RouteRegistry {
        private final List<RouteHandler> routes = new ArrayList<>();

        public void add(RouteHandler handler) {
            routes.add(handler);
        }

        public List<RouteHandler> getHandlers() { return routes; }

        public void dispatch(String target, Request baseRequest,
                             HttpServletRequest req, HttpServletResponse resp) throws IOException {
            for (RouteHandler handler : routes) {
                if (target.equals(handler.path()) || target.startsWith(handler.path() + "/")) {
                    baseRequest.setHandled(true);
                    try {
                        LOGGER.debug("ApiServer received on target {}, method: {}, query string: {}", target, req.getMethod(), req.getQueryString());
                        handler.handle(target, req, resp);
                    } catch (EofException e) {
                        // Client closed the connection before the response was written (e.g. aborted fetch)
                        LOGGER.debug("Client closed connection on {}: {}", target, e.getMessage());
                    } catch (Exception e) {
                        if (e instanceof InterruptedException) {
                            // Exception catch higiene: still interrupt the thread even if catch the error
                            Thread.currentThread().interrupt();
                        }
                        LOGGER.warn("Error handling {}", target, e);
                        if (!resp.isCommitted()) {
                            // Jetty cannot setStatus(500) if the client already received the start of the reply (e.g. with a 200)
                            // This mainly occurs if an error occurs while writting a large reply flushed halfway
                            // In that case, Jetty aborts the connection and the client gets a truncated response instead of a corrupted one (part of normal respon + error message)
                            respondError(resp, 500, e.getMessage());
                        }
                    }
                    return;
                }
            }
            resp.setStatus(404);
            baseRequest.setHandled(true);
        }
    }

    public ApiServerCommon(ConfigCommon config, SseNatsBridge bridge, Connection conn, String appName,
                           TelemetryConsumerCommon telemetryConsumer, ControlSenderCommon controlSender,
                           ControllableSwitchStyleProvider controllableSwitchStyleProvider) throws Exception {
        clickhouseClient = new ClickhouseClient(conn, appName);
        this.config = config;
        this.bridge = bridge;
        this.conn = conn;
        this.telemetryConsumer = telemetryConsumer;
        this.appName = appName;
        this.scada = ("backend_SCADA".compareTo(appName) == 0);
        this.controlSender = controlSender;
        this.iidmVersion = config.iidmVersion();
        this.controllableSwitchStyleProvider = controllableSwitchStyleProvider;

        Server server = new Server();
        HttpConfiguration httpConfig = new HttpConfiguration();
        ServerConnector connector = new ServerConnector(server,
            new HttpConnectionFactory(httpConfig),
            new HTTP2CServerConnectionFactory(httpConfig));
        connector.setPort(config.httpPort());
        server.addConnector(connector);

        RouteRegistry registry = new RouteRegistry();
        registerEndpoints(registry);

        sseClientsManager.scheduleAtFixedRate(() -> {
            LOGGER.info("Clients: {}", clients);
            Iterator<SseTopicSubscriber> it = clients.iterator();
            while (it.hasNext()) {
                SseTopicSubscriber client = it.next();
                try {
                    client.sendKeepAlive();
                } catch (IOException e) {
                    client.close();
                    it.remove();
                }
            }
        }, 10, 10, TimeUnit.SECONDS);

        server.setHandler(new AbstractHandler() {
            @Override
            public void handle(String target, Request baseRequest,
                               HttpServletRequest req, HttpServletResponse resp) throws IOException {
                registry.dispatch(target, baseRequest, req, resp);
            }
        });

        server.start();
        LOGGER.info("API server started on port {}", config.httpPort());
    }

    protected void registerEndpoints(RouteRegistry registry) {
        registry.add(new OpenApiHandler(registry));
        registry.add(new SwaggerUiHandler());
        registry.add(new HealthHandler());
        registry.add(new IidmHandler());
        registry.add(new SldHandler());
        registry.add(new SldMultiHandler());
        registry.add(new NadHandler());
        registry.add(new SubstationListHandler());
        registry.add(new NetworkComponentTypesHandler());
        registry.add(new NetworkTypeOfHandler());
        registry.add(new NetworkComponentSchemaHandler());
        registry.add(new NetworkComponentRowsHandler());
        registry.add(new SubHandler());
        registry.add(new SubDynawoConstraintsHandler());
        registry.add(new SubScadaCommandsHandler());
        registry.add(new TimeHandler());
        registry.add(new InitClockTimeHandler());
        registry.add(new HistoryHandler());
        registry.add(new HistoryDynawoConstraintsHandler());
        registry.add(new HistoryScadaCommandsHandler());
        registry.add(new ControlBatchCheckHandler());
        registry.add(new ControlPostHandler());
        registry.add(new RawControlPostHandler());
        registry.add(new GetLinkCharacteristicsHandler());
        registry.add(new GetNodeCharacteristicsHandler());
        registry.add(new GetPathCharacteristicsHandler());
        registry.add(new IflGraphHandler());
        registry.add(new IflNodesHandler());
    }

    class OpenApiHandler extends RouteHandler {
        private final RouteRegistry registry;
        OpenApiHandler(RouteRegistry registry) { this.registry = registry; }
        @Override public String path() { return "/openapi.json"; }
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            OpenAPI openAPI = new OpenAPI();
            openAPI.info(new Info().title("Argus backend API").version("1.0").description(appName));
            Reader reader = new Reader(openAPI);
            Set<Class<?>> classes = registry.getHandlers().stream()
                .map(RouteHandler::getClass)
                .collect(Collectors.toSet());
            OpenAPI result = reader.read(classes);
            respondjson(resp, 200, Json.pretty(result));
        }
    }

    // Get swagger-ui version from maven instead of hardcoding it
    private static String swaggerUiVersion() {
        try (InputStream is = ApiServerCommon.class.getResourceAsStream(
                "/META-INF/maven/org.webjars/swagger-ui/pom.properties")) {
            if (is != null) {
                Properties props = new Properties();
                props.load(is);
                String version = props.getProperty("version");
                if (version != null && !version.isBlank()) {
                    return version;
                }
            }
        } catch (IOException e) {
            LOGGER.warn("Could not read the swagger-ui webjar version", e);
        }
        return null;
    }

    private static final String SWAGGER_UI_VERSION = swaggerUiVersion();

    class SwaggerUiHandler extends RouteHandler {
        @Override public String path() { return "/swagger-ui"; }
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            String suffix = target.equals("/swagger-ui") || target.equals("/swagger-ui/")
                ? "/index.html"
                : target.substring("/swagger-ui".length());
            if (SWAGGER_UI_VERSION == null) {
                LOGGER.error("swagger-ui webjar not found on the classpath");
                resp.setStatus(404);
                return;
            }
            String resource = "/META-INF/resources/webjars/swagger-ui/" + SWAGGER_UI_VERSION + suffix;
            try (InputStream is = getClass().getResourceAsStream(resource)) {
                if (is == null) { resp.setStatus(404); return; }
                // Workaround swagger not allowing body on GET + default url to /openapi.json
                if (suffix.equals("/swagger-initializer.js")) {
                    String js = """
                        window.onload = function() {
                            window.ui = SwaggerUIBundle({
                            url: "/openapi.json",
                            dom_id: '#swagger-ui',
                            presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
                            layout: "StandaloneLayout",
                            requestInterceptor: function(request) {
                                if (request.method === 'GET' || request.method === 'HEAD') {
                                delete request.body;
                                delete request.headers['Content-Type'];
                                }
                                return request;
                            }
                            });
                        };
                        """;
                    byte[] bytes = js.getBytes(StandardCharsets.UTF_8);
                    resp.setContentType("application/javascript");
                    resp.setContentLength(bytes.length);
                    resp.getOutputStream().write(bytes);
                } else if (suffix.equals("/index.html")) {
                    String html = new String(is.readAllBytes(), StandardCharsets.UTF_8)
                        .replace("<head>", "<head>\n    <base href=\"/swagger-ui/\">")
                        .replace("href=\"./", "href=\"/swagger-ui/")
                        .replace("src=\"./", "src=\"/swagger-ui/");
                        byte[] bytes = html.getBytes(StandardCharsets.UTF_8);
                    resp.setContentType("text/html");
                    resp.setContentLength(bytes.length);
                    resp.getOutputStream().write(bytes);
                } else {
                    String mime = URLConnection.guessContentTypeFromName(resource);
                    if (mime != null) resp.setContentType(mime);
                    resp.setStatus(200);
                    is.transferTo(resp.getOutputStream());
                }
            }
        }
    }

    @Path("/health")
    class HealthHandler extends RouteHandler {
        @Override public String path() { return "/health"; }

        @GET
        @Tag(name = "Common")
        @Operation(summary = "Health check")
        @ApiResponse(responseCode = "200", description = "Server is up")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            respondjson(resp, 200, "{\"status\": \"OK\"}");
        }
    }

    @Path("/iidm")
    class IidmHandler extends RouteHandler {
        @Override public String path() { return "/iidm"; }

        @GET
        @Tag(name = "Grid")
        @Operation(summary = "Export network as IIDM/XIIDM")
        @ApiResponse(responseCode = "200", description = "XIIDM file")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if (!"GET".equalsIgnoreCase(req.getMethod())) {
                respondError(resp, 405, "Method Not Allowed");
                return;
            }
            telemetryConsumer.updateNetwork(Optional.empty());
            MemDataSource ds = writeIidm(GridModel.network);
            respondXml(resp, 200, ds);
        }
    }

    @Path("/sld/{substationName}")
    class SldHandler extends RouteHandler {
        @Override public String path() { return "/sld"; }

        @GET
        @Tag(name = "Grid")
        @Operation(summary = "Get single-line diagram for a substation or voltage level")
        @Parameter(name = "substationName", in = ParameterIn.PATH, required = true, description = "Substation or voltage level ID")
        @ApiResponse(responseCode = "200", description = "SVG and metadata as JSON")
        @ApiResponse(responseCode = "404", description = "Element not found")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if (!"GET".equalsIgnoreCase(req.getMethod())) {
                respondError(resp, 405, "Method Not Allowed");
                return;
            }
            // Note: target is already automatically URI decoded by Jetty
            String substationName = target.substring("/sld/".length());
            VoltageLevel vl = GridModel.network.getVoltageLevel(substationName);
            Substation sub = GridModel.network.getSubstation(substationName);

            String subTopic;
            if (sub != null) {
                subTopic = substationName;
            } else if (vl != null) {
                subTopic = vl.getSubstation().get().getId();
            } else {
                respondError(resp, 404, substationName + " is neither a VoltageLevel nor a Substation");
                return;
            }

            telemetryConsumer.temporarilyAcquireSubTopic(subTopic);

            Writer svgWriter = new StringWriter();
            Writer metadataWriter = new StringWriter();

            com.powsybl.sld.svg.SvgParameters svgParams = new com.powsybl.sld.svg.SvgParameters()
                .setUseName(true)
                .setLabelCentered(true)
                .setLabelDiagonal(false)
                .setTooltipEnabled(true)
                .setActivePowerUnit("MW")
                .setReactivePowerUnit("MVar")
                .setBusesLegendAdded(true)
                .setFeederInfoSymmetry(true);

            boolean showMeasurements = showMeasurementsOnSld();
            com.powsybl.sld.layout.LayoutParameters layoutParameters = new com.powsybl.sld.layout.LayoutParameters()
                .setSpaceForFeederInfos(80)  // Add room to display TI's
                .setCellWidth(60)
                .setStackHeight(0);
            if (showMeasurements) {
                layoutParameters
                    .setSpaceForFeederInfos(120)  // Even more room for measurements
                    .setCellWidth(70);
            }

            SldParameters params = new SldParameters()
                .setSvgParameters(svgParams)
                .setLayoutParameters(layoutParameters)
                .setComponentLibrary(new TitienResourcesComponentLibrary())
                .setStyleProviderFactory(getSldStyleProviderFactory())
                .setLabelProviderFactory(
                    (network, componentLibrary, layoutParams, svgParameters) ->
                        new TitienDiagramLabelProvider(componentLibrary, layoutParams, svgParameters, network, showMeasurements))
                .setLegendWriterFactory(getSldLegendWriterFactory());

            SingleLineDiagram.draw(GridModel.network, substationName, svgWriter, metadataWriter, params);

            Map<String, String> responseMap = new HashMap<>();
            responseMap.put("svg", svgWriter.toString());
            responseMap.put("metadata", metadataWriter.toString());
            responseMap.put("element_id", substationName);
            respondjson(resp, 200, MAPPER.writeValueAsString(responseMap));
        }
    }

    @Path("/sld-multi")
    class SldMultiHandler extends RouteHandler {
        @Override public String path() { return "/sld-multi"; }
        @GET
        @Tag(name = "Grid")
        @Operation(summary = "Get single-line diagram for multiple substations")
        @Parameter(name = "substations", in = ParameterIn.QUERY, required = true, description = "Comma-separated list of substation IDs")
        @ApiResponse(responseCode = "200", description = "SVG and metadata as JSON")
        @ApiResponse(responseCode = "400", description = "Missing substations parameter")
        @ApiResponse(responseCode = "404", description = "One or more substations not found")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            try {
                if (!"GET".equalsIgnoreCase(req.getMethod())) {
                    respondError(resp, 405, "Method Not Allowed");
                    return;
                }
                Map<String, String> queryParams = splitQuery(req.getQueryString());
                String raw = queryParams.get("substations");
                if (raw == null || raw.isBlank()) {
                    respondError(resp, 400, "Missing required query parameter: substations");
                    return;
                }
                List<String> substationIds = Arrays.stream(raw.split(","))
                    .map(String::trim)
                    .filter(s -> !s.isEmpty())
                    .collect(Collectors.toList());

                substationIds.forEach(id -> telemetryConsumer.temporarilyAcquireSubTopic(id));

                Writer svgWriter = new StringWriter();
                Writer metadataWriter = new StringWriter();
                com.powsybl.sld.svg.SvgParameters svgParams = new com.powsybl.sld.svg.SvgParameters()
                    .setUseName(true)
                    .setLabelCentered(true)
                    .setLabelDiagonal(false)
                    .setTooltipEnabled(true)
                    .setActivePowerUnit("MW")
                    .setReactivePowerUnit("MVar")
                    .setBusesLegendAdded(true)
                    .setFeederInfoSymmetry(true);

                SldParameters params = new SldParameters()
                    .setSvgParameters(svgParams)
                    .setComponentLibrary(new TitienResourcesComponentLibrary())
                    .setStyleProviderFactory((network, svgParameters) -> new StyleProvidersList(
                        new DefaultStyleProviderFactory().create(network, svgParameters),
                        controllableSwitchStyleProvider
                    ));

                SingleLineDiagram.drawMultiSubstations(GridModel.network, substationIds, svgWriter, metadataWriter, params);

                Map<String, Object> responseMap = new HashMap<>();
                responseMap.put("svg", svgWriter.toString());
                responseMap.put("metadata", metadataWriter.toString());
                respondjson(resp, 200, MAPPER.writeValueAsString(responseMap));
            } catch (PowsyblException e) {  // One or several substations not found
                respondError(resp, 404, e.getMessage());
            }
        }
    }

    @Path("/nad")
    class NadHandler extends RouteHandler {
        @Override public String path() { return "/nad"; }

        @GET
        @Tag(name = "Grid")
        @Operation(summary = "Get network area diagram for given voltage levels")
        @Parameter(name = "voltageLevels", in = ParameterIn.QUERY, required = true, description = "Comma-separated list of voltage level IDs")
        @Parameter(name = "depth", in = ParameterIn.QUERY, description = "Depth of neighbours to include (default 0)")
        @Parameter(name = "layout", in = ParameterIn.QUERY, description = "Layout algorithm: 'default' (default) or 'geographical'")
        @Parameter(name = "radiusFactor", in = ParameterIn.QUERY, description = "Radius factor for geographical layout (default 500)")
        @ApiResponse(responseCode = "200", description = "SVG and metadata as JSON")
        @ApiResponse(responseCode = "400", description = "Missing voltageLevels parameter")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if (!"GET".equalsIgnoreCase(req.getMethod())) {
                respondError(resp, 405, "Method Not Allowed");
                return;
            }
            Map<String, String> queryParams = splitQuery(req.getQueryString());
            int depth = Integer.parseInt(queryParams.getOrDefault("depth", "0"));
            String layoutParam = queryParams.getOrDefault("layout", "default");

            String vlParam = queryParams.get("voltageLevels");
            if (vlParam == null || vlParam.isBlank()) {
                respondError(resp, 400, "Missing 'voltageLevels' query parameter");
                return;
            }

            List<String> voltageLevelNames = Arrays.stream(vlParam.split(",")).collect(Collectors.toList());
            VoltageLevelFilter voltageLevels = VoltageLevelFilter.createVoltageLevelsDepthFilter(GridModel.network, voltageLevelNames, depth);
            Set<String> substationIds = voltageLevels.getVoltageLevels().stream()
                .map(vlItem -> vlItem.getSubstation().get().getId())
                .collect(Collectors.toSet());
            substationIds.forEach(telemetryConsumer::temporarilyAcquireSubTopic);

            Writer svgWriter = new StringWriter();
            Writer metadataWriter = new StringWriter();

            com.powsybl.nad.svg.SvgParameters svgParams = new com.powsybl.nad.svg.SvgParameters()
                .setPowerValuePrecision(1)
                .setVoltageValuePrecision(1)
                .setCurrentValuePrecision(1)
                .setAngleValuePrecision(1)
                .setEdgeInfoAlongEdge(true)
                .setEdgeInfosIncluded(true)
                .setVoltageLevelLegendsIncluded(true)
                .setInsertNameDesc(true)
                .setLanguageTag("fr");

            com.powsybl.nad.layout.LayoutParameters layoutParams = new com.powsybl.nad.layout.LayoutParameters()
                .setInjectionsAdded(true);

            LabelProviderFactory labelProviderFactory = (network, svgParameters) ->
                new DefaultLabelProvider.Builder()
                    .setVoltageLevelDetails(true)
                    .build(network, svgParameters);

            NadParameters nadParams = new NadParameters()
                .setSvgParameters(svgParams)
                .setLayoutParameters(layoutParams)
                .setLabelProviderFactory(labelProviderFactory);

            if ("geographical".equalsIgnoreCase(layoutParam)) {
                double radiusFactor = Double.parseDouble(queryParams.getOrDefault("radiusFactor", "500"));
                nadParams.setLayoutFactory(new GeographicalLayoutFactory(GridModel.network, 150000, radiusFactor, () -> new BasicForceLayout()));
            }

            NetworkAreaDiagram.draw(GridModel.network, svgWriter, metadataWriter, nadParams, voltageLevels);

            Map<String, String> responseMap = new HashMap<>();
            responseMap.put("svg", svgWriter.toString());
            responseMap.put("metadata", metadataWriter.toString());
            responseMap.put("element_id", vlParam);
            respondjson(resp, 200, MAPPER.writeValueAsString(responseMap));
        }
    }

    @Path("/substation-list")
    class SubstationListHandler extends RouteHandler {
        @Override public String path() { return "/substation-list"; }

        @GET
        @Tag(name = "Grid")
        @Operation(summary = "List all substations with their voltage levels")
        @ApiResponse(responseCode = "200", description = "JSON array of substations")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if (!"GET".equalsIgnoreCase(req.getMethod())) {
                respondError(resp, 405, "Method Not Allowed");
                return;
            }
            JsonNode list;
            synchronized (GridModel.network) {
                list = GridModel.getSubstationsWithVoltageLevels();
            }
            respondjson(resp, 200, list.toString());
        }
    }

    @Path("/network/component-types")
    class NetworkComponentTypesHandler extends RouteHandler {
        @Override public String path() { return "/network/component-types"; }

        private final Map<String, NetworkTableExtractor.NetworkTable> tables = GridModel.getNetworkStaticParameters();

        @GET
        @Tag(name = "Grid")
        @Operation(summary = "List available network component types")
        @ApiResponse(responseCode = "200", description = "List of component type names")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if (!"GET".equalsIgnoreCase(req.getMethod())) {
                respondError(resp, 405, "Method Not Allowed");
                return;
            }
            respondjson(resp, 200, new ObjectMapper().writeValueAsString(tables.keySet()));
        }
    }

    @Path("/network/type-of")
    class NetworkTypeOfHandler extends RouteHandler {
        @Override public String path() { return "/network/type-of"; }

        private final Map<String, NetworkTableExtractor.NetworkTable> tables = GridModel.getNetworkStaticParameters();

        @GET
        @Tag(name = "Grid")
        @Operation(summary = "Get the component type of an element by its id")
        @Parameter(name = "id", in = ParameterIn.PATH, required = true, description = "ID of the component to fetch")
        @ApiResponse(responseCode = "200", description = "Component type name")
        @ApiResponse(responseCode = "404", description = "No component found with the given id")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if (!"GET".equalsIgnoreCase(req.getMethod())) {
                respondError(resp, 405, "Method Not Allowed");
                return;
            }
            String id = req.getParameter("id");
            if (id == null || id.isBlank()) {
                respondError(resp, 400, "Missing 'id' parameter");
                return;
            }
            String type = tables.entrySet().stream()
                .filter(e -> e.getValue().contains(id))
                .map(Map.Entry::getKey)
                .findFirst()
                .orElse(null);
            if (type == null) {
                respondError(resp, 404, "No component found with id: " + id);
                return;
            }
            respondjson(resp, 200, new ObjectMapper().writeValueAsString(Map.of("type", type)));
        }
    }

    @Path("/network/component-types-schema/{type}")
    class NetworkComponentSchemaHandler extends RouteHandler {
        @Override public String path() { return "/network/component-types-schema"; }

        private final Map<String, NetworkTableExtractor.NetworkTable> tables = GridModel.getNetworkStaticParameters();

        @GET
        @Tag(name = "Grid")
        @Operation(summary = "Get column names and component ids for an component type")
        @Parameter(name = "type", in = ParameterIn.PATH, required = true, description = "Network component type (e.g. load, generator, line)")
        @ApiResponse(responseCode = "200", description = "Schema and ids")
        @ApiResponse(responseCode = "404", description = "Unknown component type")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if (!"GET".equalsIgnoreCase(req.getMethod())) {
                respondError(resp, 405, "Method Not Allowed");
                return;
            }

            String type = target.substring("/network/component-types-schema/".length());
            if (type.isEmpty()) {
                respondError(resp, 400, "Missing component type");
                return;
            }

            NetworkTableExtractor.NetworkTable table = tables.get(type);
            if (table == null) {
                respondError(resp, 404, "Unknown component type: " + type);
                return;
            }

            respondjson(resp, 200, new ObjectMapper().writeValueAsString(
                Map.of("columns", table.columns(), "ids", new ArrayList<>(table.ids()))
            ));
        }
    }

    @Path("/network/component-types-rows/{type}")
    class NetworkComponentRowsHandler extends RouteHandler {
        @Override public String path() { return "/network/component-types-rows"; }

        private final Map<String, NetworkTableExtractor.NetworkTable> tables = GridModel.getNetworkStaticParameters();

        @POST
        @Tag(name = "Grid")
        @Operation(summary = "Get row values for a given component type and list of component ids")
        @Parameter(name = "type", in = ParameterIn.PATH, required = true, description = "Network component type (e.g. load, generator, line)")
        @ApiResponse(responseCode = "200", description = "List of rows with all column values")
        @ApiResponse(responseCode = "404", description = "Unknown component type")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if (!"POST".equalsIgnoreCase(req.getMethod())) {
                respondError(resp, 405, "Method Not Allowed");
                return;
            }

            String type = target.substring("/network/component-types-rows/".length());
            if (type.isEmpty()) {
                respondError(resp, 400, "Missing component type");
                return;
            }

            NetworkTableExtractor.NetworkTable table = tables.get(type);
            if (table == null) {
                respondError(resp, 404, "Unknown component type: " + type);
                return;
            }

            JsonNode body = MAPPER.readTree(req.getInputStream());
            List<String> ids = MAPPER.convertValue(body, new TypeReference<List<String>>() {});

            Map<String, List<Object>> result = new LinkedHashMap<>();
            for (String id : ids) {
                List<Object> row = table.row(id);
                if (row != null) result.put(id, row);
            }

            respondjson(resp, 200, MAPPER.writeValueAsString(result));
        }
    }

    @Path("/sub/{topic}")
    class SubHandler extends RouteHandler {
        @Override public String path() { return "/sub"; }

        @GET
        @Tag(name = "Streaming")
        @Operation(summary = "Subscribe to live data for a topic via SSE")
        @Parameter(name = "topic", in = ParameterIn.PATH, required = true, description = "NATS topic suffix to subscribe to")
        @ApiResponse(responseCode = "200", description = "SSE stream of topic messages")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if (!"GET".equalsIgnoreCase(req.getMethod())) {
                respondError(resp, 405, "Method Not Allowed");
                return;
            }
            String subPrefix = switch (appName) {
                case "backend_GM" -> "GameMaster";
                case "backend_SCADA" -> "HMI.SCADA";
                default -> throw new IllegalArgumentException("appName should be backend_GM or backend_SCADA");
            };
            String suffix = target.substring("/sub/".length());
            LOGGER.info("Retaining {}", suffix);

            AsyncContext async = req.startAsync();
            async.setTimeout(0);
            respondSse(resp);
            bridge.register(subPrefix + "." + sanitizeNatsTopicName(suffix), sseClient(resp));
            clients.add(new SseTopicSubscriber(async, resp, telemetryConsumer, suffix));
        }
    }

    // TODO: move endpoint to game master backend once SCADA has alarms
    @Path("/sub-dynawo-constraints")
    class SubDynawoConstraintsHandler extends RouteHandler {
        @Override public String path() { return "/sub-dynawo-constraints"; }

        @GET
        @Tag(name = "Streaming")
        @Operation(summary = "Subscribe to Dynawo constraints via SSE")
        @ApiResponse(responseCode = "200", description = "SSE stream of Dynawo constraint events")
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
            bridge.register("Dynawo.Constraints", sseClient(resp));
        }
    }

    @Path("/sub-scada-commands")
    class SubScadaCommandsHandler extends RouteHandler {
        @Override public String path() { return "/sub-scada-commands"; }

        @GET
        @Tag(name = "Streaming")
        @Operation(summary = "Subscribe to SCADA commands via SSE")
        @ApiResponse(responseCode = "200", description = "SSE stream of SCADA commands")
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
            bridge.register("HMIControl.>", sseClient(resp));
        }
    }

    @Path("/time")
    class TimeHandler extends RouteHandler {
        @Override public String path() { return "/time"; }

        @GET
        @Tag(name = "Streaming")
        @Operation(summary = "Subscribe to simulation time via SSE")
        @ApiResponse(responseCode = "200", description = "SSE stream of time updates")
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
            bridge.register("time", sseClient(resp));
        }
    }

    @Path("/init-clock-time")
    class InitClockTimeHandler extends RouteHandler {
        @Override public String path() { return "/init-clock-time"; }

        @GET
        @Tag(name = "Common")
        @Operation(summary = "Get the initial simulation clock time")
        @ApiResponse(responseCode = "200", description = "Initial clock time as JSON")
        @ApiResponse(responseCode = "500", description = "No response from orchestrator")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if (!"GET".equalsIgnoreCase(req.getMethod())) {
                respondError(resp, 405, "Method Not Allowed");
                return;
            }
            Message reply = conn.request(
                orchestratorControlTopic() + "." + appName,
                "{\"command\": \"get_initial_clock_time\"}".getBytes(StandardCharsets.UTF_8),
                Duration.ofSeconds(10)
            );
            if (reply == null) {
                throw new IOException("No response from Orchestrator");
            }
            respondjson(resp, 200, new String(reply.getData(), StandardCharsets.UTF_8));
        }
    }

    @Path("/history/{topic}")
    class HistoryHandler extends RouteHandler {
        @Override public String path() { return "/history"; }

        @GET
        @Tag(name = "History")
        @Operation(summary = "Query historical data for a topic")
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
            String topic = target.substring("/history/".length());

            Map<String, String> params = splitQuery(req.getQueryString());
            double min = Double.parseDouble(params.get("min"));
            double max = Double.parseDouble(params.get("max"));

            String json = clickhouseClient.queryHistory(Optional.of(topic), min, max);
            respondjson(resp, 200, json);
        }
    }

    // TODO: move endpoint to game master backend once SCADA has alarms
    @Path("/history-dynawo-constraints")
    class HistoryDynawoConstraintsHandler extends RouteHandler {
        @Override public String path() { return "/history-dynawo-constraints"; }

        @GET
        @Tag(name = "History")
        @Operation(summary = "Query historical Dynawo constraints")
        @Parameter(name = "min", in = ParameterIn.QUERY, required = true, description = "Start of time range")
        @Parameter(name = "max", in = ParameterIn.QUERY, required = true, description = "End of time range")
        @ApiResponse(responseCode = "200", description = "JSON array of Dynawo constraint history")
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
                respondjson(resp, 200, clickhouseClient.queryDynawoConstraints(min, max));
            } catch (NumberFormatException e) {
                respondError(resp, 400, "Invalid min/max parameters");
            }
        }
    }

    @Path("/history-scada-commands")
    class HistoryScadaCommandsHandler extends RouteHandler {
        @Override public String path() { return "/history-scada-commands"; }

        @GET
        @Tag(name = "History")
        @Operation(summary = "Query historical commands sent from SCADA clients")
        @Parameter(name = "min", in = ParameterIn.QUERY, required = true, description = "Start of time range")
        @Parameter(name = "max", in = ParameterIn.QUERY, required = true, description = "End of time range")
        @ApiResponse(responseCode = "200", description = "JSON array of SCADA commands (time, command, command_source)")
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
                respondjson(resp, 200, clickhouseClient.queryScadaCommands(min, max));
            } catch (NumberFormatException e) {
                respondError(resp, 400, "Invalid min/max parameters");
            }
        }
    }

    @Path("/control-batch-check")
    class ControlBatchCheckHandler extends RouteHandler {
        @Override public String path() { return "/control-batch-check"; }

        @POST
        @Tag(name = "Control")
        @Operation(summary = "Batch check controllability for multiple equipment/column pairs")
        @ApiResponse(responseCode = "200", description = "Map of equipmentId -> set of controllable columns")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if (!"POST".equalsIgnoreCase(req.getMethod())) {
                respondError(resp, 405, "Method Not Allowed");
                return;
            }
            // Input: { "equipmentIds": ["id1","id2"], "columns": ["col1","col2"] }
            JsonNode body = MAPPER.readTree(req.getInputStream());
            List<String> equipmentIds = MAPPER.convertValue(body.get("equipmentIds"), new TypeReference<>() {});
            List<String> columns = MAPPER.convertValue(body.get("columns"), new TypeReference<>() {});

            // Result: { "id1": ["col1"], "id2": ["col1", "col2"], ... }
            Map<String, List<String>> result = new LinkedHashMap<>();
            for (String equipmentId : equipmentIds) {
                List<String> controllable = new ArrayList<>();
                for (String column : columns) {
                    if (controlSender.isControllable(equipmentId, column)) {
                        controllable.add(column);
                    }
                }
                if (!controllable.isEmpty()) result.put(equipmentId, controllable);
            }
            respondjson(resp, 200, MAPPER.writeValueAsString(result));
        }
    }

    @Path("/control/{equipmentId}/{kind}/{value}")
    class ControlPostHandler extends RouteHandler {
        @Override public String path() { return "/control"; }

        @POST
        @Tag(name = "Control")
        @Operation(summary = "Send a control command to an iidm element")
        @Parameter(name = "equipmentId", in = ParameterIn.PATH, required = true, description = "Equipment ID")
        @Parameter(name = "kind", in = ParameterIn.PATH, required = true, description = "Control kind")
        @Parameter(name = "value", in = ParameterIn.PATH, required = true, description = "Control value (numeric or boolean)")
        @Parameter(name = "requester", in = ParameterIn.QUERY, required = true, description = "Requester identifier")
        @ApiResponse(responseCode = "200", description = "OK")
        @ApiResponse(responseCode = "400", description = "Invalid path or missing parameters")
        @ApiResponse(responseCode = "404", description = "Equipment not found")
        @ApiResponse(responseCode = "504", description = "Control timed out")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if (!"POST".equalsIgnoreCase(req.getMethod())) {
                respondError(resp, 405, "Method Not Allowed");
                return;
            }
            String[] parts = target.split("/", -1);
            if (parts.length < 5) {
                respondError(resp, 400, "Invalid path");
                return;
            }
            String equipmentId = parts[2];
            String kind = parts[3];
            String valueString = parts[4];

            Map<String, String> query = splitQuery(req.getQueryString());
            String requester = query.get("requester");
            if (requester == null || requester.isEmpty()) {
                respondError(resp, 400, "Missing requester");
                return;
            }

            Value value = Value.parse(valueString);
            if (value == null) {
                respondError(resp, 400, "value must be numeric or boolean (" + parts[4] + " given)");
                return;
            }
            try {
                controlSender.sendControl(equipmentId, kind, value, requester);
                respondjson(resp, 200, "{}");
            } catch (NoSuchElementException e) {
                respondError(resp, 404, e.getMessage());
            } catch (TimeoutException e) {
                respondError(resp, 504, e.getMessage());
            }
        }
    }

    @Path("/control-raw/{id}/{value}")
    class RawControlPostHandler extends RouteHandler {
        @Override public String path() { return "/control-raw"; }

        @POST
        @Tag(name = "Control")
        @Operation(summary = "Send a control command")
        @Parameter(name = "id", in = ParameterIn.PATH, required = true, description = "Element ID")
        @Parameter(name = "value", in = ParameterIn.PATH, required = true, description = "Control value (numeric or boolean)")
        @Parameter(name = "requester", in = ParameterIn.QUERY, required = true, description = "Requester identifier")
        @ApiResponse(responseCode = "200", description = "OK")
        @ApiResponse(responseCode = "400", description = "Invalid path or missing parameters")
        @ApiResponse(responseCode = "504", description = "Control timed out")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if (!"POST".equalsIgnoreCase(req.getMethod())) {
                respondError(resp, 405, "Method Not Allowed");
                return;
            }
            String[] parts = target.split("/", -1);
            if (parts.length < 4) {
                respondError(resp, 400, "Invalid path");
                return;
            }
            String id = parts[2];
            String valueString = parts[3];

            Map<String, String> query = splitQuery(req.getQueryString());
            String requester = query.get("requester");
            if (requester == null || requester.isEmpty()) {
                respondError(resp, 400, "Missing requester");
                return;
            }

            Value value = Value.parse(valueString);
            if (value == null) {
                respondError(resp, 400, "value must be numeric or boolean (" + parts[3] + " given)");
                return;
            }
            try {
                controlSender.sendControl(id, value, requester);
                respondjson(resp, 200, "{}");
            } catch (NoSuchElementException e) {
                respondError(resp, 404, e.getMessage());
            } catch (TimeoutException e) {
                respondError(resp, 504, e.getMessage());
            }
        }
    }

    // -------------------------------------------------------------------------
    // Information flow model
    // -------------------------------------------------------------------------

    @Path("/get-link-characteristics")
    class GetLinkCharacteristicsHandler extends RouteHandler {
        @Override public String path() { return "/get-link-characteristics"; }

        @GET
        @Tag(name = "Information Flow")
        @Operation(summary = "Get characteristics of a link between two nodes")
        @Parameter(name = "from", in = ParameterIn.QUERY, required = true, description = "Source node name")
        @Parameter(name = "to", in = ParameterIn.QUERY, required = true, description = "Destination node name")
        @Parameter(name = "requester", in = ParameterIn.QUERY, required = true, description = "Requester identifier")
        @ApiResponse(responseCode = "200", description = "Link characteristics as JSON")
        @ApiResponse(responseCode = "400", description = "Missing parameters")
        @ApiResponse(responseCode = "500", description = "No response from the Orchestrator")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if (!"GET".equalsIgnoreCase(req.getMethod())) {
                respondError(resp, 405, "Method Not Allowed");
                return;
            }
            Map<String, String> params = splitQuery(req.getQueryString());
            String from = getRequiredParam(params, "from", resp); if (from == null) return;
            String to = getRequiredParam(params, "to", resp); if (to == null) return;
            String requester = getRequiredParam(params, "requester", resp); if (requester == null) return;
            JsonNode scenario = MAPPER.valueToTree(Map.of(
                "command", "get_link_characteristics",
                "link", Map.of("from", from, "to", to)
            ));
            JsonNode reply = requestOrchestratorControl(requester, scenario);
            JsonNode status = reply.get("status");
            if (status != null && "OK".equals(status.asText())) {
                respondjson(resp, 200, MAPPER.writeValueAsString(reply.get("reply")));
            } else {
                respondjson(resp, 500, MAPPER.writeValueAsString(reply));
            }
        }
    }

    @Path("/get-node-characteristics")
    class GetNodeCharacteristicsHandler extends RouteHandler {
        @Override public String path() { return "/get-node-characteristics"; }

        @GET
        @Tag(name = "Information Flow")
        @Operation(summary = "Get characteristics of a node")
        @Parameter(name = "node", in = ParameterIn.QUERY, required = true, description = "Node name")
        @Parameter(name = "requester", in = ParameterIn.QUERY, required = true, description = "Requester identifier")
        @ApiResponse(responseCode = "200", description = "Node characteristics as JSON")
        @ApiResponse(responseCode = "400", description = "Missing parameters")
        @ApiResponse(responseCode = "500", description = "No response from the Orchestrator")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if (!"GET".equalsIgnoreCase(req.getMethod())) {
                respondError(resp, 405, "Method Not Allowed");
                return;
            }
            Map<String, String> params = splitQuery(req.getQueryString());
            String node = getRequiredParam(params, "node", resp); if (node == null) return;
            String requester = getRequiredParam(params, "requester", resp); if (requester == null) return;
            JsonNode scenario = MAPPER.valueToTree(Map.of(
                "command", "get_node_characteristics",
                "node", node
            ));
            JsonNode reply = requestOrchestratorControl(requester, scenario);
            JsonNode status = reply.get("status");
            if (status != null && "OK".equals(status.asText())) {
                respondjson(resp, 200, MAPPER.writeValueAsString(reply.get("reply")));
            } else {
                respondjson(resp, 500, MAPPER.writeValueAsString(reply));
            }
        }
    }

    @Path("/get-path-characteristics")
    class GetPathCharacteristicsHandler extends RouteHandler {
        @Override public String path() { return "/get-path-characteristics"; }

        @GET
        @Tag(name = "Information Flow")
        @Operation(summary = "Get characteristics of a path between source and destination")
        @Parameter(name = "source", in = ParameterIn.QUERY, required = true, description = "Source node name")
        @Parameter(name = "destination", in = ParameterIn.QUERY, required = true, description = "Destination node name")
        @Parameter(name = "requester", in = ParameterIn.QUERY, required = true, description = "Requester identifier")
        @ApiResponse(responseCode = "200", description = "Path characteristics as JSON")
        @ApiResponse(responseCode = "400", description = "Missing parameters")
        @ApiResponse(responseCode = "500", description = "No response from the Orchestrator")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if (!"GET".equalsIgnoreCase(req.getMethod())) {
                respondError(resp, 405, "Method Not Allowed");
                return;
            }
            Map<String, String> params = splitQuery(req.getQueryString());
            String source = getRequiredParam(params, "source", resp); if (source == null) return;
            String destination = getRequiredParam(params, "destination", resp); if (destination == null) return;
            String requester = getRequiredParam(params, "requester", resp); if (requester == null) return;
            JsonNode scenario = MAPPER.valueToTree(Map.of(
                "command", "get_path_characteristics",
                "source", source,
                "destination", destination
            ));
            JsonNode reply = requestOrchestratorControl(requester, scenario);
            JsonNode status = reply.get("status");
            if (status != null && "OK".equals(status.asText())) {
                respondjson(resp, 200, MAPPER.writeValueAsString(reply.get("reply")));
            } else {
                respondjson(resp, 500, MAPPER.writeValueAsString(reply));
            }
        }
    }

    @Path("/ifl-graph")
    class IflGraphHandler extends RouteHandler {
        @Override public String path() { return "/ifl-graph"; }

        @GET
        @Tag(name = "Information Flow")
        @Operation(summary = "Get information flow graph as SVG")
        @Parameter(name = "nodes", in = ParameterIn.QUERY, required = false, description = "Comma-separated list of node IDs to focus on (whole network if not specified)")
        @Parameter(name = "depth", in = ParameterIn.QUERY, required = false, description = "Number of hops around selected nodes to include (default 0)")
        @ApiResponse(responseCode = "200", description = "SVG of the information flow graph as JSON {svg_content: string}")
        @ApiResponse(responseCode = "400", description = "Invalid parameters")
        @ApiResponse(responseCode = "500", description = "Internal error")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            try {
                if (!"GET".equalsIgnoreCase(req.getMethod())) {
                    respondError(resp, 405, "Method Not Allowed");
                    return;
                }

                String nodesParam = req.getParameter("nodes");
                Optional<Set<String>> selectedNodeIds = (nodesParam != null && !nodesParam.isBlank())
                    ? Optional.of(new HashSet<>(Arrays.asList(nodesParam.split(","))))
                    : Optional.empty();

                int depth = 0;
                String depthParam = req.getParameter("depth");
                if (depthParam != null && !depthParam.isBlank()) {
                    try {
                        depth = Integer.parseInt(depthParam);
                    } catch (NumberFormatException e) {
                        respondError(resp, 400, "Invalid depth parameter: " + depthParam);
                        return;
                    }
                }

                InformationFlowModelLayout.LayoutResult layout = InformationFlowModelLayout.compute(selectedNodeIds, depth);
                String svg = SvgRenderer.render(layout);
                respondjson(resp, 200, MAPPER.writeValueAsString(Map.of("svg_content", svg)));
            } catch (IllegalArgumentException e) {
                respondError(resp, 400, e.getMessage());
            }
        }
    }

    @Path("/ifl-nodes")
    class IflNodesHandler extends RouteHandler {
        @Override public String path() { return "/ifl-nodes"; }

        @GET
        @Tag(name = "Information Flow")
        @Operation(summary = "Get list of all nodes in the information flow graph")
        @ApiResponse(responseCode = "200", description = "JSON array of node IDs")
        @Override
        public void handle(String target, HttpServletRequest req, HttpServletResponse resp) throws Exception {
            addCorsHeaders(resp);
            if (!"GET".equalsIgnoreCase(req.getMethod())) {
                respondError(resp, 405, "Method Not Allowed");
                return;
            }
            respondjson(resp, 200, MAPPER.writeValueAsString(InformationFlowModelLayout.getNodeIds()));
        }
    }

    protected static void respondError(HttpServletResponse resp, int status, String message) throws IOException {
        ObjectMapper m = new ObjectMapper();
        respondjson(resp, status, m.writeValueAsString(Map.of("error", message != null ? message : "Unknown error")));
    }

    protected static void respondjson(HttpServletResponse resp, int status, String body) throws IOException {
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        resp.setStatus(status);
        resp.setContentType("application/json; charset=utf-8");
        resp.setContentLength(bytes.length);
        resp.getOutputStream().write(bytes);
    }

    protected static void respondXml(HttpServletResponse resp, int status, MemDataSource mds) throws IOException {
        byte[] data = mds.getData(".xiidm");
        resp.setStatus(status);
        resp.setContentType("application/xml; charset=utf-8");
        resp.setContentLength(data.length);
        resp.getOutputStream().write(data);
    }

    protected static void respondSse(HttpServletResponse resp) throws IOException {
        resp.setStatus(200);
        resp.setContentType("text/event-stream");
        resp.addHeader("Cache-Control", "no-cache");
        resp.addHeader("X-Accel-Buffering", "no");
    }

    protected static Map<String, String> splitQuery(String queryString) {
        Map<String, String> queryPairs = new HashMap<>();
        if (queryString == null) return queryPairs;
        for (String pair : queryString.split("&")) {
            String[] parts = pair.split("=", 2);
            if (parts.length == 2) queryPairs.put(
                URLDecoder.decode(parts[0], StandardCharsets.UTF_8),
                URLDecoder.decode(parts[1], StandardCharsets.UTF_8)
            );
        }
        return queryPairs;
    }

    protected String getRequiredParam(Map<String, String> params, String name, HttpServletResponse resp) throws IOException {
        // params comes from splitQuery(), which already decodes both keys and values
        String value = params.get(name);
        if (value == null || value.isEmpty()) {
            respondError(resp, 400, "Missing " + name);
            return null;
        }
        return value;
    }

    protected JsonNode requestOrchestratorControl(String requester, JsonNode scenarioJson) throws Exception {
        Message reply = conn.request(
            orchestratorControlTopic() + "." + requester,
            MAPPER.writeValueAsBytes(scenarioJson),
            Duration.ofSeconds(10)
        );
        if (reply == null) throw new IOException("No response from the Orchestrator");
        return MAPPER.readTree(reply.getData());
    }

    protected static void addCorsHeaders(HttpServletResponse resp) {
        resp.addHeader("Access-Control-Allow-Origin", "*");
        resp.addHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
        resp.addHeader("Access-Control-Allow-Headers", "Content-Type");
    }

    public static String sanitizeNatsTopicName(String topic) {
        if (topic == null) return null;

        char[] chars = topic.toCharArray();

        for (int i = 0; i < chars.length; i++) {
            switch (chars[i]) {
                case '\0': // null
                case ' ':  // space
                case '.':  // dot
                case '*':  // wildcard
                case '>':  // wildcard
                    chars[i] = '_';
                    break;
                default:
                    // keep as is
                    break;
            }
        }

        return new String(chars);
    }

    protected MemDataSource writeIidm(Network network) {
        MemDataSource ds = new MemDataSource();
        ZonedDateTime now = ZonedDateTime.now();
        DateTimeFormatter format = DateTimeFormatter.ofPattern("yyyyMMdd.HHmmss");
        String dateFormatee = "TwinCR-snapshot-" + now.format(format);
        Properties props = null;

        if (iidmVersion != null) {
            props = new Properties();
            props.setProperty("iidm.export.xml.version", iidmVersion);
        }
        synchronized (network) {
            network.setCaseDate(now);
            network.setName(dateFormatee);
            network.write("XIIDM", props, ds);
        }
        return ds;
    }

    private static class SseTopicSubscriber {
        private final AsyncContext async;
        private final OutputStream os;
        private final TelemetryConsumerCommon telemetryConsumer;
        private final String topic;

        SseTopicSubscriber(AsyncContext async, HttpServletResponse resp,
                           TelemetryConsumerCommon telemetryConsumer, String topic) throws IOException {
            this.async = async;
            this.os = resp.getOutputStream();
            this.topic = topic;
            this.telemetryConsumer = telemetryConsumer;
            LOGGER.debug("Acquiring {} for SSE client", topic);
            telemetryConsumer.acquireSubTopic(topic);
        }

        void sendKeepAlive() throws IOException {
            os.write(":keepalive\n\n".getBytes(StandardCharsets.UTF_8));
            os.flush();
        }

        void close() {
            try { os.close(); } catch (IOException ignored) {}
            try { async.complete(); } catch (IllegalStateException ignored) {}
            LOGGER.debug("Releasing {} after SSE client disconnection", topic);
            telemetryConsumer.releaseSubTopic(topic);
        }
    }

    protected static SseClient sseClient(HttpServletResponse resp) {
        // SSE must follow format "data: <payload>\n\n"
        return data -> {
            OutputStream os = resp.getOutputStream();
            os.write(("data: " + data + "\n\n").getBytes(StandardCharsets.UTF_8));
            os.flush();
        };
    }

    protected boolean showMeasurementsOnSld() {
        return false;
    }

    protected com.powsybl.sld.svg.LegendWriterFactory getSldLegendWriterFactory() {
        return (network, svgParameters) -> new com.powsybl.sld.svg.DefaultSVGLegendWriter(network, svgParameters);
    }

    protected com.powsybl.sld.svg.styles.StyleProviderFactory getSldStyleProviderFactory() {
        return (network, svgParameters) -> new StyleProvidersList(
            new DefaultStyleProviderFactory().create(network, svgParameters),
            controllableSwitchStyleProvider
        );
    }

    protected abstract String orchestratorControlTopic();
}
