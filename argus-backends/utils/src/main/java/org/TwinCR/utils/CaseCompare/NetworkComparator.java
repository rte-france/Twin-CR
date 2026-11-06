/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.utils.CaseCompare;

import com.powsybl.iidm.network.*;
import java.util.*;
import java.util.stream.Collectors;

public class NetworkComparator {
    record ComparisonResult(String id, double val1, double val2, double diffPct) {}
    record InjectionResult(String id, double p1, double q1, double s1, double p2, double q2, double s2, double diffPct) {}
    record NodeInjection(double p, double q, double s) {}

    public void compare(Network n1, Network n2) {
        List<ComparisonResult> tensionDiffs = new ArrayList<>();
        List<InjectionResult> injectionDiffs = new ArrayList<>();

        for (Bus bus1 : n1.getBusView().getBuses()) {
            Bus bus2 = n2.getBusView().getBus(bus1.getId());
            if (bus2 == null) continue;

            // --- 1. Comparaison des Tensions (V) ---
            double v1 = bus1.getV();
            double v2 = bus2.getV();
            tensionDiffs.add(new ComparisonResult(bus1.getId(), v1, v2, calculatePct(v1, v2)));

            // --- 2. Comparaison des Injections Nodales (S) ---
            NodeInjection ni1 = calculateNodeInjectionS(bus1);
            NodeInjection ni2 = calculateNodeInjectionS(bus2);
            injectionDiffs.add(new InjectionResult(bus1.getId(), ni1.p(), ni1.q(), ni1.s(), ni2.p(), ni2.q(), ni2.s(), calculatePct(ni1.s(), ni2.s())));
        }

        // Affichage des Top 20
        printTop20("TENSIONS", tensionDiffs);
        printTop20Injection("INJECTIONS", injectionDiffs);
    }

    private NodeInjection calculateNodeInjectionS(Bus bus) {
        double pSum = 0;
        double qSum = 0;

        // Somme des générateurs
        for (Generator g : bus.getGenerators()) {
            pSum += g.getTerminal().getP();
            qSum += g.getTerminal().getQ();
        }
        // Soustraction des charges
        for (Load l : bus.getLoads()) {
            pSum -= l.getTerminal().getP();
            qSum -= l.getTerminal().getQ();
        }
        // Ajout des shunts (statiques)
        for (StaticVarCompensator s : bus.getStaticVarCompensators()) {
            qSum += s.getTerminal().getQ();
        }
        // Ajout des consos fictives
        pSum += bus.getFictitiousP0();
        qSum += bus.getFictitiousQ0();

        double sValue = Math.sqrt(pSum * pSum + qSum * qSum);
        return new NodeInjection(pSum, qSum, sValue);
    }

    private double calculatePct(double v1, double v2) {
        if (Math.abs(v1) < 1e-6) return 0;
        return (Math.abs(v1 - v2) / Math.abs(v1)) * 100.0;
    }

    private void printTop20(String label, List<ComparisonResult> results) {
        System.out.println("\n--- TOP 20 ÉCARTS " + label + " (%) ---");
        results.stream()
                .sorted(Comparator.comparingDouble(ComparisonResult::diffPct).reversed())
                .limit(20)
                .forEach(r -> System.out.printf("ID: %s | N1: %.2f | N2: %.2f | Écart: %.4f%%%n",
                        r.id(), r.val1(), r.val2(), r.diffPct()));
    }

    private void printTop20Injection(String label, List<InjectionResult> results) {
        System.out.println("\n--- TOP 20 ÉCARTS " + label + " (%) ---");
        results.stream()
                .sorted(Comparator.comparingDouble(InjectionResult::diffPct).reversed())
                .limit(20)
                .forEach(r -> System.out.printf("ID: %s | N1: P=%.2f Q=%.2f S=%.2f | N2: P=%.2f Q=%.2f S=%.2f | Écart: %.4f%%%n",
                        r.id(), r.p1(), r.q1(), r.s1(), r.p2(), r.q2(), r.s2(), r.diffPct()));
    }
}