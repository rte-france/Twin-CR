/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.common.synoptic;

import com.powsybl.iidm.network.*;

import org.TwinCR.argus_backends.common.gridmodel.LatestValues;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Functions available in the synoptic expressions, evaluated on the backend network model
 * (GridModel.network) and on the latest raw telemetry values. Unknown ids give NaN ("?").
 *
 * <ul>
 *   <li>{@code p1/p2/q1/q2/i1/i2('id')}: branch (line, transformer, tie line), HVDC line or 3 windings transformer (p3...) side values; 0 if the side is disconnected</li>
 *   <li>{@code p/q/i('id')}: injection (generator, load, battery, shunt, dangling line, converter station) terminal values (load sign convention)</li>
 *   <li>{@code pgen('id')}: -p, i.e. produced active power</li>
 *   <li>{@code ilim1/ilim2('id')}: permanent current limit of a branch side</li>
 *   <li>{@code connected('id')}: 1 if every terminal of the equipment is connected to a bus</li>
 *   <li>{@code v/vmin/vmax('vlId')}: max/min bus voltage (kV) of a voltage level, {@code nbus('vlId')} its number of electrical nodes</li>
 *   <li>{@code bus('id')}, {@code bus1/bus2('id')}: index (0 = main node) of the electrical node of a terminal in its voltage level, NaN if disconnected</li>
 *   <li>{@code targetp/maxp/minp('genId')}: generator set point and limits</li>
 *   <li>{@code exchange('FR', 'BE')}: active power flowing from country A to country B on the lines/HVDC between them</li>
 *   <li>{@code out('id')}: latest raw telemetry value (gm_output / scada_output id, TI libelle or tase2 id)</li>
 * </ul>
 */
public class SynopticFunctions implements SynopticExpression.Functions {

    private final Network network;
    private final Map<String, List<Bus>> busesByVl = new HashMap<>();
    private static final Map<String, List<BorderLink>> BORDER_CACHE = new HashMap<>();

    private record BorderLink(Identifiable<?> equipment, Terminal sideA) {}

    public SynopticFunctions(Network network) {
        this.network = network;
    }

    /** True if the network has an equipment / container with this id */
    public boolean exists(String id) {
        return network.getIdentifiable(id) != null;
    }

    @Override
    public double call(String name, List<Object> args) {
        return switch (name) {
            case "p1" -> sideValue(str(args, 0), 1, 'p');
            case "p2" -> sideValue(str(args, 0), 2, 'p');
            case "p3" -> sideValue(str(args, 0), 3, 'p');
            case "q1" -> sideValue(str(args, 0), 1, 'q');
            case "q2" -> sideValue(str(args, 0), 2, 'q');
            case "q3" -> sideValue(str(args, 0), 3, 'q');
            case "i1" -> sideValue(str(args, 0), 1, 'i');
            case "i2" -> sideValue(str(args, 0), 2, 'i');
            case "i3" -> sideValue(str(args, 0), 3, 'i');
            case "p" -> sideValue(str(args, 0), 0, 'p');
            case "q" -> sideValue(str(args, 0), 0, 'q');
            case "i" -> sideValue(str(args, 0), 0, 'i');
            case "pgen" -> -sideValue(str(args, 0), 0, 'p');
            case "ilim1" -> currentLimit(str(args, 0), TwoSides.ONE);
            case "ilim2" -> currentLimit(str(args, 0), TwoSides.TWO);
            case "connected" -> connected(str(args, 0));
            case "v", "vmax" -> voltage(str(args, 0), true);
            case "vmin" -> voltage(str(args, 0), false);
            case "nbus" -> busCount(str(args, 0));
            case "bus" -> busIndex(terminal(str(args, 0), 0));
            case "bus1" -> busIndex(terminal(str(args, 0), 1));
            case "bus2" -> busIndex(terminal(str(args, 0), 2));
            case "bus3" -> busIndex(terminal(str(args, 0), 3));
            case "targetp" -> generatorValue(str(args, 0), Generator::getTargetP);
            case "maxp" -> generatorValue(str(args, 0), Generator::getMaxP);
            case "minp" -> generatorValue(str(args, 0), Generator::getMinP);
            case "exchange" -> exchange(str(args, 0), str(args, 1));
            case "out" -> LatestValues.get(str(args, 0));
            default -> throw new IllegalArgumentException("Unknown synoptic function " + name + "()");
        };
    }

    private static String str(List<Object> args, int i) {
        if (i >= args.size() || !(args.get(i) instanceof String s)) {
            throw new IllegalArgumentException("argument " + (i + 1) + " must be a quoted id");
        }
        return s;
    }

    /** Terminal of an equipment: side 0 for injections, 1..3 for branches / HVDC / 3 windings transformers. */
    public Terminal terminal(String id, int side) {
        Identifiable<?> identifiable = network.getIdentifiable(id);
        if (identifiable == null) {
            return null;
        }
        if (side == 0 && identifiable instanceof Injection<?> injection) {
            return injection.getTerminal();
        }
        if (identifiable instanceof Branch<?> branch && (side == 1 || side == 2)) {
            return branch.getTerminal(side == 1 ? TwoSides.ONE : TwoSides.TWO);
        }
        if (identifiable instanceof HvdcLine hvdc && (side == 1 || side == 2)) {
            return (side == 1 ? hvdc.getConverterStation1() : hvdc.getConverterStation2()).getTerminal();
        }
        if (identifiable instanceof ThreeWindingsTransformer t3 && side >= 1 && side <= 3) {
            return t3.getTerminal(ThreeSides.valueOf(side));
        }
        return null;
    }

    private static boolean isConnected(Terminal t) {
        return t.isConnected() && t.getBusView().getBus() != null;
    }

    private double sideValue(String id, int side, char kind) {
        Terminal t = terminal(id, side);
        if (t == null) {
            return Double.NaN;
        }
        if (!isConnected(t)) {
            return 0;
        }
        return switch (kind) {
            case 'p' -> t.getP();
            case 'q' -> t.getQ();
            default -> t.getI();
        };
    }

    private double currentLimit(String id, TwoSides side) {
        if (network.getIdentifiable(id) instanceof Branch<?> branch) {
            Optional<CurrentLimits> limits = branch.getCurrentLimits(side);
            return limits.map(LoadingLimits::getPermanentLimit).orElse(Double.NaN);
        }
        return Double.NaN;
    }

    private double connected(String id) {
        Identifiable<?> identifiable = network.getIdentifiable(id);
        if (identifiable instanceof Connectable<?> connectable) {
            for (Terminal t : connectable.getTerminals()) {
                if (!isConnected(t)) {
                    return 0;
                }
            }
            return 1;
        }
        if (identifiable instanceof HvdcLine hvdc) {
            return isConnected(hvdc.getConverterStation1().getTerminal())
                && isConnected(hvdc.getConverterStation2().getTerminal()) ? 1 : 0;
        }
        if (identifiable instanceof Switch sw) {
            return sw.isOpen() ? 0 : 1;
        }
        return Double.NaN;
    }

    private List<Bus> energizedBuses(String vlId) {
        return busesByVl.computeIfAbsent(vlId, id -> {
            VoltageLevel vl = network.getVoltageLevel(id);
            if (vl == null) {
                return null;
            }
            List<Bus> buses = new ArrayList<>();
            for (Bus bus : vl.getBusView().getBuses()) {
                if (bus.getConnectedTerminalCount() > 0) {
                    buses.add(bus);
                }
            }
            // Main node first: the one with the most connected terminals (stable colors between renders)
            buses.sort(Comparator.comparingInt(Bus::getConnectedTerminalCount).reversed().thenComparing(Bus::getId));
            return buses;
        });
    }

    private double voltage(String vlId, boolean max) {
        List<Bus> buses = energizedBuses(vlId);
        if (buses == null) {
            return Double.NaN;
        }
        double result = Double.NaN;
        for (Bus bus : buses) {
            double v = bus.getV();
            if (!Double.isNaN(v) && v > 0) {
                result = Double.isNaN(result) ? v : (max ? Math.max(result, v) : Math.min(result, v));
            }
        }
        return result;
    }

    private double busCount(String vlId) {
        List<Bus> buses = energizedBuses(vlId);
        return buses == null ? Double.NaN : buses.size();
    }

    private double busIndex(Terminal t) {
        if (t == null || !isConnected(t)) {
            return Double.NaN;
        }
        Bus bus = t.getBusView().getBus();
        List<Bus> buses = energizedBuses(t.getVoltageLevel().getId());
        int index = buses == null ? -1 : buses.indexOf(bus);
        return index < 0 ? 0 : index;
    }

    private double generatorValue(String id, java.util.function.ToDoubleFunction<Generator> getter) {
        Generator g = network.getGenerator(id);
        return g == null ? Double.NaN : getter.applyAsDouble(g);
    }

    private static Optional<String> country(Terminal t) {
        return t.getVoltageLevel().getSubstation().flatMap(Substation::getCountry).map(Enum::name);
    }

    private List<BorderLink> borderLinks(String countryA, String countryB) {
        synchronized (BORDER_CACHE) {
            return BORDER_CACHE.computeIfAbsent(countryA + ">" + countryB, k -> {
                List<BorderLink> links = new ArrayList<>();
                for (Branch<?> branch : network.getBranches()) {
                    addBorderLink(links, branch, branch.getTerminal1(), branch.getTerminal2(), countryA, countryB);
                }
                for (HvdcLine hvdc : network.getHvdcLines()) {
                    addBorderLink(links, hvdc, hvdc.getConverterStation1().getTerminal(),
                        hvdc.getConverterStation2().getTerminal(), countryA, countryB);
                }
                return links;
            });
        }
    }

    private static void addBorderLink(List<BorderLink> links, Identifiable<?> equipment, Terminal t1, Terminal t2,
                                      String countryA, String countryB) {
        Optional<String> c1 = country(t1);
        Optional<String> c2 = country(t2);
        if (c1.isEmpty() || c2.isEmpty()) {
            return;
        }
        if (c1.get().equals(countryA) && c2.get().equals(countryB)) {
            links.add(new BorderLink(equipment, t1));
        } else if (c2.get().equals(countryA) && c1.get().equals(countryB)) {
            links.add(new BorderLink(equipment, t2));
        }
    }

    /** Ids of the connectables between two countries (branches, tie line boundary lines, HVDC converter stations), see exchange(). */
    public List<String> borderEquipmentIds(String countryA, String countryB) {
        List<String> ids = new ArrayList<>();
        for (BorderLink link : borderLinks(countryA, countryB)) {
            if (link.equipment() instanceof HvdcLine hvdc) {
                ids.add(hvdc.getConverterStation1().getId());
                ids.add(hvdc.getConverterStation2().getId());
            } else if (link.equipment() instanceof TieLine tieLine) {
                ids.add(tieLine.getBoundaryLine1().getId());
                ids.add(tieLine.getBoundaryLine2().getId());
            } else {
                ids.add(link.equipment().getId());
            }
        }
        return ids;
    }

    private double exchange(String countryA, String countryB) {
        List<BorderLink> links = borderLinks(countryA, countryB);
        if (links.isEmpty()) {
            return Double.NaN;
        }
        double sum = 0;
        for (BorderLink link : links) {
            Terminal t = link.sideA();
            if (isConnected(t) && !Double.isNaN(t.getP())) {
                sum += t.getP();
            }
        }
        return sum;
    }
}
