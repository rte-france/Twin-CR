/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.common.gridmodel;

import java.util.Map;

final class ProtectionEquipmentStyleCatalog {

    record ProtectionEquipmentStyles(String colorActive, String colorInactive, String labelActive, String labelInactive) {}

    private static ProtectionEquipmentStyles og(String label) {
        return new ProtectionEquipmentStyles("orange", "grey", label, label);
    }

    private static ProtectionEquipmentStyles rb(String label) {
        return new ProtectionEquipmentStyles("red", "black", label, label);
    }

    private static ProtectionEquipmentStyles oo(String labelActive, String labelInactive) {
        return new ProtectionEquipmentStyles("orange", "orange", labelActive, labelInactive);
    }

    private static final ProtectionEquipmentStyles DEFAULT = og("?");

    private static final Map<String, ProtectionEquipmentStyles> CATALOG = Map.ofEntries(
        Map.entry("AMU",      og("AMU")),
        Map.entry("RSE",      og("RSE")),
        Map.entry("RTS",      og("RTS")),
        Map.entry("AUTD",     og("AUTD")),
        Map.entry("AR.MONO",  og("M")),
        Map.entry("AR.TRIPH", og("T")),
        Map.entry("AR.TRI.R", og("R")),
        Map.entry("UREF",     oo("BO2", "BO1")),
        Map.entry("AUT.EXT",  og("EXT")),
        Map.entry("PDA.",     og("PDA")),
        Map.entry("AL.SUR.1", rb("Su 1")),
        Map.entry("AL.SUR.5", rb("Su 5")),  // Added compared to original Titien-Xplorer
        Map.entry("AL.SUR10", rb("Su 10")),
        Map.entry("AL.SUR20", rb("Su 20")),
        Map.entry("AL.SUR60", rb("Su 60")),
        Map.entry("MQ.UL",    rb("U")),
        Map.entry("RAT",      og("RAT")),
        Map.entry("AL.T.LIM", rb("0L")),
        Map.entry("REG.AUTO", og("REG.AUTO")),
        Map.entry("REG.SEC1", og("REG.SEC")),
        Map.entry("EXP.TRAN", rb("TEP")),
        Map.entry("DF.TRAN",  rb("T")),
        Map.entry("ISOL.DJ",  rb("D")),
        Map.entry("ARR.POMP", rb("P")),
        Map.entry("AR.IC",    og("IC")),
        Map.entry("AR.RENV",  oo("▲▼", "▬")),
        Map.entry("AR.REB",   og("▬")),
        Map.entry("AR.RVL",   og("▲")),
        Map.entry("AR.RVB",   og("▼")),
        Map.entry("AR.RVB+L", og("▲▼")),
        Map.entry("AR.D.REN", og("▲")),
        Map.entry("RTS.RVL",  og("⭡")),
        Map.entry("RTS.RVB",  og("⭣"))
    );

    private ProtectionEquipmentStyleCatalog() {}

    static String getColor(String peType, boolean active) {
        ProtectionEquipmentStyles c = CATALOG.getOrDefault(peType, DEFAULT);
        return active ? c.colorActive() : c.colorInactive();
    }

    static String getLabel(String peType, boolean active) {
        ProtectionEquipmentStyles c = CATALOG.getOrDefault(peType, DEFAULT);
        return active ? c.labelActive() : c.labelInactive();
    }

    static boolean contains(String peType) {
        return CATALOG.containsKey(peType);
    }
}
