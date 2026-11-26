"""
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Direct conversion of a pypowsybl network to an ANDES system (static data: power flow, continuation power flow).

The conversion works on pypowsybl's calculated buses (bus view), so it handles node-breaker networks directly and
open couplers are respected. Only the main synchronous component is converted.

Mapping
-------
- Bus                    -> Bus (``name`` = pypowsybl bus id)
- Load                   -> PQ (p0, q0)
- Battery                -> PQ (injection: negative load)
- Generator              -> PV if voltage regulating, else PQ (injection); the generators of the slack bus are
                            aggregated in one Slack
- Static var compensator -> PV (voltage regulation, limits from b_min/b_max) or PQ (fixed reactive power)
- Shunt compensator      -> Shunt (current number of sections)
- VSC station            -> PQ at the solved state (ANDES has no HVDC model); needs a solved network
- Line                   -> Line (pi model; symmetric part of the end shunts in ``g``/``b``, asymmetric part as Shunts)
- 2-winding transformer  -> Line with tap and phase shift, plus a Shunt for the magnetizing admittance. powsybl
                            model: ideal transformer on side 1, then the shunt (g, b), then the series impedance
                            (r, x), all expressed at side 2. The shunt at that inner node draws the same power as a
                            shunt y / tap^2 on bus 1, which is what is created.

ANDES 2.0.0's Line model applies ``g1``/``b1`` (not ``g2``/``b2``) at both ends, so those four parameters are never
used here: all shunts go through ``g``/``b`` (half at each end) or separate Shunt devices.
- Branches with one open end become a Shunt at the connected bus (their input admittance).

Not converted (a warning is raised when present in the main component): 3-winding transformers, dangling lines, LCC
stations, HVDC lines (only through their VSC stations). Ratio/phase tap changer regulation and remote voltage regulation
are not modelled by ANDES: transformer taps stay at their current position and a remotely regulating generator
regulates its own bus.
"""

import warnings

import andes
import numpy as np
import pandas as pd


# Below this magnitude, a branch impedance (pu) is considered numerically degenerate.
MINIMUM_BRANCH_IMPEDANCE_PU = 1e-6
# Shunt admittances below this magnitude (pu on the system base, i.e. 1e-5 Mvar at 1 pu) are not worth a device.
MINIMUM_SHUNT_ADMITTANCE_PU = 1e-7

# OpenLoadFlow ignores voltage targets outside this range (pu of the nominal voltage): such a controller does not
# regulate. Same defaults as OpenLoadFlow's minPlausibleTargetVoltage / maxPlausibleTargetVoltage.
MINIMUM_PLAUSIBLE_TARGET_VOLTAGE_PU = 0.8
MAXIMUM_PLAUSIBLE_TARGET_VOLTAGE_PU = 1.2


class ConversionReport:
    """Counters of what was converted and what had to be approximated, printed by ``summary``."""

    def __init__(self) -> None:
        self.converted_counts: dict[str, int] = {}
        self.warnings: list[str] = []

    def count(self, element_type: str, number: int = 1) -> None:
        self.converted_counts[element_type] = self.converted_counts.get(element_type, 0) + number

    def warn(self, message: str) -> None:
        self.warnings.append(message)
        warnings.warn(message, stacklevel=3)

    def summary(self) -> str:
        counts = ", ".join(f"{count} {element_type}" for element_type, count in self.converted_counts.items())
        lines = [f"Converted: {counts}"]
        lines.extend(f"WARNING: {message}" for message in self.warnings)
        return "\n".join(lines)


def pypowsybl_to_andes(
    network,
    slack_bus_id: str | None = None,
    base_mva: float = 100.0,
    frequency_hz: float = 50.0,
    initialize_from_solution: bool = True,
):
    """
    Convert a pypowsybl network to an ANDES system, ready for ``system.PFlow.run()``.

    Parameters
    ----------
    network
        pypowsybl network. For ``initialize_from_solution`` (recommended) and for VSC stations, run an AC load flow
        on it first.
    slack_bus_id
        Calculated bus (``network.get_buses()`` index) holding the slack. Default: the bus of the largest voltage
        regulating generator of the main component. To reproduce a pypowsybl solution, pass the load flow's reference
        bus (``ComponentResult.reference_bus_id``).
    base_mva, frequency_hz
        System base and frequency.
    initialize_from_solution
        Start ANDES from the bus voltages and angles stored in the network (when available).

    Returns
    -------
    andes.System
        With ``system.conversion_report`` (a ``ConversionReport``). Bus names are the pypowsybl bus ids and branch
        names the pypowsybl branch ids.
    """
    report = ConversionReport()
    system = andes.System(no_output=True, default_config=True)
    system.config.mva = base_mva
    system.config.freq = frequency_hz
    system.PQ.config.pq2z = 0  # keep loads at constant power, like pypowsybl

    buses = network.get_buses()
    main_component_buses = buses[buses["synchronous_component"] == 0]
    nominal_voltage_kv_by_level = network.get_voltage_levels()["nominal_v"]
    nominal_voltage_kv_by_bus_id = main_component_buses["voltage_level_id"].map(nominal_voltage_kv_by_level)
    has_solution = initialize_from_solution and bool(main_component_buses["v_mag"].notna().any())

    andes_bus_index_by_bus_id = {bus_id: position + 1 for position, bus_id in enumerate(main_component_buses.index)}
    _add_buses(system, main_component_buses, nominal_voltage_kv_by_bus_id, andes_bus_index_by_bus_id, has_solution)
    report.count("buses", len(andes_bus_index_by_bus_id))

    def is_in_main_component(bus_ids: pd.Series) -> pd.Series:
        return bus_ids.isin(andes_bus_index_by_bus_id)

    def to_pu_power(power_mw: float) -> float:
        return float(power_mw) / base_mva

    context = _ConversionContext(
        system=system,
        report=report,
        base_mva=base_mva,
        main_component_buses=main_component_buses,
        nominal_voltage_kv_by_bus_id=nominal_voltage_kv_by_bus_id,
        andes_bus_index_by_bus_id=andes_bus_index_by_bus_id,
        has_solution=has_solution,
        implausible_target_count=0,
        not_started_count=0,
        is_in_main_component=is_in_main_component,
        to_pu_power=to_pu_power,
    )

    generators = network.get_generators(all_attributes=True)
    generators = generators[generators["connected"] & is_in_main_component(generators["bus_id"])]
    slack_bus_id = slack_bus_id or _default_slack_bus_id(generators)
    if slack_bus_id not in andes_bus_index_by_bus_id:
        raise ValueError(f"Slack bus {slack_bus_id!r} is not a bus of the main synchronous component")

    _add_loads(context, network)
    _add_batteries(context, network)
    _add_generators(context, generators, slack_bus_id)
    _add_static_var_compensators(context, network)
    _add_shunt_compensators(context, network)
    _add_vsc_stations(context, network)
    _add_lines(context, network)
    _add_two_windings_transformers(context, network)
    _warn_about_unsupported_elements(context, network)

    system.setup()
    system.conversion_report = report
    return system


class _ConversionContext:
    """Everything the element converters share."""

    def __init__(self, **attributes) -> None:
        self.__dict__.update(attributes)

    def bus_nominal_kv(self, bus_id: str) -> float:
        return float(self.nominal_voltage_kv_by_bus_id[bus_id])

    def bus_index(self, bus_id: str) -> int:
        return self.andes_bus_index_by_bus_id[bus_id]

    def solved_voltage_pu(self, bus_id: str) -> float:
        v_mag_kv = self.main_component_buses.at[bus_id, "v_mag"]
        return float(v_mag_kv) / self.bus_nominal_kv(bus_id) if self.has_solution and pd.notna(v_mag_kv) else 1.0


def _add_buses(system, main_component_buses, nominal_voltage_kv_by_bus_id, andes_bus_index_by_bus_id, has_solution):
    for bus_id, bus in main_component_buses.iterrows():
        nominal_kv = float(nominal_voltage_kv_by_bus_id[bus_id])
        solved = has_solution and pd.notna(bus["v_mag"])
        system.add(
            "Bus",
            {
                "idx": andes_bus_index_by_bus_id[bus_id],
                "name": bus_id,
                "Vn": nominal_kv,
                "v0": float(bus["v_mag"]) / nominal_kv if solved else 1.0,
                "a0": float(np.radians(bus["v_angle"])) if solved else 0.0,
            },
        )


def _default_slack_bus_id(generators: pd.DataFrame) -> str:
    regulating_generators = generators[generators["voltage_regulator_on"]]
    candidates = regulating_generators if not regulating_generators.empty else generators
    if candidates.empty:
        raise ValueError("No generator in the main component to host the slack: pass slack_bus_id")
    return candidates.loc[candidates["max_p"].idxmax(), "bus_id"]


def _add_pq(context, name_suffix: str, bus_id: str, active_power_mw: float, reactive_power_mvar: float) -> None:
    context.system.add(
        "PQ",
        {
            "bus": context.bus_index(bus_id),
            "Vn": context.bus_nominal_kv(bus_id),
            "p0": context.to_pu_power(active_power_mw),
            "q0": context.to_pu_power(reactive_power_mvar),
            "name": name_suffix,
        },
    )


def _add_loads(context, network) -> None:
    loads = network.get_loads()
    loads = loads[loads["connected"] & context.is_in_main_component(loads["bus_id"])]
    for load_id, load in loads.iterrows():
        _add_pq(context, load_id, load["bus_id"], load["p0"], load["q0"])
    context.report.count("loads", len(loads))


def _add_batteries(context, network) -> None:
    batteries = network.get_batteries()
    batteries = batteries[batteries["connected"] & context.is_in_main_component(batteries["bus_id"])]
    for battery_id, battery in batteries.iterrows():
        # Generator convention (target_p > 0 = injection) -> negative load.
        _add_pq(context, battery_id, battery["bus_id"], -battery["target_p"], -battery["target_q"])
    context.report.count("batteries (as PQ)", len(batteries))


def _generator_initial_reactive_power_mvar(generator: pd.Series, has_solution: bool) -> float:
    """Injected reactive power: solved value if known, else the target, else 0."""
    if has_solution and pd.notna(generator["q"]):
        return -float(generator["q"])
    return float(generator["target_q"]) if pd.notna(generator["target_q"]) else 0.0


def _generator_reactive_limits_mvar(generator: pd.Series) -> tuple[float, float]:
    minimum = generator["min_q_at_target_p"]
    maximum = generator["max_q_at_target_p"]
    if pd.isna(minimum) or pd.isna(maximum):
        return -9999.0, 9999.0
    return float(minimum), float(maximum)


def _add_generators(context, generators: pd.DataFrame, slack_bus_id: str) -> None:
    system, to_pu_power = context.system, context.to_pu_power
    slack_generators = []
    remote_regulation_count = 0
    for generator_id, generator in generators.iterrows():
        bus_id = generator["bus_id"]
        is_voltage_regulating = _is_regulating_voltage(context, generator)
        if not is_voltage_regulating:
            _add_pq(context, generator_id, bus_id, -generator["target_p"], -_generator_reactive_power_setpoint(generator))
            context.report.count("generators (as PQ)")
            continue
        if bus_id == slack_bus_id:
            slack_generators.append((generator_id, generator))
            continue

        voltage_setpoint_pu, is_remote = _voltage_setpoint_pu(context, generator)
        remote_regulation_count += is_remote
        minimum_q, maximum_q = _generator_reactive_limits_mvar(generator)
        system.add(
            "PV",
            {
                "name": generator_id,
                "bus": context.bus_index(bus_id),
                "Vn": context.bus_nominal_kv(bus_id),
                "p0": to_pu_power(generator["target_p"]),
                "q0": to_pu_power(_generator_initial_reactive_power_mvar(generator, context.has_solution)),
                "pmax": to_pu_power(generator["max_p"]),
                "pmin": to_pu_power(generator["min_p"]),
                "qmax": to_pu_power(maximum_q),
                "qmin": to_pu_power(minimum_q),
                "v0": voltage_setpoint_pu,
            },
        )
        context.report.count("generators (as PV)")

    _add_slack(context, slack_bus_id, slack_generators)
    if context.not_started_count:
        context.report.warn(
            f"{context.not_started_count} generators are not started (target_p outside [min_p, max_p]): "
            "they do not regulate voltage (as in OpenLoadFlow) and are modelled as fixed PQ"
        )
    if context.implausible_target_count:
        context.report.warn(
            f"{context.implausible_target_count} generators have a voltage target outside "
            f"[{MINIMUM_PLAUSIBLE_TARGET_VOLTAGE_PU}, {MAXIMUM_PLAUSIBLE_TARGET_VOLTAGE_PU}] pu: they do not "
            "regulate (as in OpenLoadFlow) and are modelled as fixed PQ"
        )
    if remote_regulation_count:
        context.report.warn(
            f"{remote_regulation_count} generators regulate a remote bus: ANDES cannot, they regulate their own bus "
            "(at the solved voltage if the network is solved, else at the target converted to their own bus)"
        )


def _is_plausible_voltage_target(target_kv: float, nominal_kv: float) -> bool:
    return MINIMUM_PLAUSIBLE_TARGET_VOLTAGE_PU <= target_kv / nominal_kv <= MAXIMUM_PLAUSIBLE_TARGET_VOLTAGE_PU


def _is_regulating_voltage(context, generator: pd.Series) -> bool:
    """
    A generator regulates if its regulator is on, it is started (target_p within [min_p, max_p]) and its voltage
    target is plausible: same rules as OpenLoadFlow.
    """
    if not bool(generator["voltage_regulator_on"]) or pd.isna(generator["target_v"]):
        return False
    if not generator["min_p"] <= generator["target_p"] <= generator["max_p"]:
        context.not_started_count += 1
        return False
    regulated_bus_id = generator["regulated_bus_id"]
    regulated_nominal_kv = context.nominal_voltage_kv_by_bus_id.get(regulated_bus_id, np.nan)
    if np.isnan(regulated_nominal_kv):
        regulated_nominal_kv = context.bus_nominal_kv(generator["bus_id"])
    if not _is_plausible_voltage_target(float(generator["target_v"]), float(regulated_nominal_kv)):
        context.implausible_target_count += 1
        return False
    return True


def _generator_reactive_power_setpoint(generator: pd.Series) -> float:
    return float(generator["target_q"]) if pd.notna(generator["target_q"]) else 0.0


def _voltage_setpoint_pu(context, generator: pd.Series) -> tuple[float, bool]:
    """Voltage setpoint of a regulating generator, in pu of its own bus, and whether the regulation is remote."""
    own_bus_id = generator["bus_id"]
    regulated_bus_id = generator["regulated_bus_id"]
    is_remote = pd.notna(regulated_bus_id) and regulated_bus_id != own_bus_id
    if not is_remote:
        return float(generator["target_v"]) / context.bus_nominal_kv(own_bus_id), False
    if context.has_solution:
        return context.solved_voltage_pu(own_bus_id), True
    regulated_nominal_kv = context.nominal_voltage_kv_by_bus_id.get(regulated_bus_id, context.bus_nominal_kv(own_bus_id))
    return float(generator["target_v"]) / float(regulated_nominal_kv), True


def _add_slack(context, slack_bus_id: str, slack_generators: list) -> None:
    """One Slack on the slack bus, aggregating the voltage regulating generators connected there (if any)."""
    to_pu_power = context.to_pu_power
    bus_voltage_pu = context.solved_voltage_pu(slack_bus_id)
    bus_angle_rad = float(np.radians(context.main_component_buses.at[slack_bus_id, "v_angle"])) if context.has_solution else 0.0
    if np.isnan(bus_angle_rad):
        bus_angle_rad = 0.0

    parameters = {
        "name": f"slack@{slack_bus_id}",
        "bus": context.bus_index(slack_bus_id),
        "Vn": context.bus_nominal_kv(slack_bus_id),
        "v0": bus_voltage_pu,
        "a0": bus_angle_rad,
    }
    if slack_generators:
        generators = pd.DataFrame([generator for _, generator in slack_generators])
        limits = [_generator_reactive_limits_mvar(generator) for _, generator in slack_generators]
        parameters.update(
            {
                "name": f"slack@{slack_bus_id}({len(slack_generators)} generators)",
                "p0": to_pu_power(generators["target_p"].sum()),
                "pmax": to_pu_power(generators["max_p"].sum()),
                "pmin": to_pu_power(generators["min_p"].sum()),
                "qmax": to_pu_power(sum(maximum for _, maximum in limits)),
                "qmin": to_pu_power(sum(minimum for minimum, _ in limits)),
                "v0": float(generators["target_v"].iloc[0]) / context.bus_nominal_kv(slack_bus_id),
            }
        )
    context.system.add("Slack", parameters)
    context.report.count("slack", 1)


def _add_static_var_compensators(context, network) -> None:
    static_var_compensators = network.get_static_var_compensators(all_attributes=True)
    static_var_compensators = static_var_compensators[
        static_var_compensators["connected"] & context.is_in_main_component(static_var_compensators["bus_id"])
    ]
    for compensator_id, compensator in static_var_compensators.iterrows():
        bus_id = compensator["bus_id"]
        nominal_kv = context.bus_nominal_kv(bus_id)
        is_regulating_voltage = (
            compensator["regulation_mode"] == "VOLTAGE"
            and bool(compensator["regulating"])
            and _is_plausible_voltage_target(float(compensator["target_v"]), nominal_kv)
        )
        if is_regulating_voltage:
            # Reactive power at nominal voltage: Q [Mvar] = b [S] * V [kV]^2.
            context.system.add(
                "PV",
                {
                    "name": compensator_id,
                    "bus": context.bus_index(bus_id),
                    "Vn": nominal_kv,
                    "p0": 0.0,
                    "q0": context.to_pu_power(-compensator["q"]) if context.has_solution and pd.notna(compensator["q"]) else 0.0,
                    "pmax": 0.0,
                    "pmin": 0.0,
                    "qmax": context.to_pu_power(compensator["b_max"] * nominal_kv**2),
                    "qmin": context.to_pu_power(compensator["b_min"] * nominal_kv**2),
                    "v0": float(compensator["target_v"]) / nominal_kv,
                },
            )
        else:
            reactive_power_mvar = compensator["target_q"] if compensator["regulation_mode"] == "REACTIVE_POWER" else 0.0
            _add_pq(context, compensator_id, bus_id, 0.0, -float(np.nan_to_num(reactive_power_mvar)))
    context.report.count("static var compensators", len(static_var_compensators))


def _add_shunt_compensators(context, network) -> None:
    shunt_compensators = network.get_shunt_compensators(all_attributes=True)
    shunt_compensators = shunt_compensators[
        shunt_compensators["connected"] & context.is_in_main_component(shunt_compensators["bus_id"])
    ]
    for shunt_id, shunt in shunt_compensators.iterrows():
        bus_id = shunt["bus_id"]
        impedance_base_ohm = context.bus_nominal_kv(bus_id) ** 2 / context.base_mva
        # LINEAR models give g and b per section; NON_LINEAR ones already give the value of the current section.
        section_count = float(shunt["section_count"]) if shunt["model_type"] == "LINEAR" else 1.0
        context.system.add(
            "Shunt",
            {
                "name": shunt_id,
                "bus": context.bus_index(bus_id),
                "Vn": context.bus_nominal_kv(bus_id),
                "Sn": context.base_mva,
                "g": float(shunt["g"]) * section_count * impedance_base_ohm,
                "b": float(shunt["b"]) * section_count * impedance_base_ohm,
            },
        )
    context.report.count("shunt compensators", len(shunt_compensators))


def _add_vsc_stations(context, network) -> None:
    stations = network.get_vsc_converter_stations(all_attributes=True)
    stations = stations[stations["connected"] & context.is_in_main_component(stations["bus_id"])]
    if stations.empty:
        return
    for station_id, station in stations.iterrows():
        if context.has_solution and pd.notna(station["p"]) and pd.notna(station["q"]):
            active_power_mw, reactive_power_mvar = float(station["p"]), float(station["q"])
        else:
            active_power_mw = 0.0
            reactive_power_mvar = -float(np.nan_to_num(station["target_q"]))
            context.report.warn(f"VSC station {station_id}: no solved state, active power set to 0")
        # Results are in load convention (positive = consumption), like PQ.
        _add_pq(context, station_id, station["bus_id"], active_power_mw, reactive_power_mvar)
    context.report.count("VSC stations (as fixed PQ)", len(stations))


def _add_fixed_shunt(context, bus_id: str, name: str, admittance_pu: complex) -> None:
    context.system.add(
        "Shunt",
        {
            "name": name,
            "bus": context.bus_index(bus_id),
            "Vn": context.bus_nominal_kv(bus_id),
            "Sn": context.base_mva,
            "g": float(admittance_pu.real),
            "b": float(admittance_pu.imag),
        },
    )


def _open_ended_branch_shunt(context, bus_id: str, name: str, admittance_pu: complex) -> None:
    """A branch connected at one end only draws its input admittance: model it as a Shunt."""
    if abs(admittance_pu) == 0.0:
        return
    _add_fixed_shunt(context, bus_id, f"{name}(open end)", admittance_pu)
    context.report.count("open-ended branches (as Shunt)")


def _add_lines(context, network) -> None:
    lines = network.get_lines()
    base_mva = context.base_mva
    degenerate_impedance_count = 0
    different_nominal_voltage_count = 0
    for line_id, line in lines.iterrows():
        bus1_id = line["bus1_id"] if line["bus1_id"] in context.andes_bus_index_by_bus_id else None
        bus2_id = line["bus2_id"] if line["bus2_id"] in context.andes_bus_index_by_bus_id else None
        if bus1_id is None and bus2_id is None:
            continue
        nominal_kv_1 = context.bus_nominal_kv(bus1_id) if bus1_id else None
        nominal_kv_2 = context.bus_nominal_kv(bus2_id) if bus2_id else None
        base_kv = nominal_kv_1 if nominal_kv_1 is not None else nominal_kv_2
        impedance_base_ohm = base_kv**2 / base_mva
        if nominal_kv_1 and nominal_kv_2 and not np.isclose(nominal_kv_1, nominal_kv_2):
            different_nominal_voltage_count += 1

        series_impedance_pu = complex(line["r"], line["x"]) / impedance_base_ohm
        shunt_1_pu = complex(line["g1"], line["b1"]) * impedance_base_ohm
        shunt_2_pu = complex(line["g2"], line["b2"]) * impedance_base_ohm

        if bus1_id and bus2_id:
            if abs(series_impedance_pu) < MINIMUM_BRANCH_IMPEDANCE_PU:
                degenerate_impedance_count += 1
            symmetric_shunt_pu = shunt_1_pu + shunt_2_pu  # ANDES puts half of g, b at each end
            context.system.add(
                "Line",
                {
                    "name": line_id,
                    "bus1": context.bus_index(bus1_id),
                    "bus2": context.bus_index(bus2_id),
                    "Sn": base_mva,
                    "Vn1": nominal_kv_1,
                    "Vn2": nominal_kv_2,
                    "r": series_impedance_pu.real,
                    "x": series_impedance_pu.imag,
                    "g": symmetric_shunt_pu.real,
                    "b": symmetric_shunt_pu.imag,
                },
            )
            asymmetry_pu = (shunt_1_pu - shunt_2_pu) / 2
            if abs(asymmetry_pu) > MINIMUM_SHUNT_ADMITTANCE_PU:
                _add_fixed_shunt(context, bus1_id, f"{line_id}(asymmetry 1)", asymmetry_pu)
                _add_fixed_shunt(context, bus2_id, f"{line_id}(asymmetry 2)", -asymmetry_pu)
            context.report.count("lines")
        elif bus1_id:
            _open_ended_branch_shunt(
                context, bus1_id, line_id, shunt_1_pu + _input_admittance(series_impedance_pu, shunt_2_pu)
            )
        else:
            _open_ended_branch_shunt(
                context, bus2_id, line_id, shunt_2_pu + _input_admittance(series_impedance_pu, shunt_1_pu)
            )

    if degenerate_impedance_count:
        context.report.warn(
            f"{degenerate_impedance_count} lines have |z| < {MINIMUM_BRANCH_IMPEDANCE_PU} pu: ill-conditioned for ANDES"
        )
    if different_nominal_voltage_count:
        context.report.warn(
            f"{different_nominal_voltage_count} lines join voltage levels with different nominal voltages: "
            "modelled with a unit tap on the nominal voltage of bus 1"
        )


def _input_admittance(series_impedance: complex, far_end_shunt_admittance: complex) -> complex:
    """Admittance seen at one end of a series impedance whose other end only has a shunt to ground."""
    if far_end_shunt_admittance == 0:
        return 0.0
    return 1.0 / (series_impedance + 1.0 / far_end_shunt_admittance)


def _add_two_windings_transformers(context, network) -> None:
    transformers = network.get_2_windings_transformers(all_attributes=True)
    base_mva = context.base_mva
    degenerate_impedance_count = 0
    for transformer_id, transformer in transformers.iterrows():
        bus1_id = transformer["bus1_id"] if transformer["bus1_id"] in context.andes_bus_index_by_bus_id else None
        bus2_id = transformer["bus2_id"] if transformer["bus2_id"] in context.andes_bus_index_by_bus_id else None
        if bus1_id is None and bus2_id is None:
            continue
        # Nominal voltages of the voltage levels (fall back on the rated voltages when a side is not in the component).
        nominal_kv_1 = context.bus_nominal_kv(bus1_id) if bus1_id else float(transformer["rated_u1"])
        nominal_kv_2 = context.bus_nominal_kv(bus2_id) if bus2_id else float(transformer["rated_u2"])

        # powsybl: r, x, g, b at side 2 (values at the current tap), ideal transformer on side 1.
        impedance_base_ohm = nominal_kv_2**2 / base_mva
        series_impedance_pu = complex(transformer["r_at_current_tap"], transformer["x_at_current_tap"]) / impedance_base_ohm
        shunt_admittance_pu = complex(transformer["g_at_current_tap"], transformer["b_at_current_tap"]) * impedance_base_ohm
        # ANDES: node voltage = v1 / tap (a1 - phi), so tap = 1 / (rho * Vn1 / Vn2), phi = -alpha.
        tap = nominal_kv_2 / (float(transformer["rho"]) * nominal_kv_1)
        phase_shift_rad = -float(np.radians(transformer["alpha"])) if pd.notna(transformer["alpha"]) else 0.0

        if bus1_id and bus2_id:
            if abs(series_impedance_pu) < MINIMUM_BRANCH_IMPEDANCE_PU:
                degenerate_impedance_count += 1
            context.system.add(
                "Line",
                {
                    "name": transformer_id,
                    "bus1": context.bus_index(bus1_id),
                    "bus2": context.bus_index(bus2_id),
                    "Sn": base_mva,
                    "Vn1": nominal_kv_1,
                    "Vn2": nominal_kv_2,
                    "r": series_impedance_pu.real,
                    "x": series_impedance_pu.imag,
                    "tap": tap,
                    "phi": phase_shift_rad,
                },
            )
            context.report.count("2-winding transformers")
            if abs(shunt_admittance_pu) > MINIMUM_SHUNT_ADMITTANCE_PU:
                _add_fixed_shunt(context, bus1_id, f"{transformer_id}(magnetizing)", shunt_admittance_pu / tap**2)
        elif bus1_id:
            # Side 2 open: only the shunt at the inner node remains, seen from bus 1 through the ideal transformer.
            _open_ended_branch_shunt(context, bus1_id, transformer_id, shunt_admittance_pu / tap**2)
        else:
            # Side 1 open: series impedance in series with the shunt, seen from bus 2.
            _open_ended_branch_shunt(
                context, bus2_id, transformer_id, _input_admittance(series_impedance_pu, shunt_admittance_pu)
            )

    if degenerate_impedance_count:
        context.report.warn(
            f"{degenerate_impedance_count} transformers have |z| < {MINIMUM_BRANCH_IMPEDANCE_PU} pu: "
            "ill-conditioned for ANDES"
        )


def _warn_about_unsupported_elements(context, network) -> None:
    for description, elements in (
        ("3-winding transformers", network.get_3_windings_transformers()),
        ("dangling lines", network.get_dangling_lines()),
        ("LCC converter stations", network.get_lcc_converter_stations()),
    ):
        if len(elements):
            context.report.warn(f"{len(elements)} {description} are not converted")
