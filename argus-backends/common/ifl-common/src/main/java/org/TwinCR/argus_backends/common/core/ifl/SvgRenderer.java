/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.common.core.ifl;

import org.TwinCR.argus_backends.common.core.ifl.InformationFlowModelLayout.LayoutResult;

public class SvgRenderer {

    private static final int WIDTH     = 1200;
    private static final int HEIGHT    = 800;
    private static final int FONT_SIZE = 10;

    public static String render(LayoutResult layout) {
        StringBuilder sb = new StringBuilder();

        sb.append("""
            <svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d">
            """.formatted(WIDTH, HEIGHT));

        for (Link link : layout.links()) {
            Node s = layout.nodes().get(link.from());
            Node t = layout.nodes().get(link.to());
            boolean bothHubs = s.degree > 1 && t.degree > 1;
            String color = bothHubs ? "orange" : "#999";
            sb.append("""
                <line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="1" data-from="%s" data-to="%s"/>
                """.formatted(s.x, s.y, t.x, t.y, color, escapeXml(link.from()), escapeXml(link.to())));
        }

        for (Node node : layout.nodes().values()) {
            boolean hub = node.degree > 1;
            double r = hub ? 10 : 5;
            double labelX = node.x + 0.2 * FONT_SIZE;
            if (node.cycosimNode) {
                double half = r/2;
                sb.append("""
                    <rect cx="%.2f" cy="%.2f" x="%.2f" y="%.2f" width="%.1f" height="%.1f" fill="red" stroke="red" stroke-width="1" base_r="%.1f" data-node="%s"/>
                    <text x="%.2f" y="%.2f" fill="white" font-size="%d" class="ifl-text-nodes">%s</text>
                    """.formatted(node.x, node.y, node.x - half, node.y - half, r, r, r, escapeXml(node.id), labelX, node.y, FONT_SIZE, escapeXml(node.id)));
            } else {
                String fill = hub ? "orange" : "steelblue";
                sb.append("""
                    <circle cx="%.2f" cy="%.2f" r="%.1f" fill="%s" base_r="%.1f" data-node="%s"/>
                    <text x="%.2f" y="%.2f" fill="white" font-size="%d" class="ifl-text-nodes">%s</text>
                    """.formatted(node.x, node.y, r, fill, r, escapeXml(node.id), labelX, node.y, FONT_SIZE, escapeXml(node.id)));
            }
        }

        sb.append("</svg>");
        return sb.toString();
    }

    private static String escapeXml(String s) {
        return s.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\"", "&quot;");
    }
}
