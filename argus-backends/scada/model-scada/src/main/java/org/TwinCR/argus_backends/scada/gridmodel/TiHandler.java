/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.scada.gridmodel;

import java.util.Set;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;


public class TiHandler {
    private static final Logger LOGGER = LoggerFactory.getLogger(TiHandler.class);

    private final Ti data;

    public TiHandler(Ti data) {
        this.data = data;
    }

    public String getType() {
        return data.type();
    }

    public String getTase2() {
        return data.tase2();
    }

    public String getEquipmentId() {
        if (isBreakerStatus()) {
            if (data.iidmdj() == null) {
                LOGGER.debug("No iidmdj set in {}", data);
            }
            return data.iidmdj();
        }
        String equipementId = data.iidm();
        if (equipementId == null) {
            equipementId = data.bayiidm();
        }
        if (equipementId == null) {
            LOGGER.debug("No iidm set in {}", data);
        }
        return equipementId;
    }

    public String getSide() {
        return data.side();
    }

    public String getLibelle() {
        String libelle = data.libelle();

        if (data.iidm() != null && "TM".equals(getType())) {
            libelle = data.oldLib();
        }
        return libelle;
    }

    public String getKind() {
        if (isBreakerStatus()) {
            return "state";
        }

        String kind = data.typ();
        if (kind == null || kind.isEmpty()) {
            return null;
        }

        kind = kind.toUpperCase();

        switch (kind) {
            case "U":
            case "U.BTS":
                return "U";
            case "P":
                return "P";
            case "Q":
                return "Q";
            case "STATE":
                return "state";
            default:
                LOGGER.debug("Unhandled kind {} in {}", kind, data);
                return null;  // The vast majority of cases
        }
    }

    private boolean isBreakerStatus() {
        String bayt = data.bayt();
        if (bayt == null) {
            return false;
        }

        if (Set.of("Breaker", "Disconnector", "LoadBreakSwitch").contains(bayt)) {
            String pointclass = data.pointclass();
            if (pointclass == null) {
                return false;
            }

            return BREAKER_POINT_CLASSES.contains(pointclass);
        }
        return false;
    }

    private static final Set<String> BREAKER_POINT_CLASSES = Set.of(
            "SA.AT#", "S.SHUNTb", "SI.#", "SA.b#HT", "DJ#.HT", "DJ.TRu1#", "DJ.MT#", "SS.bt##", "SRB.##",
            "SA.AT#HT", "SL.HT", "DJ.GR.S", "DJ.COMP", "SA.b", "SRB#.HT", "SM.b", "SL#", "COUPL", "SSb.ssHT",
            "INTER2", "DJ", "DJ.MT#.S", "COUPL.S", "DJ.HT.S", "DJ.SH.HT", "INTER", "INTER1", "DJ.MT.GR",
            "SA.#HT", "DJ.MCOMP", "INTERbHT", "DJ.HT", "SA.b#", "DJ.TA", "DJ.GR"
    );
}
