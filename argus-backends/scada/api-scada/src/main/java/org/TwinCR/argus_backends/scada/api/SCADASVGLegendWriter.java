/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.scada.api;

import com.powsybl.iidm.network.Network;
import com.powsybl.iidm.network.VoltageLevel;
import com.powsybl.sld.model.graphs.VoltageLevelGraph;
import com.powsybl.sld.svg.BusLegendInfo;
import com.powsybl.sld.svg.DefaultSVGLegendWriter;
import com.powsybl.sld.svg.GraphMetadata;
import com.powsybl.sld.svg.SvgParameters;
import com.powsybl.sld.svg.styles.StyleClassConstants;
import com.powsybl.sld.svg.styles.StyleProvider;
import com.powsybl.sld.util.IdUtil;
import org.TwinCR.argus_backends.scada.telemetry.TelemetryConsumer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.w3c.dom.Element;
import org.w3c.dom.Text;

import java.util.List;

import static com.powsybl.diagram.util.CssUtil.writeStyleClasses;
import static com.powsybl.sld.svg.SVGWriter.GROUP;

/*
    Specialized SVGLegendWriter for SCADA voltage level display.
    A gauge showing time elapsed since last state estimation is displayed before nodes legend.

    @author Olivier Bretteville <olivier.bretteville at rte-france.com>
*/
public class SCADASVGLegendWriter extends DefaultSVGLegendWriter {
    private static final Logger LOGGER = LoggerFactory.getLogger(SCADASVGLegendWriter.class);

    protected static final int CIRCLE_RADIUS_NODE_INFOS_SIZE = 10;

    protected TelemetryConsumer telemetryConsumer;

    public SCADASVGLegendWriter(Network net, SvgParameters svgParameters, TelemetryConsumer telemetryConsumer) {
        super(net, svgParameters);
        this.telemetryConsumer = telemetryConsumer;
    }

    protected List<BusLegendInfo> getBusLegendInfos(VoltageLevelGraph graph) {
        VoltageLevel vl = network.getVoltageLevel(graph.getVoltageLevelInfos().id());
        return vl.getBusView().getBusStream()
                .map(b -> new BusLegendInfo(b.getId(), List.of(
                        new BusLegendInfo.Caption(valueFormatter.formatVoltage(b.getV(), "kV"), "v"),
                        new BusLegendInfo.Caption(valueFormatter.formatAngleInDegrees(b.getAngle()), "angle"),
                        new BusLegendInfo.Caption(valueFormatter.formatPower(b.getFictitiousP0(), "MW fict."), "p"),
                        new BusLegendInfo.Caption(valueFormatter.formatPower(b.getFictitiousQ0(), "MVar fict."), "q")
                )))
                .toList();
    }

    public void drawGauge(VoltageLevelGraph graph, GraphMetadata metadata, StyleProvider styleProvider, Element legendRootElement, double xShift, double yShift) {
        final int GAUGE_WIDTH=80;

        Element rectBackground = legendRootElement.getOwnerDocument().createElementNS("http://www.w3.org/2000/svg", "rect");
        rectBackground.setAttribute("x", String.valueOf(xShift));
        rectBackground.setAttribute("y", String.valueOf(yShift));
        rectBackground.setAttribute("width", String.format("%d", GAUGE_WIDTH));
        rectBackground.setAttribute("height", "10");
        rectBackground.setAttribute("rx", "5");
        rectBackground.setAttribute("fill", "#e0e0e0");
        legendRootElement.appendChild(rectBackground);

        Element rectProgressBar = legendRootElement.getOwnerDocument().createElementNS("http://www.w3.org/2000/svg", "rect");
        rectProgressBar.setAttribute("x", String.valueOf(xShift));
        rectProgressBar.setAttribute("y", String.valueOf(yShift));
        double percentage = telemetryConsumer.getProportionBeforeNextEstim();
        double width = percentage * ((double) GAUGE_WIDTH);
        rectProgressBar.setAttribute("width", String.format("%d", (int) width));
        rectProgressBar.setAttribute("height", "10");
        rectProgressBar.setAttribute("rx", "5");
        rectProgressBar.setAttribute("fill", "#0a702f");
        legendRootElement.appendChild(rectProgressBar);

        Element textPercentage = legendRootElement.getOwnerDocument().createElementNS("http://www.w3.org/2000/svg", "text");
        textPercentage.setAttribute("x", String.valueOf(xShift+50.0));
        textPercentage.setAttribute("y", String.valueOf(yShift+5.0));
        textPercentage.setAttribute("font-family", "Arial, sans-serif");
        textPercentage.setAttribute("font-size", "5");
        textPercentage.setAttribute("font-weight", "bold");
        textPercentage.setAttribute("fill", "#000000");
        textPercentage.setAttribute("text-anchor", "middle");
        textPercentage.setAttribute("dominant-baseline", "central");
        double seconds = telemetryConsumer.getSecondsSinceLastEstimTime();
        textPercentage.setTextContent(String.format("%d seconds ago", (int) seconds));
        legendRootElement.appendChild(textPercentage);

        LOGGER.debug("SLD legend updated with percentage= " + percentage + " and seconds= " + seconds);
    }

    public void drawLegend(VoltageLevelGraph graph, GraphMetadata metadata, StyleProvider styleProvider, Element legendRootElement, double positionX, double positionY) {
        double shiftX = positionX;

        // First we draw the gauge
        drawGauge(graph, metadata, styleProvider, legendRootElement, positionX, positionY-CIRCLE_RADIUS_NODE_INFOS_SIZE/2);
        shiftX += 140;

        // Then the "usual" legend
        for (BusLegendInfo busLegendInfo : getBusLegendInfos(graph)) {
            String idNode = metadata.getSvgParameters().getPrefixId() + "NODE_" + busLegendInfo.busId();
            String escapedIdNode = IdUtil.escapeId(idNode);
            Element gNode = legendRootElement.getOwnerDocument().createElement(GROUP);
            gNode.setAttribute("id", escapedIdNode);

            drawBusLegendInfo(busLegendInfo, shiftX, positionY, gNode, idNode, graph, styleProvider);

            legendRootElement.appendChild(gNode);

            shiftX += 2 * CIRCLE_RADIUS_NODE_INFOS_SIZE + 50;
        }
    }

    private void drawBusLegendInfo(BusLegendInfo busLegendInfo, double xShift, double yShift,
                                   Element g, String idNode, VoltageLevelGraph graph, StyleProvider styleProvider) {

        Element circle = g.getOwnerDocument().createElement("circle");

        // colored circle
        circle.setAttribute("id", IdUtil.escapeId(idNode + "_circle"));
        circle.setAttribute("cx", String.valueOf(xShift));
        circle.setAttribute("cy", String.valueOf(yShift));
        circle.setAttribute("r", String.valueOf(CIRCLE_RADIUS_NODE_INFOS_SIZE));
        circle.setAttribute("stroke-width", String.valueOf(CIRCLE_RADIUS_NODE_INFOS_SIZE));
        writeStyleClasses(circle, styleProvider.getBusStyles(busLegendInfo.busId(), graph));
        g.appendChild(circle);

        // legend nodes
        double padding = 2.0;
        for (BusLegendInfo.Caption caption : busLegendInfo.captions()) {
            Element label = g.getOwnerDocument().createElement("text");
            writeStyleClasses(label, styleProvider.getBusLegendCaptionStyles(caption), StyleClassConstants.BUS_LEGEND_INFO);
            label.setAttribute("id", IdUtil.escapeId(idNode + "_" + caption.type()));
            label.setAttribute("x", String.valueOf(xShift - CIRCLE_RADIUS_NODE_INFOS_SIZE));
            label.setAttribute("y", String.valueOf(yShift + padding * CIRCLE_RADIUS_NODE_INFOS_SIZE));
            Text textNode = g.getOwnerDocument().createTextNode(caption.label());
            label.appendChild(textNode);
            g.appendChild(label);

            padding += 1.0;
        }
    }
}
