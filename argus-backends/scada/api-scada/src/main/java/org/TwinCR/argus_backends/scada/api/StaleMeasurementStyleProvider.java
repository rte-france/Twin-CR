/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.scada.api;

import java.util.List;

import com.powsybl.sld.library.SldComponentLibrary;
import com.powsybl.sld.model.cells.Cell;
import com.powsybl.sld.model.graphs.Graph;
import com.powsybl.sld.model.graphs.VoltageLevelGraph;
import com.powsybl.sld.model.nodes.BranchEdge;
import com.powsybl.sld.model.nodes.Edge;
import com.powsybl.sld.model.nodes.Node;
import com.powsybl.sld.svg.BusInfo;
import com.powsybl.sld.svg.BusLegendInfo;
import com.powsybl.sld.svg.FeederInfo;
import com.powsybl.sld.svg.LabelProvider;
import com.powsybl.sld.svg.styles.StyleProvider;

import org.TwinCR.argus_backends.scada.telemetry.TelemetryConsumer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Style provider coloring in blue the labels of measurements which have not been
 * refreshed for a configurable amount of time.
 *
 * @author Olivier Bretteville <olivier.bretteville at rte-france.com>
 */
public class StaleMeasurementStyleProvider implements StyleProvider {
    private static final Logger LOGGER = LoggerFactory.getLogger(StaleMeasurementStyleProvider.class);
    public static final String STALE_MEASUREMENT_STYLE_CLASS = "sld-stale-measurement";
    private static final String CSS_FILE = "stale-measurement.css";

    private final TelemetryConsumer telemetryConsumer;
    private final double staleTimeout;

    public StaleMeasurementStyleProvider(TelemetryConsumer telemetryConsumer, double staleTimeout) {
        this.telemetryConsumer = telemetryConsumer;
        this.staleTimeout = staleTimeout;
    }

    @Override
    public List<String> getFeederInfoStyles(FeederInfo info) {
        String measurementId = info.getUserDefinedId();
        if (measurementId == null) {
            return List.of();
        }
        if (telemetryConsumer.isMeasurementStale(measurementId, staleTimeout)) {
            LOGGER.info("Measurement {} is stale (older than {} seconds)", measurementId, Double.toString(staleTimeout));
            return List.of(STALE_MEASUREMENT_STYLE_CLASS);
        }
        return List.of();
    }

    @Override public List<String> getEdgeStyles(Graph graph, Edge edge) { return List.of(); }
    @Override public List<String> getNodeStyles(VoltageLevelGraph graph, Node node, SldComponentLibrary componentLibrary, boolean showInternalNodes) { return List.of(); }
    @Override public List<String> getNodeDecoratorStyles(LabelProvider.NodeDecorator nodeDecorator, Node node, SldComponentLibrary componentLibrary) { return List.of(); }
    @Override public List<String> getBranchEdgeStyles(BranchEdge edge, SldComponentLibrary componentLibrary) { return List.of(); }
    @Override public List<String> getNodeSubcomponentStyles(Graph graph, Node node, String subComponentName) { return List.of(); }
    @Override public List<String> getCssFilenames() { return List.of(CSS_FILE); }
    @Override public List<String> getBusStyles(String busId, VoltageLevelGraph graph) { return List.of(); }
    @Override public List<String> getBusInfoStyle(BusInfo info) { return List.of(); }
    @Override public List<String> getBusLegendCaptionStyles(BusLegendInfo.Caption caption) { return List.of(); }
    @Override public List<String> getCellStyles(Cell cell) { return List.of(); }
    @Override public void reset() {}
}