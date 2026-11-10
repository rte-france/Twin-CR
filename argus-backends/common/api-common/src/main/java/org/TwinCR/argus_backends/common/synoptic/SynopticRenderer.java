/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.common.synoptic;

import com.fasterxml.jackson.databind.JsonNode;
import com.powsybl.iidm.network.Connectable;
import com.powsybl.iidm.network.Identifiable;
import com.powsybl.iidm.network.Network;
import com.powsybl.iidm.network.Substation;
import com.powsybl.iidm.network.Terminal;
import com.powsybl.iidm.network.VoltageLevel;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Function;

/**
 * Renders a synoptic definition (see Twin-CR/tools/synoptic/README.md) to SVG, evaluating its expressions
 * on the current network state. Unknown / unmapped values are displayed as "?".
 */
public class SynopticRenderer {
    private static final Logger LOGGER = LoggerFactory.getLogger(SynopticRenderer.class);
    private static final String UNKNOWN = "?";

    private final JsonNode def;
    private final Map<String, SynopticExpression> expressions = new ConcurrentHashMap<>();
    private final Set<String> reportedErrors = ConcurrentHashMap.newKeySet();
    private volatile Set<String> topics;
    private final Locale locale;
    private final String[] nodeColors;
    private final String offColor;
    private final String unknownColor;
    private final String textColor;
    private final String valueColor;
    private final String unitOnColor;
    private final String arrowColor;
    private final String fontFamily;
    private final double fontSize;

    public SynopticRenderer(JsonNode def) {
        this.def = def;
        this.locale = Locale.forLanguageTag(def.path("locale").asText("en"));
        JsonNode palette = def.path("palette");
        List<String> nodes = new ArrayList<>();
        palette.path("nodes").forEach(n -> nodes.add(n.asText()));
        if (nodes.isEmpty()) {
            nodes.addAll(List.of("#ff2a2a", "#e8e8e8", "#38d038", "#ffb000", "#c05cff"));
        }
        this.nodeColors = nodes.toArray(String[]::new);
        this.offColor = palette.path("off").asText("#6f8586");
        this.unknownColor = palette.path("unknown").asText("#b08cd8");
        this.textColor = palette.path("text").asText("#ffffff");
        this.valueColor = palette.path("value").asText("#ff3030");
        this.unitOnColor = palette.path("unitOn").asText("#4a6cf0");
        this.arrowColor = palette.path("arrow").asText("#ffffff");
        this.fontFamily = def.path("fontFamily").asText("Arial, Helvetica, sans-serif");
        this.fontSize = def.path("fontSize").asDouble(14);
        // Fail fast on syntax errors, and warm the cache
        for (JsonNode e : def.path("elements")) {
            for (Map.Entry<String, JsonNode> field : e.properties()) {
                if (isExpressionField(field.getKey()) && field.getValue().isTextual()) {
                    expression(field.getValue().asText());
                }
            }
            for (JsonNode row : e.path("rows")) {
                if (row.path("expr").isTextual()) {
                    expression(row.path("expr").asText());
                }
            }
        }
    }

    private static boolean isExpressionField(String name) {
        return name.equals("expr") || name.equals("dir") || name.equals("on");
    }

    public String name() {
        return def.path("name").asText();
    }

    public String title() {
        return def.path("title").asText(name());
    }

    /**
     * Every quoted id used by the expressions and the branch/node elements, plus the border equipments of the
     * exchange('A', 'B') calls (to subscribe to their topics).
     */
    public Set<String> referencedIds(SynopticFunctions f) {
        Set<String> ids = new HashSet<>();
        List<List<String>> exchanges = new ArrayList<>();
        expressions.values().forEach(e -> {
            e.collectIds(ids);
            e.collectCalls("exchange", exchanges);
        });
        for (List<String> args : exchanges) {
            if (args.size() == 2 && args.get(0) != null && args.get(1) != null) {
                ids.addAll(f.borderEquipmentIds(args.get(0), args.get(1)));
            }
        }
        for (JsonNode e : def.path("elements")) {
            for (String key : List.of("branch", "vl", "equipment")) {
                if (e.path(key).isTextual()) {
                    ids.add(e.path(key).asText());
                }
            }
        }
        return ids;
    }

    /**
     * Telemetry topics to subscribe to for the live values of this synoptic: substations of the referenced equipments
     * (voltage levels, substations, connectables), topics of the out('id') outputs (outputTopic, GM).
     * Computed once: the definition and the network topology do not change after loading.
     */
    public Set<String> topics(Network network, Function<String, Optional<String>> outputTopic) {
        Set<String> cached = topics;
        if (cached != null) {
            return cached;
        }
        Set<String> found = new HashSet<>();
        synchronized (network) {
            for (String id : referencedIds(new SynopticFunctions(network))) {
                Identifiable<?> identifiable = network.getIdentifiable(id);
                if (identifiable == null) {
                    outputTopic.apply(id).ifPresent(found::add);
                } else if (identifiable instanceof VoltageLevel vl) {
                    vl.getSubstation().ifPresent(s -> found.add(s.getId()));
                } else if (identifiable instanceof Substation s) {
                    found.add(s.getId());
                } else if (identifiable instanceof Connectable<?> c) {
                    for (Terminal t : c.getTerminals()) {
                        t.getVoltageLevel().getSubstation().ifPresent(s -> found.add(s.getId()));
                    }
                }
            }
        }
        topics = Set.copyOf(found);
        return topics;
    }

    private SynopticExpression expression(String source) {
        return expressions.computeIfAbsent(source, SynopticExpression::parse);
    }

    private double eval(JsonNode exprNode, SynopticFunctions f) {
        if (exprNode == null || exprNode.isMissingNode() || exprNode.isNull()) {
            return Double.NaN;
        }
        if (exprNode.isNumber()) {
            return exprNode.asDouble();
        }
        String source = exprNode.asText();
        try {
            return expression(source).evaluate(f);
        } catch (RuntimeException e) {
            if (reportedErrors.add(source)) {
                LOGGER.warn("Synoptic {}: cannot evaluate '{}': {}", name(), source, e.getMessage());
            }
            return Double.NaN;
        }
    }

    private String format(double v, JsonNode e) {
        if (Double.isNaN(v) || Double.isInfinite(v)) {
            return UNKNOWN;
        }
        String fmt = e.path("format").asText("%.0f");
        String s = String.format(locale, fmt, v);
        if (s.matches("-0([.,]0*)?")) {
            s = s.substring(1);  // No "-0"
        }
        return e.path("prefix").asText("") + s + e.path("suffix").asText("");
    }

    // Color of a value from the optional "thresholds": [{"value": 9, "fill": "#ffa000"}, ...] (ascending)
    private String thresholdColor(double v, JsonNode e, String defaultColor) {
        String color = defaultColor;
        if (!Double.isNaN(v)) {
            for (JsonNode t : e.path("thresholds")) {
                if (v >= t.path("value").asDouble()) {
                    color = t.path("fill").asText(color);
                }
            }
        }
        return color;
    }

    private String nodeColor(double busIndex) {
        if (Double.isNaN(busIndex)) {
            return offColor;
        }
        return nodeColors[(int) busIndex % nodeColors.length];
    }

    public String render(SynopticFunctions f) {
        double width = def.path("width").asDouble(1000);
        double height = def.path("height").asDouble(1000);
        StringBuilder sb = new StringBuilder(1 << 20);
        sb.append("<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 ").append(num(width)).append(' ').append(num(height))
            .append("\" width=\"").append(num(width)).append("\" height=\"").append(num(height))
            .append("\" font-family=\"").append(esc(fontFamily)).append("\" font-size=\"").append(num(fontSize)).append("\">\n");
        sb.append("<rect class=\"synoptic-background\" x=\"0\" y=\"0\" width=\"").append(num(width)).append("\" height=\"").append(num(height))
            .append("\" fill=\"").append(esc(def.path("background").asText("#1c3f41"))).append("\"/>\n");

        // Draw order: decorations and branches below nodes, texts and values on top
        List<JsonNode> elements = new ArrayList<>();
        def.path("elements").forEach(elements::add);
        for (int pass = 0; pass < 3; pass++) {
            for (JsonNode e : elements) {
                String type = e.path("type").asText();
                int layer = switch (type) {
                    case "rect", "polyline", "branch" -> 0;
                    case "node", "unit", "arrow" -> 1;
                    default -> 2;
                };
                if (layer != pass) {
                    continue;
                }
                try {
                    switch (type) {
                        case "rect" -> rect(sb, e);
                        case "polyline" -> polyline(sb, e);
                        case "branch" -> branch(sb, e, f);
                        case "node" -> node(sb, e, f);
                        case "unit" -> unit(sb, e, f);
                        case "arrow" -> arrow(sb, e, f);
                        case "text" -> text(sb, e.path("x").asDouble(), e.path("y").asDouble(), e.path("text").asText(), e,
                            e.path("fill").asText(textColor));
                        case "value" -> value(sb, e, f);
                        case "table" -> table(sb, e, f);
                        default -> {
                            if (reportedErrors.add("type:" + type)) {
                                LOGGER.warn("Synoptic {}: unknown element type '{}'", name(), type);
                            }
                        }
                    }
                } catch (RuntimeException ex) {
                    if (reportedErrors.add("elem:" + e.path("id").asText(e.toString()))) {
                        LOGGER.warn("Synoptic {}: cannot render element {}: {}", name(), e.path("id").asText(type), ex.toString());
                    }
                }
            }
        }
        sb.append("</svg>\n");
        return sb.toString();
    }

    private void openGroup(StringBuilder sb, JsonNode e, String cssClass, SynopticFunctions f) {
        sb.append("<g class=\"").append(cssClass).append("\"");
        if (e.has("id")) {
            sb.append(" id=\"").append(esc(e.path("id").asText())).append("\"");
        }
        String equipment = equipmentId(e);
        if (equipment != null && f.exists(equipment)) {
            sb.append(" data-equipment=\"").append(esc(equipment)).append("\"");  // Context menu / properties in argus
        }
        sb.append(">");
        String tooltip = e.path("tooltip").asText(equipment == null ? "" : equipment);
        if (!tooltip.isEmpty()) {
            sb.append("<title>").append(esc(tooltip)).append("</title>");
        }
    }

    // Network equipment shown by an element: "equipment", else the "branch" / "vl" it draws
    private static String equipmentId(JsonNode e) {
        for (String key : List.of("equipment", "branch", "vl")) {
            if (e.path(key).isTextual() && !e.path(key).asText().isEmpty()) {
                return e.path(key).asText();
            }
        }
        return null;
    }

    private void rect(StringBuilder sb, JsonNode e) {
        sb.append("<rect x=\"").append(num(e.path("x").asDouble())).append("\" y=\"").append(num(e.path("y").asDouble()))
            .append("\" width=\"").append(num(e.path("w").asDouble())).append("\" height=\"").append(num(e.path("h").asDouble()))
            .append("\" rx=\"").append(num(e.path("rx").asDouble(4)))
            .append("\" fill=\"").append(esc(e.path("fill").asText("none")))
            .append("\" stroke=\"").append(esc(e.path("stroke").asText(textColor)))
            .append("\" stroke-width=\"").append(num(e.path("strokeWidth").asDouble(1))).append("\"/>\n");
    }

    private void polyline(StringBuilder sb, JsonNode e) {
        sb.append("<polyline points=\"").append(points(e.path("points"))).append("\" fill=\"none\" stroke=\"")
            .append(esc(e.path("stroke").asText(textColor))).append("\" stroke-width=\"").append(num(e.path("width").asDouble(1))).append("\"");
        if (e.has("dash")) {
            sb.append(" stroke-dasharray=\"").append(esc(e.path("dash").asText())).append("\"");
        }
        sb.append("/>\n");
    }

    private void branch(StringBuilder sb, JsonNode e, SynopticFunctions f) {
        String id = e.path("branch").asText(null);
        List<double[]> pts = pointList(e.path("points"));
        if (pts.size() < 2) {
            return;
        }
        double width = e.path("width").asDouble(2);
        String c1;
        String c2;
        boolean dashed1;
        boolean dashed2;
        if (id == null || f.terminal(id, 1) == null) {
            c1 = c2 = unknownColor;
            dashed1 = dashed2 = true;
        } else {
            int s1 = e.path("side1").asInt(1);  // Network side drawn at the first point
            double b1 = f.call(s1 == 1 ? "bus1" : "bus2", List.of(id));
            double b2 = f.call(s1 == 1 ? "bus2" : "bus1", List.of(id));
            c1 = nodeColor(b1);
            c2 = nodeColor(b2);
            dashed1 = Double.isNaN(b1);
            dashed2 = Double.isNaN(b2);
        }
        List<List<double[]>> halves = splitHalf(pts);
        openGroup(sb, e, "synoptic-branch", f);
        halfLine(sb, halves.get(0), c1, width, dashed1);
        halfLine(sb, halves.get(1), c2, width, dashed2);
        sb.append("</g>\n");
    }

    private void halfLine(StringBuilder sb, List<double[]> pts, String color, double width, boolean dashed) {
        sb.append("<polyline points=\"");
        for (double[] p : pts) {
            sb.append(num(p[0])).append(',').append(num(p[1])).append(' ');
        }
        sb.append("\" fill=\"none\" stroke=\"").append(esc(color)).append("\" stroke-width=\"").append(num(width)).append("\"");
        if (dashed) {
            sb.append(" stroke-dasharray=\"6,4\"");
        }
        sb.append("/>");
    }

    private static List<List<double[]>> splitHalf(List<double[]> pts) {
        double total = 0;
        for (int i = 1; i < pts.size(); i++) {
            total += Math.hypot(pts.get(i)[0] - pts.get(i - 1)[0], pts.get(i)[1] - pts.get(i - 1)[1]);
        }
        double half = total / 2;
        List<double[]> first = new ArrayList<>();
        List<double[]> second = new ArrayList<>();
        first.add(pts.get(0));
        double acc = 0;
        boolean split = false;
        for (int i = 1; i < pts.size(); i++) {
            double[] a = pts.get(i - 1);
            double[] b = pts.get(i);
            double seg = Math.hypot(b[0] - a[0], b[1] - a[1]);
            if (!split && acc + seg >= half) {
                double t = seg == 0 ? 0 : (half - acc) / seg;
                double[] m = {a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])};
                first.add(m);
                second.add(m);
                split = true;
            }
            (split ? second : first).add(b);
            acc += seg;
        }
        return List.of(first, second);
    }

    private void node(StringBuilder sb, JsonNode e, SynopticFunctions f) {
        String vl = e.path("vl").asText(null);
        double x = e.path("x").asDouble();
        double y = e.path("y").asDouble();
        double r = e.path("r").asDouble(12);
        double nbus = vl == null ? Double.NaN : f.call("nbus", List.of(vl));
        String color = Double.isNaN(nbus) ? unknownColor : (nbus == 0 ? offColor : nodeColors[0]);
        openGroup(sb, e, "synoptic-node", f);
        sb.append("<circle cx=\"").append(num(x)).append("\" cy=\"").append(num(y)).append("\" r=\"").append(num(r))
            .append("\" fill=\"").append(esc(e.path("fill").asText("none"))).append("\" stroke=\"").append(color)
            .append("\" stroke-width=\"").append(num(e.path("strokeWidth").asDouble(2))).append("\"/>");
        String inner = Double.isNaN(nbus) ? UNKNOWN : (nbus > 1 ? String.valueOf((int) nbus) : null);
        if (inner != null) {
            sb.append("<text x=\"").append(num(x)).append("\" y=\"").append(num(y)).append("\" text-anchor=\"middle\" dominant-baseline=\"central\" fill=\"")
                .append(color).append("\" font-size=\"").append(num(r * 1.4)).append("\">").append(inner).append("</text>");
        }
        sb.append("</g>\n");
    }

    private void unit(StringBuilder sb, JsonNode e, SynopticFunctions f) {
        double x = e.path("x").asDouble();
        double y = e.path("y").asDouble();
        double r = e.path("r").asDouble(12);
        double on = eval(e.get("on"), f);
        String fill = Double.isNaN(on) ? "none" : (on != 0 ? e.path("fill").asText(unitOnColor) : "none");
        String stroke = Double.isNaN(on) ? unknownColor : e.path("stroke").asText(nodeColors[0]);
        openGroup(sb, e, "synoptic-unit", f);
        sb.append("<circle cx=\"").append(num(x)).append("\" cy=\"").append(num(y)).append("\" r=\"").append(num(r))
            .append("\" fill=\"").append(esc(fill)).append("\" stroke=\"").append(esc(stroke)).append("\" stroke-width=\"2\"");
        if (Double.isNaN(on)) {
            sb.append(" stroke-dasharray=\"3,3\"");
        }
        sb.append("/>");
        String label = Double.isNaN(on) && !e.has("label") ? UNKNOWN : e.path("label").asText("");
        sb.append("<text x=\"").append(num(x)).append("\" y=\"").append(num(y))
            .append("\" text-anchor=\"middle\" dominant-baseline=\"central\" fill=\"").append(esc(e.path("labelFill").asText(textColor)))
            .append("\" font-size=\"").append(num(r * 1.2)).append("\">").append(esc(label)).append("</text>");
        sb.append("</g>\n");
    }

    private void arrow(StringBuilder sb, JsonNode e, SynopticFunctions f) {
        double x = e.path("x").asDouble();
        double y = e.path("y").asDouble();
        double size = e.path("size").asDouble(16);
        double angle = e.path("angle").asDouble(0);  // Direction (degrees, SVG frame) of a positive "dir"
        double dir = e.has("dir") ? eval(e.get("dir"), f) : 1;
        double deadband = e.path("deadband").asDouble(0);
        String fill = e.path("fill").asText(arrowColor);
        openGroup(sb, e, "synoptic-arrow", f);
        if (!Double.isNaN(dir) && Math.abs(dir) > deadband) {
            double a = dir < 0 ? angle + 180 : angle;
            double s = size;
            // Arrow pointing to +x, centered on (0, 0): shaft + head
            sb.append("<path transform=\"translate(").append(num(x)).append(',').append(num(y)).append(") rotate(").append(num(a))
                .append(")\" d=\"M").append(num(-s / 2)).append(',').append(num(-s * 0.09))
                .append(" L").append(num(s * 0.1)).append(',').append(num(-s * 0.09))
                .append(" L").append(num(s * 0.1)).append(',').append(num(-s * 0.3))
                .append(" L").append(num(s / 2)).append(",0")
                .append(" L").append(num(s * 0.1)).append(',').append(num(s * 0.3))
                .append(" L").append(num(s * 0.1)).append(',').append(num(s * 0.09))
                .append(" L").append(num(-s / 2)).append(',').append(num(s * 0.09))
                .append(" Z\" fill=\"").append(esc(fill)).append("\"/>");
        }
        if (e.has("expr")) {
            double v = eval(e.get("expr"), f);
            if (e.path("abs").asBoolean(true) && !Double.isNaN(v)) {
                v = Math.abs(v);
            }
            double lx = x + e.path("labelDx").asDouble(0);
            double ly = y + e.path("labelDy").asDouble(0);
            text(sb, lx, ly, format(v, e), e, thresholdColor(v, e, e.path("labelFill").asText(fill)));
        }
        sb.append("</g>\n");
    }

    private void value(StringBuilder sb, JsonNode e, SynopticFunctions f) {
        double v = eval(e.get("expr"), f);
        text(sb, e.path("x").asDouble(), e.path("y").asDouble(), format(v, e), e, thresholdColor(v, e, e.path("fill").asText(valueColor)));
    }

    private void table(StringBuilder sb, JsonNode e, SynopticFunctions f) {
        double x = e.path("x").asDouble();
        double y = e.path("y").asDouble();
        double rowH = e.path("rowHeight").asDouble(fontSize * 1.5);
        double labelW = e.path("labelWidth").asDouble(200);
        double valueW = e.path("valueWidth").asDouble(80);
        double pad = 6;
        int nRows = e.path("rows").size();
        boolean hasTitle = e.has("title");
        double h = rowH * (nRows + (hasTitle ? 1 : 0)) + pad;
        openGroup(sb, e, "synoptic-table", f);
        sb.append("<rect x=\"").append(num(x)).append("\" y=\"").append(num(y)).append("\" width=\"").append(num(labelW + valueW + 2 * pad))
            .append("\" height=\"").append(num(h)).append("\" rx=\"4\" fill=\"").append(esc(e.path("fill").asText("none")))
            .append("\" stroke=\"").append(esc(e.path("stroke").asText(textColor))).append("\"/>");
        double fs = e.path("fontSize").asDouble(fontSize);
        double cy = y + pad / 2 + rowH * 0.5;
        if (hasTitle) {
            sb.append("<text x=\"").append(num(x + pad)).append("\" y=\"").append(num(cy)).append("\" dominant-baseline=\"central\" font-size=\"")
                .append(num(fs)).append("\" font-weight=\"bold\" fill=\"").append(esc(e.path("titleFill").asText(textColor))).append("\">")
                .append(esc(e.path("title").asText())).append("</text>");
            cy += rowH;
        }
        for (JsonNode row : e.path("rows")) {
            sb.append("<text x=\"").append(num(x + pad)).append("\" y=\"").append(num(cy)).append("\" dominant-baseline=\"central\" font-size=\"")
                .append(num(fs)).append("\" fill=\"").append(esc(row.path("labelFill").asText(e.path("labelFill").asText(textColor)))).append("\">")
                .append(esc(row.path("label").asText())).append("</text>");
            String text;
            String color = row.path("fill").asText(e.path("valueFill").asText(textColor));
            if (row.has("text")) {
                text = row.path("text").asText();
            } else {
                double v = eval(row.get("expr"), f);
                text = format(v, row);
                color = thresholdColor(v, row, color);
            }
            sb.append("<text x=\"").append(num(x + pad + labelW + valueW)).append("\" y=\"").append(num(cy))
                .append("\" text-anchor=\"end\" dominant-baseline=\"central\" font-size=\"").append(num(fs)).append("\" fill=\"")
                .append(esc(color)).append("\">").append(esc(text)).append("</text>");
            cy += rowH;
        }
        sb.append("</g>\n");
    }

    private void text(StringBuilder sb, double x, double y, String content, JsonNode e, String color) {
        sb.append("<text x=\"").append(num(x)).append("\" y=\"").append(num(y)).append("\" fill=\"").append(esc(color)).append("\"");
        String anchor = e.path("anchor").asText("middle");
        sb.append(" text-anchor=\"").append(esc(anchor)).append("\" dominant-baseline=\"central\"");
        if (e.has("fontSize")) {
            sb.append(" font-size=\"").append(num(e.path("fontSize").asDouble())).append("\"");
        }
        if (e.path("bold").asBoolean(false)) {
            sb.append(" font-weight=\"bold\"");
        }
        if (e.path("italic").asBoolean(false)) {
            sb.append(" font-style=\"italic\"");
        }
        sb.append(">").append(esc(content)).append("</text>\n");
    }

    private static List<double[]> pointList(JsonNode points) {
        List<double[]> pts = new ArrayList<>();
        for (JsonNode p : points) {
            pts.add(new double[] {p.path(0).asDouble(), p.path(1).asDouble()});
        }
        return pts;
    }

    private static String points(JsonNode points) {
        StringBuilder sb = new StringBuilder();
        for (double[] p : pointList(points)) {
            sb.append(num(p[0])).append(',').append(num(p[1])).append(' ');
        }
        return sb.toString().trim();
    }

    private static String num(double v) {
        if (v == Math.rint(v) && Math.abs(v) < 1e9) {
            return Long.toString((long) v);
        }
        return String.format(Locale.ROOT, "%.2f", v);
    }

    private static String esc(String s) {
        StringBuilder sb = new StringBuilder(s.length());
        for (char c : s.toCharArray()) {
            switch (c) {
                case '<' -> sb.append("&lt;");
                case '>' -> sb.append("&gt;");
                case '&' -> sb.append("&amp;");
                case '"' -> sb.append("&quot;");
                default -> sb.append(c);
            }
        }
        return sb.toString();
    }
}
