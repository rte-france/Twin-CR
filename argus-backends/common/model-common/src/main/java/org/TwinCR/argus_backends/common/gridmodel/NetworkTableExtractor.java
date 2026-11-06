/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.common.gridmodel;

import com.powsybl.dataframe.DataframeElementType;
import com.powsybl.dataframe.DataframeFilter;
import com.powsybl.dataframe.DataframeHandler;
import com.powsybl.dataframe.network.NetworkDataframeContext;
import com.powsybl.dataframe.network.NetworkDataframes;
import com.powsybl.iidm.network.Network;
import com.powsybl.iidm.network.Substation;
import com.powsybl.iidm.network.VoltageLevel;

import java.util.*;

public class NetworkTableExtractor {
    public record NetworkTable(List<String> columns, Map<String, Object[]> rowsById) {
        public Set<String> ids() {
            return rowsById.keySet();
        }

        public boolean contains(String id) {
            return rowsById.containsKey(id);
        }

        public List<Object> row(String id) {
            Object[] values = rowsById.get(id);
            return values == null ? null : Arrays.asList(values);
        }
    }

    private static CollectingHandler collect(Network network, DataframeElementType type) {
        var mapper = NetworkDataframes.getDataframeMapper(type);
        var handler = new CollectingHandler();
        mapper.createDataframe(network, handler, new DataframeFilter(), NetworkDataframeContext.DEFAULT);
        return handler;
    }

    public static NetworkTable extract(Network network, DataframeElementType type) {
        CollectingHandler handler = collect(network, type);
        return build(handler.columns(), handler.size(), List.of(), null, null, null);
    }

    public static Map<String, NetworkTable> extractAll(Network network) {
        NetworkTable substations = extract(network, DataframeElementType.SUBSTATION);

        // Columns describing a row's substation (country, TSO...), added to every table that names a substation or voltage level.
        List<String> extraColumns = substations.columns().stream()
            .filter(column -> !column.equals("id") && !column.equals("name"))
            .toList();
        int[] extraSource = extraColumns.stream().mapToInt(substations.columns()::indexOf).toArray();
        Map<String, Object[]> substationDataframeByVoltageLevel = buildSubstationDataframeByVoltageLevelIndex(network, substations);

        Map<String, NetworkTable> result = new LinkedHashMap<>();
        for (DataframeElementType type : DataframeElementType.values()) {
            try {
                CollectingHandler handler = collect(network, type);
                result.put(toSnakeName(type), build(handler.columns(), handler.size(),
                        extraColumns, extraSource, substations.rowsById(), substationDataframeByVoltageLevel));
            } catch (Exception e) {
                // Some element types do not have a mapper
            }
        }
        return result;
    }

    private static NetworkTable build(Map<String, Object[]> columnData, int size, List<String> extraColumns, int[] extraSource,
            Map<String, Object[]> substationDataframeBySubstationId, Map<String, Object[]> substationDataframeByVoltageLevel) {

        List<String> baseColumns = List.copyOf(columnData.keySet());
        Object[][] data = columnData.values().toArray(new Object[0][]);
        int idColumn = baseColumns.indexOf("id");
        int substationColumn = baseColumns.indexOf("substation_id");
        int voltageLevelColumn = baseColumns.indexOf("voltage_level_id");
        boolean hasSubstationColumn = substationColumn >= 0;
        boolean hasVoltageLevelColumn = voltageLevelColumn >= 0;

        // Only a table naming a substation or voltage level gets the extra columns.
        boolean addSubstationColumns = (hasSubstationColumn || hasVoltageLevelColumn) && substationDataframeBySubstationId != null;
        List<String> columns = baseColumns;
        if (addSubstationColumns) {
            columns = new ArrayList<>(baseColumns);
            columns.addAll(extraColumns);
        }

        Map<String, Object[]> rowsById = new LinkedHashMap<>();
        for (int i = 0; i < size; i++) {
            String id = idColumn >= 0 ? (String) data[idColumn][i] : null;
            if (id == null) id = buildSyntheticId(columnData, i);
            if (id == null) continue;
            if (rowsById.containsKey(id)) id = id + "#" + rowsById.size();

            Object[] row = new Object[columns.size()];
            for (int c = 0; c < baseColumns.size(); c++) {
                row[c] = data[c][i];
            }
            if (addSubstationColumns) {
                Object[] substation = substation(data, i, substationColumn, voltageLevelColumn, substationDataframeBySubstationId, substationDataframeByVoltageLevel);
                for (int e = 0; e < extraColumns.size(); e++) {
                    row[baseColumns.size() + e] = substation == null ? null : substation[extraSource[e]];
                }
            }
            rowsById.put(id, row);
        }
        return new NetworkTable(columns, rowsById);
    }

    private static Object[] substation(Object[][] data, int row, int substationColumn, int voltageLevelColumn,
            Map<String, Object[]> substationDataframeBySubstationId, Map<String, Object[]> substationDataframeByVoltageLevel) {

        Object substationId = substationColumn >= 0 ? data[substationColumn][row] : null;
        if (substationId != null) {
            return substationDataframeBySubstationId.get((String) substationId);
        }
        Object voltageLevelId = voltageLevelColumn >= 0 ? data[voltageLevelColumn][row] : null;
        return voltageLevelId == null ? null : substationDataframeByVoltageLevel.get((String) voltageLevelId);
    }

    // Some dataframes (e.g. OperationalLimits) have no "id" column: their index is "element_id",
    // shared by several rows (one per side (ONE/TWO) and name (permanent_limit/SUR_20/...))
    // We build a unique key by concaneting those rows
    private static String buildSyntheticId(Map<String, Object[]> columnData, int row) {
        Object[] elementIds = columnData.get("element_id");
        if (elementIds == null || elementIds[row] == null) return null;
        StringBuilder sb = new StringBuilder(String.valueOf(elementIds[row]));
        sb.append("#_fake_id_#_");  // Avoid potential conflicts with actual powsybl ids
        for (String key : List.of("side", "name")) {
            Object[] column = columnData.get(key);
            if (column != null && column[row] != null) sb.append('_').append(column[row]);
        }
        return sb.toString();
    }

    private static Map<String, Object[]> buildSubstationDataframeByVoltageLevelIndex(Network network, NetworkTable substations) {
        Map<String, Object[]> index = new HashMap<>();
        for (VoltageLevel vl : network.getVoltageLevels()) {
            Substation sub = vl.getSubstation().orElse(null);
            if (sub == null) continue;
            Object[] substationRow = substations.rowsById().get(sub.getId());
            if (substationRow != null) index.put(vl.getId(), substationRow);
        }
        return index;
    }

    // Implements the callback interface the mapper uses to push columnar data
    private static class CollectingHandler implements DataframeHandler {
        private final Map<String, Object[]> columns = new LinkedHashMap<>();
        private int size;

        Map<String, Object[]> columns() {
            return columns;
        }

        int size() {
            return size;
        }

        @Override
        public void allocate(int seriesCount) {
            // seriesCount is just a hint for pre-allocation, columns are registered via new*Series
        }

        @Override
        public StringSeriesWriter newStringIndex(String name, int size) {
            return newStringSeries(name, size);
        }

        @Override
        public IntSeriesWriter newIntIndex(String name, int size) {
            return newIntSeries(name, size);
        }

        @Override
        public StringSeriesWriter newStringSeries(String name, int size) {
            Object[] col = column(name, size);
            return (index, value) -> col[index] = value;
        }

        @Override
        public OptionalIntSeriesWriter newOptionalIntSeries(String name, int size) {
            Object[] col = column(name, size);
            return (index, value) -> col[index] = value;
        }

        @Override
        public IntSeriesWriter newIntSeries(String name, int size) {
            Object[] col = column(name, size);
            return (index, value) -> col[index] = value;
        }

        @Override
        public BooleanSeriesWriter newBooleanSeries(String name, int size) {
            Object[] col = column(name, size);
            return (index, value) -> col[index] = value;
        }

        @Override
        public OptionalDoubleSeriesWriter newOptionalDoubleSeries(String name, int size) {
            Object[] col = column(name, size);
            return (index, value) -> col[index] = value;
        }

        @Override
        public DoubleSeriesWriter newDoubleSeries(String name, int size) {
            Object[] col = column(name, size);
            return (index, value) -> col[index] = value;
        }

        private Object[] column(String name, int size) {
            this.size = size;
            Object[] col = new Object[size];
            columns.put(name, col);
            return col;
        }
    }

    private static String toSnakeName(DataframeElementType type) {
        return switch (type) {
            case BUS -> "bus";
            case BUS_FROM_BUS_BREAKER_VIEW -> "bus_from_bus_breaker_view";
            case LINE -> "line";
            case TWO_WINDINGS_TRANSFORMER -> "2_windings_transformer";  // Note: 2 instead of two to match pypowsybl
            case THREE_WINDINGS_TRANSFORMER -> "3_windings_transformer";
            case GENERATOR -> "generator";
            case LOAD -> "load";
            case GROUND -> "ground";
            case BATTERY -> "battery";
            case SHUNT_COMPENSATOR -> "shunt_compensator";
            case NON_LINEAR_SHUNT_COMPENSATOR_SECTION -> "non_linear_shunt_compensator_section";
            case LINEAR_SHUNT_COMPENSATOR_SECTION -> "linear_shunt_compensator_section";
            case BOUNDARY_LINE -> "boundary_line";
            case BOUNDARY_LINE_GENERATION -> "boundary_line_generation";
            case TIE_LINE -> "tie_line";
            case LCC_CONVERTER_STATION -> "lcc_converter_station";
            case VSC_CONVERTER_STATION -> "vsc_converter_station";
            case STATIC_VAR_COMPENSATOR -> "static_var_compensator";
            case SWITCH -> "switch";
            case VOLTAGE_LEVEL -> "voltage_level";
            case SUBSTATION -> "substation";
            case BUSBAR_SECTION -> "busbar_section";
            case HVDC_LINE -> "hvdc_line";
            case RATIO_TAP_CHANGER_STEP -> "ratio_tap_changer_step";
            case PHASE_TAP_CHANGER_STEP -> "phase_tap_changer_step";
            case RATIO_TAP_CHANGER -> "ratio_tap_changer";
            case PHASE_TAP_CHANGER -> "phase_tap_changer";
            case REACTIVE_CAPABILITY_CURVE_POINT -> "reactive_capability_curve_point";
            case LOADING_LIMITS -> "loading_limits";
            case VOLTAGE_ANGLE_LIMITS -> "voltage_angle_limits";
            case SELECTED_LOADING_LIMITS -> "selected_loding_limits";
            case MINMAX_REACTIVE_LIMITS -> "minmax_reactive_limits";
            case ALIAS -> "alias";
            case IDENTIFIABLE -> "identifiable";
            case INJECTION -> "injection";
            case BRANCH -> "branch";
            case TERMINAL -> "terminal";
            case SUB_NETWORK -> "sub_network";
            case AREA -> "area";
            case AREA_VOLTAGE_LEVELS -> "area_voltage_levels";
            case AREA_BOUNDARIES -> "area_boundaries";
            case INTERNAL_CONNECTION -> "internal_connection";
            case PROPERTIES -> "properties";
            case DC_LINE -> "dc_lines";
            case DC_NODE -> "dc_node";
            case VOLTAGE_SOURCE_CONVERTER -> "voltage_source_converter";
            case DC_GROUND -> "dc_ground";
            case DC_SWITCH -> "dc_switch";
            case DC_BUS -> "dc_bus";
        };
    }
}
