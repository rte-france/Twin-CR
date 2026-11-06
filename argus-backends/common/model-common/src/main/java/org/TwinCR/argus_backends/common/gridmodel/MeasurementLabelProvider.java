/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.common.gridmodel;

import java.util.ArrayList;
import java.util.List;

import com.powsybl.iidm.network.Identifiable;
import com.powsybl.iidm.network.Network;
import com.powsybl.iidm.network.ThreeSides;
import com.powsybl.iidm.network.extensions.Measurement;
import com.powsybl.iidm.network.extensions.Measurements;
import com.powsybl.sld.layout.LayoutParameters;
import com.powsybl.sld.library.SldComponentLibrary;
import com.powsybl.sld.model.nodes.FeederNode;
import com.powsybl.sld.svg.DefaultLabelProvider;
import com.powsybl.sld.svg.FeederInfo;
import com.powsybl.sld.svg.LabelProvider;
import com.powsybl.sld.svg.SvgParameters;
import com.powsybl.sld.svg.ValueFeederInfo;

import static com.powsybl.sld.library.SldComponentTypeName.*;

public class MeasurementLabelProvider extends DefaultLabelProvider {
    public MeasurementLabelProvider(Network network, SldComponentLibrary componentLibrary,
                                     LayoutParameters layoutParameters, SvgParameters svgParameters) {
        super(network, componentLibrary, layoutParameters, svgParameters);
    }

    @Override
    public List<FeederInfo> getFeederInfos(FeederNode node) {
        String id = node.getId();
        String sideStr = id.substring(id.lastIndexOf('_') + 1);
        ThreeSides side;
        try {
            side = ThreeSides.valueOf(sideStr);
        } catch (IllegalArgumentException e) {
            side = ThreeSides.ONE;
        }

        List<FeederInfo> infos = new ArrayList<>(super.getFeederInfos(node));
        Identifiable<?> identifiable = network.getIdentifiable(node.getEquipmentId());
        if (identifiable == null) {
            return infos;
        }
        Measurements<?> measurements = (Measurements<?>) identifiable.getExtension(Measurements.class);
        if (measurements == null) {
            return infos;
        }

        addMeasurement(side, infos, measurements, Measurement.Type.ACTIVE_POWER,
            ARROW_ACTIVE, svgParameters.getActivePowerUnit());
        addMeasurement(side, infos, measurements, Measurement.Type.REACTIVE_POWER,
            ARROW_REACTIVE, svgParameters.getReactivePowerUnit());

        return infos;
    }

    private void addMeasurement(ThreeSides side, List<FeederInfo> infos, Measurements<?> measurements,
                                 Measurement.Type type, String componentType, String unit) {
        String antenna = Character.toString(0x1F4E1);
        measurements.getMeasurements(type).stream()
            .filter(m -> m.getSide() == side)
            .findFirst().ifPresent(m -> {
            double measured = (double) m.getValue();
            LabelProvider.LabelDirection direction = measured > 0
                ? LabelProvider.LabelDirection.OUT : LabelProvider.LabelDirection.IN;
            infos.add(new ValueFeederInfo(componentType, direction,
                null, antenna + " " + valueFormatter.formatPower(measured, unit), m.getId()));
        });
    }
}
