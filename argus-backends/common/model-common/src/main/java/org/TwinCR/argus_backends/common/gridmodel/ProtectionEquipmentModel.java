/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.common.gridmodel;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.MappingIterator;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.annotation.JsonDeserialize;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Path;
import java.util.*;
import java.util.concurrent.atomic.AtomicReference;

import com.powsybl.sld.model.nodes.NodeSide;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import org.TwinCR.argus_backends.common.core.util.FileLoader;
import org.TwinCR.argus_backends.common.core.util.PooledString;
import org.TwinCR.argus_backends.common.datamodel.Value;

public class ProtectionEquipmentModel {
    private static final Logger LOGGER = LoggerFactory.getLogger(ProtectionEquipmentModel.class);
    private static final ObjectMapper MAPPER = new ObjectMapper();


    public record ProtectionEquipmentValue(String typ, String libelle, String tase2, Value value, String tase2_control) {}

    private record ProtectionEquipmentEntry(String typ, String libelle, String tase2, String dv, String side, AtomicReference<Value> value) {}

    @JsonIgnoreProperties(ignoreUnknown = true)
    private record TiMappedEntry(
        @JsonProperty("type")    @JsonDeserialize(using = PooledString.class) String type,
        @JsonProperty("libelle") String libelle,
        @JsonProperty("dv")      String dv,  // Null for TVC and OM
        @JsonProperty("typ")     @JsonDeserialize(using = PooledString.class) String typ,
        @JsonProperty("tase2")   String tase2,
        @JsonProperty("bayt")    @JsonDeserialize(using = PooledString.class) String bayt,
        @JsonProperty("iidm")    @JsonDeserialize(using = PooledString.class) String iidm,
        @JsonProperty("iidmdj")  @JsonDeserialize(using = PooledString.class) String iidmdj,  // Nullable, the breaker that trips
        @JsonProperty("side")    @JsonDeserialize(using = PooledString.class) String side,  // Nullable
        @JsonProperty("bayiidm") @JsonDeserialize(using = PooledString.class) String bayiidm
    ) {}

    // Where a protection equipment is shown: an equipment of the case and, for a branch, its side.
    private record Target(String equipmentId, String side) {}

    private final Map<String, ProtectionEquipmentEntry> byLibelle;
    private final Map<String, List<ProtectionEquipmentEntry>> byIidm;
    private final Map<String, String> tase2ControlByDv;

    public ProtectionEquipmentModel(Path jsonPath) throws IOException {
        Map<String, ProtectionEquipmentEntry> libMap = new HashMap<>();
        Map<String, List<ProtectionEquipmentEntry>> iidmMap = new HashMap<>();
        Map<String, String> tcMap = new HashMap<>();

        // Read the (eventually compressed) timapped.json one entry at a time.
        try (InputStream in = FileLoader.open(jsonPath);
             MappingIterator<TiMappedEntry> iterator = MAPPER.readerFor(TiMappedEntry.class).readValues(in)) {
            while (iterator.hasNext()) {
                TiMappedEntry e = iterator.next();
                if (!"ProtectionEquipment".equals(e.bayt())) {
                    continue;
                }
                if (("TS".equals(e.type()) || "TM".equals(e.type()) || "OM".equals(e.type()))
                        && e.typ() != null
                        && ProtectionEquipmentStyleCatalog.contains(e.typ())) {
                    Target target = resolveTarget(e);
                    ProtectionEquipmentEntry pe = new ProtectionEquipmentEntry(e.typ(), e.libelle(), e.tase2(), e.dv(), target.side(),
                        new AtomicReference<>(new Value.IntValue(0)));
                    libMap.put(e.libelle(), pe);
                    iidmMap.computeIfAbsent(target.equipmentId(), k -> new ArrayList<>()).add(pe);
                } else if ("TC".equals(e.type()) && e.dv() != null) {
                    tcMap.put(e.dv(), e.tase2());
                }
            }
        } finally {
            PooledString.release();
        }

        // Use unmodifiableMap for thread-safety, value can still be modified (but no element can be added/removed)
        this.byLibelle = Collections.unmodifiableMap(libMap);

        Map<String, List<ProtectionEquipmentEntry>> frozenBay = new HashMap<>();
        iidmMap.forEach((k, v) -> frozenBay.put(k, Collections.unmodifiableList(v)));
        this.byIidm = Collections.unmodifiableMap(frozenBay);

        this.tase2ControlByDv = Collections.unmodifiableMap(tcMap);
    }

    /**
     * Return where a protection equipment is shown.
     *
     * The mapping names the breaker that trips, in the voltage level the protection belongs to, which
     * is where it is drawn. It has no side of its own; "iidm", the element the measurement is taken
     * from, is a fallback for the entries that name no breaker.
     */
    private static Target resolveTarget(TiMappedEntry e) {
        if (e.iidmdj() != null) {
            return new Target(e.iidmdj(), null);
        }
        return new Target(e.iidm(), e.side());
    }

    public boolean updateByLibelle(String libelle, Value value) {
        ProtectionEquipmentEntry e = byLibelle.get(libelle);
        if (e != null) {
            e.value().set(value);
            return true;
        }
        return false;
    }

    public List<ProtectionEquipmentValue> getByEquipmentId(String iidmId, NodeSide side) {
        String sideStr = side == null ? null : switch (side) {
            case ONE -> "1";
            case TWO -> "2";
            case THREE -> "3";
        };

        return byIidm.getOrDefault(iidmId, List.of())
            .stream()
            .filter(e -> e.side() == null || Objects.equals(e.side(), sideStr))
            .map(e -> new ProtectionEquipmentValue(e.typ(), e.libelle(), e.tase2(), e.value().get(), tase2ControlByDv.get(e.dv())))
            .toList();
    }
}
