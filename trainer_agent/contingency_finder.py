"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import copy
import itertools
import json
import math
import multiprocessing as mp
import numpy as np
import pandas as pd
import pandapower as pp
import pypowsybl as ps

from tqdm import tqdm

from clusters import get_clusters
from dc_sensitivity_factors import DCSensitivityFactors
from opf import powsybl2pandapower, pp_opf, _setup_redispatch_cost, fcr
from voltage_instability import min_singular_value, l_index

network = None
INCREASE_LOAD_PERCENT = 30
# Contingency name -> seconds before its first overload. Set in find_contingency before the worker
# pool is forked, so the workers inherit it.
time_available_by_contingency = {}


def _initialize_worker(worker_pp_net, worker_mode, worker_time_available_by_contingency):
    """Pool initializer: spawned workers do not inherit the parent's globals, so they are set here."""
    global pp_net, global_mode, time_available_by_contingency
    pp_net = worker_pp_net
    global_mode = worker_mode
    time_available_by_contingency = worker_time_available_by_contingency


def change_contingency_state_ps(network, contingency_name, connected):
        if contingency_name in network.get_branches().index:
            network.update_branches(id=contingency_name, connected1=connected, connected2=connected)
        else:
            network.update_generators(id=contingency_name, connected=connected)

def change_contingency_state_pp(pp_net, contingency_name, connected):
        line_idx = pp_net.line["name"] == contingency_name
        if np.sum(line_idx) > 0:
            pp_net.line.loc[line_idx, "in_service"] = connected
        else:
            trafo_idx = pp_net.trafo["name"] == contingency_name
            pp_net.trafo.loc[trafo_idx, "in_service"] = connected

def control_loss_opf(pp_net, name):
    if global_mode == "vsi":
        pp.runpp(pp_net)
        msv = min_singular_value(pp_net)
        li = l_index(pp_net)[1]
        return [[name, msv, li]]
    else:
        _, difficulty, cost, p_redispatch = pp_opf(pp_net, pre_check="load" in name or "gen" in name,
                                                available_time=time_available_by_contingency.get(name))

        abs_redispatch = np.abs(p_redispatch)
        difficulty_10 = np.sum(abs_redispatch > 10) if difficulty >= 0 else -1
        to_ret = [[name, difficulty, difficulty_10, np.sum(abs_redispatch > 100), cost, np.sum(np.abs(p_redispatch))]]

        if False and difficulty_10 > 0:
            biggest_redispatch_idx = np.argsort(-abs_redispatch) # descending=True only available from newer numpy version, which seem incompatbile with pandapower
            biggest_redispatch_idx = biggest_redispatch_idx[:difficulty_10]

            for i in range(len(biggest_redispatch_idx)):
                controllable_mask = biggest_redispatch_idx.values[:i+1]

                previous_controllable = copy.deepcopy(pp_net.gen.loc[controllable_mask, "controllable"])
                pp_net.gen.loc[controllable_mask, "controllable"] = False
                _, difficulty_cl, cost_cl, p_redispatch_cl = pp_opf(pp_net)
                pp_net.gen.loc[controllable_mask, "controllable"] = previous_controllable

                to_ret.append([name + f"_control_loss_{i + 1}", difficulty_cl, np.sum(np.abs(p_redispatch_cl) > 10), 
                                    np.sum(np.abs(p_redispatch_cl) > 100), cost_cl, np.sum(np.abs(p_redispatch))])
    
        return to_ret


def load_contingency(i, el_group):
    pp_net.load.loc[el_group.index, "p_mw"] *= 1 + INCREASE_LOAD_PERCENT / 100.
    
    # pp_net gen table is change inside pandapower opf (to add dclines eq)
    to_ret = control_loss_opf(pp_net, "load" + i)

    pp_net.load.loc[el_group.index, "p_mw"] /= 1 + INCREASE_LOAD_PERCENT / 100.

    return to_ret

def gen_contingency(i, el_group):
    previous_p = pp_net.gen.loc[el_group.index, "p_mw"].copy()
                                
    pp_net.gen.loc[el_group.index, "p_mw"] *= 1 + INCREASE_LOAD_PERCENT / 100.
    pp_net.gen["p_mw"] = pp_net.gen[["max_p_mw", "p_mw"]].min(axis=1)
    to_ret = control_loss_opf(pp_net, "gen" + i)

    pp_net.gen.loc[el_group.index, "p_mw"] = previous_p

    return to_ret


def single_power_contingencies():
    pp_net = powsybl2pandapower(network)

    previous_load = None
    for load_id in pp_net.load.index:
        pp_net.load.loc[load_id, "p_mw"] *= 1.3
        if previous_load is not None:
            pp_net.load.loc[previous_load, "p_mw"] /= 1.3
        previous_load = load_id
        
        converged, difficulty, cost, p_redispatch = pp_opf(pp_net)
        print(load_id, difficulty, cost)

def compute_overflow_PI(pp_net):
    pp.rundcpp(pp_net)#pp_net = dcpf(pp_net)

    overflows_idx = pp_net.res_line["loading_percent"] > 100
    line_PI = pp_net.res_line["loading_percent"][pp_net.line["in_service"] & overflows_idx] / 100
    line_PI = line_PI ** 2

    overflows_idx = pp_net.res_trafo["loading_percent"] > pp_net.trafo["max_loading_percent"]
    trafo_PI = pp_net.res_trafo["loading_percent"][pp_net.trafo["in_service"] & overflows_idx] / pp_net.trafo["max_loading_percent"]
    trafo_PI = trafo_PI ** 2

    return line_PI.sum() + trafo_PI.sum()

def branches_contingencies(elements):
    # Necessary to setup cost again as it could have been changed with generators contingencies
    if global_mode == "opf":
        _setup_redispatch_cost(pp_net)
    to_ret = []
    for contingency in tqdm(elements):
        change_contingency_state_pp(pp_net, contingency, False)
        # overflow_PI = compute_overflow_PI(pp_net)
        # contingencies.loc[contingency, "overflow_PI"] = overflow_PI
        results = control_loss_opf(pp_net, contingency)

        for res in results:
            to_ret.append(res)

        change_contingency_state_pp(pp_net, contingency, True)
    
    return to_ret

def n_minus_2_contingencies(pairs):
    to_ret = []

    for pair in tqdm(pairs):
        change_contingency_state_pp(pp_net, pair[0], False)
        change_contingency_state_pp(pp_net, pair[1], False)

        results = control_loss_opf(pp_net, f"{pair[0]}_+_{pair[1]}")

        for res in results:
            to_ret.append(res)

        change_contingency_state_pp(pp_net, pair[0], True)
        change_contingency_state_pp(pp_net, pair[1], True)

    return to_ret
        
def run_security_analysis(elements, verbose=True):
    global network, params, voltage_levels
    security_analysis = ps.security.create_analysis()
    security_analysis.add_single_element_contingencies(elements)
    report_node = ps.report.ReportNode()if verbose else None
    result = security_analysis.run_ac(network, params, report_node=report_node)
    
    if result.pre_contingency_result.status != ps.loadflow.ComponentStatus.CONVERGED:
        print("Could not converge with current network state !")    
            
    if verbose:
        print("Security Analysis")
        # print(report_node)
    contingencies = {}

    violations = result.limit_violations
    violations = violations.reset_index()
    violations = pd.merge(violations, network.get_voltage_levels()[["nominal_v"]], left_on="subject_id", right_on="id", how="left")
    violations["PI"] = violations.apply(
        lambda row: 
        row["value"] / row["limit"] 
        if row["limit_type"] == "CURRENT" 
        else (row["value"] - row["nominal_v"]) / (row["limit"] - row["nominal_v"]), axis=1)

    violations["PI"] = violations["PI"] ** 2

    contingencies = violations.groupby("contingency_id")["PI"].sum().to_frame()
        
    failing_contingencies = []
    for key, res in result.post_contingency_results.items():
        if res.status != ps.security.ComputationStatus.CONVERGED:
            print("Convergence problem with ", key) 
            failing_contingencies.append(key)

    loads = network.get_loads()
    generators = network.get_generators()

    load_shedding_factors = {}

    for failing_contingency in tqdm(failing_contingencies):
        change_contingency_state_ps(network, failing_contingency, False)
        converged = False
        factor = 0.99
        while not converged and factor >= 0:        
            network.update_loads(loads[["p0", "q0"]] * factor)
            network.update_generators(generators[["target_p"]] * factor)
            sol = ps.loadflow.run_ac(network, params)
            converged = (sol[0].status == ps.loadflow.ComponentStatus.CONVERGED)
            factor -= 0.01

        if not converged:
            print(failing_contingency, "unsolvable")
            load_shedding_factors[failing_contingency] = [0]
        else:
            print(failing_contingency, "solved with factor", factor)
            load_shedding_factors[failing_contingency] = [factor]
        change_contingency_state_ps(network, failing_contingency, True)
    
    network.update_loads(loads[["p0", "q0"]])
    network.update_generators(generators[["target_p"]])   
    load_shedding_factors = pd.DataFrame.from_dict(load_shedding_factors, orient="index", columns=["PI"])
    return contingencies, (1 - load_shedding_factors) * 999999

class ContingencyFinder:

    def __init__(self, net=None, n_jobs=10, mode="opf", governor_kgover=None):
        self.n_jobs = n_jobs
        self.mode = mode
        global params, global_mode
        global_mode = mode
        
        params = ps.loadflow.Parameters(transformer_voltage_control_on=True, distributed_slack=True, voltage_init_mode=ps.loadflow.VoltageInitMode.DC_VALUES)

        self.applied_contingencies = []

        if net is not None:
            self.update_network(net, governor_kgover)

    def update_network(self, net, governor_kgover=None, loadflow=True):
        global network, pp_net, voltage_levels
        network = net

        if self.mode in ["opf", "vsi"]:
            if loadflow:
                generators = network.get_generators()
                generators["target_p"] = -generators["p"]
                network.update_generators(generators[["target_p"]])
                loads = network.get_loads()
                loads["p0"] = loads["p"]
                network.update_loads(loads[["p0"]])
                params = ps.loadflow.Parameters(balance_type=ps.loadflow.BalanceType.PROPORTIONAL_TO_LOAD)
                if self.mode == "opf":
                    ps.loadflow.run_dc(network, params)

            pp_net = powsybl2pandapower(network, governor_kgover)
            if self.mode == "opf":
                # This is just to remove some annoying warning related to voltage that has no impact in the case of a DCOPF
                pp_net.gen["vm_pu"] = 1.0

            adjusted_gen = fcr(pp_net)
            pp_net.gen["p_mw"] = adjusted_gen
            # Generators setpoints can be below min (for example if they are starting). They are then not controllable
            pp_net.gen.loc[pp_net.gen["p_mw"] < pp_net.gen["min_p_mw"], "controllable"] = False
            pp_net.gen["min_p_mw"] = pp_net.gen[["min_p_mw", "p_mw"]].min(axis=1)
            # Generators are sometimes slightly above max (from iidm sent by Game Master, was not the case in the docs/example file)
            pp_net.gen["max_p_mw"] = pp_net.gen[["max_p_mw", "p_mw"]].max(axis=1)
            self.pp_net = pp_net

            substation_clusters = get_clusters(25)

            self.load_groups = self.prepare_group_power_contingencies(substation_clusters, "load")
            self.gen_groups = self.prepare_group_power_contingencies(substation_clusters, "gen")
            if self.mode == "opf":
                self.sensitivity_factors = DCSensitivityFactors(pp_net, network.get_operational_limits())
        else:
            voltage_levels = network.get_voltage_levels()
            voltage_levels = voltage_levels[voltage_levels["nominal_v"] > 100]
            voltage_tolerance = 0.1
            # Overwrite iidm voltage limits
            voltage_levels["low_voltage_limit"] = voltage_levels["nominal_v"] * (1 - voltage_tolerance)
            voltage_levels["high_voltage_limit"] = voltage_levels["nominal_v"] * (1 + voltage_tolerance)
            #voltage_levels["low_voltage_limit"] = (1 - (voltage_levels["high_voltage_limit"] / voltage_levels["nominal_v"] - 1)) * voltage_levels["nominal_v"]
            network.update_voltage_levels(voltage_levels[["low_voltage_limit", "high_voltage_limit"]])
            # security_analysis = ps.security.create_analysis()
            # params = ps.loadflow.Parameters(transformer_voltage_control_on=True, distributed_slack=True)
            # result = security_analysis.run_ac(network, params)
            # ps.loadflow.run_ac(network, params)
            print()

    def prepare_group_power_contingencies(self, substation_clusters, type):
        # type is either load or gen
        
        if type == "gen":
            pp_elements = self.pp_net.gen
            ps_elements = network.get_generators()
        else:
            pp_elements = self.pp_net.load
            ps_elements = network.get_loads()
        
        ps_elements = ps_elements[ps_elements["connected"]]

        ps_elements = ps_elements.join(network.get_voltage_levels()[["substation_id"]], on="voltage_level_id").join(network.get_substations()[["country"]], on="substation_id")
        ps_elements = pd.merge(ps_elements.reset_index(), substation_clusters, how="left", on="substation_id")

        pp_elements_group = pd.merge(pp_elements, ps_elements, left_on="name", right_on="id")
        pp_elements_group.loc[pp_elements_group["group"].isna(), "group"] = pp_elements_group.loc[pp_elements_group["group"].isna(), "country"]

        if type == "gen":
            pp_elements_group = pp_elements_group[pp_elements_group["type"].isin(["solar", "wind"])] 

        return pp_elements_group.groupby("group")

    def screen_load_groups(self):
        """Load groups whose change of INCREASE_LOAD_PERCENT overloads a branch (FCR model, PTDF only).
        Also stores, for each group, the smallest change that would (self.load_margins)."""
        groups = {name: group.index.values for name, group in self.load_groups}
        fraction = INCREASE_LOAD_PERCENT / 100.
        self.load_margins = self.sensitivity_factors.load_group_margins(groups, direction=1 if fraction >= 0 else -1)
        overloaded = self.sensitivity_factors.load_group_overloads(groups, fraction)
        return [(name, group) for name, group in self.load_groups if name in overloaded], overloaded

    def screen_gen_groups(self):
        """Generator groups whose change of INCREASE_LOAD_PERCENT overloads a branch (FCR model, PTDF only).
        Also stores, for each group, the smallest change that would (self.gen_margins)."""
        groups = {name: group.index.values for name, group in self.gen_groups}
        fraction = INCREASE_LOAD_PERCENT / 100.
        try:
            self.gen_margins = self.sensitivity_factors.gen_group_margins(groups, direction=1 if fraction >= 0 else -1)
            overloaded = self.sensitivity_factors.gen_group_overloads(groups, fraction)
        except NotImplementedError as error:
            # Gens that share the FCR are not supported by the PTDF model: no screening, every group goes to the OPF
            print(f"Generator groups not screened: {error}")
            return list(self.gen_groups), {}
        return [(name, group) for name, group in self.gen_groups if name in overloaded], overloaded

    def initial_simulation(self):
        if self.n_jobs == 1:  
            report_node = ps.report.ReportNode()
            sol = ps.loadflow.run_ac(network, params, report_node=report_node)
            print("Initial simulation")
            print(report_node)
            #network.write_network_area_diagram_svg('initial.svg')
    
    def get_contingency_type(self, contingency_name):
        transformers = network.get_2_windings_transformers()
        generators = network.get_generators()
        lines = network.get_lines()

        if contingency_name in lines.index:
            return "line"
        elif contingency_name in generators.index:
            return "generator"
        elif contingency_name in transformers.index:
            return "transformer"
        else:
            return "group"

    def find_contingency(self, include_failing=True, voltage_thresh=0, include_pairs=False):
        if self.mode == "opf":
            if include_pairs:
                elements, pairs, overloads = self.sensitivity_factors.get_problematic_n_minus_2(voltage_thresh)
            else:
                elements, overloads = self.sensitivity_factors.get_problematic_n_minus_1(voltage_thresh)

            # Groups that do not overload anything need no OPF
            load_groups, load_overloads = self.screen_load_groups()
            gen_groups, gen_overloads = self.screen_gen_groups()
            # Must be set before the pool is created so that forked workers see it
            global time_available_by_contingency
            time_available_by_contingency = {
                **{key if isinstance(key, str) else f"{key[0]}_+_{key[1]}": min(times.values())  for key, times in overloads.items()},
                **{"load" + group_name: min(times.values()) for group_name, times in load_overloads.items()},
                **{"gen" + group_name: min(times.values()) for group_name, times in gen_overloads.items()},
            }
        else:
            transformers = network.get_2_windings_transformers()
            lines = network.get_lines()
             # Only check lines above a certain voltage threshold
            if voltage_thresh > 0:
                vlevels = network.get_voltage_levels()
                lines = lines.join(vlevels["nominal_v"], on="voltage_level1_id")
                elements = list(lines.index[lines["nominal_v"] > voltage_thresh])
                elements += list(transformers.index[transformers["rated_u1"] > voltage_thresh])
            else:
                elements = list(lines.index) 
                elements += list(transformers.index) # + list(generators.index)

            load_groups = self.load_groups
            gen_groups = self.gen_groups

        print("Starting contingency analysis")
        if self.n_jobs > 1:
            if self.mode == "vsi":
                # Forking after BLAS / pypowsybl native runtimes were used hangs or corrupts the children
                # (e.g. ARPACK in svds). Workers are spawned and receive the globals explicitly.
                ctx = mp.get_context('spawn')
                pool_kwargs = dict(initializer=_initialize_worker,
                                   initargs=(pp_net, self.mode, time_available_by_contingency))
            else:
                ctx = mp.get_context('fork')
                pool_kwargs = {}
            with ctx.Pool(self.n_jobs, **pool_kwargs) as pool:
                if self.mode in ["opf", "vsi"]:
                    load_results = pool.starmap_async(load_contingency, load_groups)
                    gen_results = pool.starmap_async(gen_contingency, gen_groups)

                    elements_results = pool.map_async(branches_contingencies, np.array_split(elements, self.n_jobs))
                    if include_pairs:
                        n2_results = pool.map_async(n_minus_2_contingencies, np.array_split(pairs, self.n_jobs))

                    contingencies = list(itertools.chain.from_iterable(load_results.get()))
                    print("Load contingencies computed")
                    contingencies += list(itertools.chain.from_iterable(gen_results.get()))
                    print("Generators contingencies computed")

                    contingencies += list(itertools.chain.from_iterable(elements_results.get()))
                    if include_pairs:
                        contingencies += list(itertools.chain.from_iterable(n2_results.get()))
                else:
                    all_contingencies, all_failing_contingencies = zip(*pool.map(run_security_analysis, np.array_split(elements, self.n_jobs)))
                    contingencies = pd.concat(all_contingencies)
                    failing_contingencies = pd.concat(all_failing_contingencies)
        else:
            if self.mode in ["opf", "vsi"]:
                contingencies = []

                for i, load_group in load_groups:
                    for res in load_contingency(i, load_group):
                        contingencies.append(res)

                for i, gen_group in gen_groups:
                    for res in gen_contingency(i, gen_group):
                        contingencies.append(res)
                
                contingencies = contingencies + branches_contingencies(elements)
                if include_pairs:
                    contingencies += n_minus_2_contingencies(pairs)
            else:
                contingencies, failing_contingencies = run_security_analysis(elements)

        if self.mode == "opf":
            contingencies = pd.DataFrame(contingencies, columns=["id", "difficulty", "difficulty_10", "difficulty_100", "cost", "total redispatch"])
            contingencies = contingencies.set_index("id")
            contingencies["time_available"] = contingencies.index.map(lambda name: time_available_by_contingency.get(name, -1))
        elif self.mode == "vsi":
            contingencies = pd.DataFrame(contingencies, columns=["id", "min_singular_value", "l_index"])
            contingencies = contingencies.set_index("id")
        elif include_failing:
            contingencies = pd.concat((contingencies, failing_contingencies))

        # Avoid returning the same contingency as previously
        for contingency in self.applied_contingencies:
            if contingency in contingencies.index:
                contingencies = contingencies.drop(contingency)

        if len(contingencies) > 0:
            if self.mode != "vsi":
                contingencies = contingencies.sort_values(ascending=False, by="difficulty_10" if self.mode == "opf" else "PI")
            # contingencies = contingencies.to_frame()
            contingencies["component_type"] = contingencies.apply(lambda row: self.get_contingency_type(row.name), axis=1)
            self.contingencies = contingencies
            return contingencies
        else:
            # This is only to be able to return multiple failing contingencies. So return rest of the previous list if we cannot converge anymore
            return self.contingencies

    def get_generators(self, contingency_id):

        return self.pp_net.gen.loc[self.gen_groups.groups[contingency_id[3:]], "name"].values
    
    def get_loads(self, contingency_id):

        return self.pp_net.load.loc[self.load_groups.groups[contingency_id[4:]], "name"].values

    def apply_contingency(self, contingency_name):
        if self.mode == "opf":
            if "gen" in contingency_name:
                self.pp_net.gen.loc[self.gen_groups.groups[contingency_name[3:]], "p_mw"] *= 1 + INCREASE_LOAD_PERCENT / 100.
                self.pp_net.gen["p_mw"] = self.pp_net.gen[["max_p_mw", "p_mw"]].min(axis=1)

            elif "load" in contingency_name:
                self.pp_net.load.loc[self.load_groups.groups[contingency_name[4:]], "p_mw"] *= 1 + INCREASE_LOAD_PERCENT / 100.
            elif "_+_" in contingency_name:
                idx = contingency_name.find("_+_")
                change_contingency_state_pp(self.pp_net, contingency_name[:idx], False)
                change_contingency_state_pp(self.pp_net, contingency_name[idx+3:], False)
            else:
                change_contingency_state_pp(self.pp_net, contingency_name, False)
        else:
            change_contingency_state_ps(network, contingency_name, False)

        self.contingencies = self.contingencies.drop(contingency_name)
        self.applied_contingencies.append(contingency_name)


    def get_overloaded_branch_substations(self):
        init_gen = fcr(self.pp_net)
        pp_net.gen["p_mw"] = init_gen
        pp.rundcpp(pp_net)
        overloaded_branch_names = self._get_overloaded_branch_names()
        v_levels = network.get_voltage_levels()
        branches = network.get_branches()
        branches = branches.loc[list(overloaded_branch_names)]
        v_levels = v_levels.loc[branches["voltage_level2_id"]]
        return v_levels["substation_id"], v_levels.index


    def get_solution(self):
        pp_net.line["max_loading_percent"] *= 0.9
        pp_net.trafo["max_loading_percent"] *= 0.9
        converged, difficulty, cost, p_redispatch = pp_opf(pp_net, True)
        pp_net.line["max_loading_percent"] /= 0.9
        pp_net.trafo["max_loading_percent"] /= 0.9
        redispatch_idx = abs(p_redispatch) > 1
        setpoints = pp_net.gen.loc[redispatch_idx, "p_mw"] + p_redispatch[redispatch_idx]
        setpoints.name = "p_mw" 
        return pd.concat([pp_net.gen.loc[redispatch_idx, "name"], setpoints], axis=1)

    def write_diagram(self):
        sol = ps.loadflow.run_ac(network)
        network.write_network_area_diagram_svg('worst_contingency.svg')

    def write_diagram_from_pp_state(self, file_name="worst_contingency.svg", v_levels=None, depth=3):
        """Write a DC network area diagram on the original pypowsybl network, with the current state of pp_net
        (disconnected branches, generator and load setpoints) copied onto it, to keep real voltage levels."""
        disconnected_branch_names = list(self.pp_net.line.loc[~self.pp_net.line["in_service"], "name"]) \
            + list(self.pp_net.trafo.loc[~self.pp_net.trafo["in_service"], "name"])
        disconnected_branch_names = [name for name in disconnected_branch_names if name in network.get_branches().index]
        network.update_branches(id=disconnected_branch_names,
                                connected1=[False] * len(disconnected_branch_names),
                                connected2=[False] * len(disconnected_branch_names))
        if v_levels is None:
            _, v_levels = self.get_overloaded_branch_substations()
        generator_setpoints = self.pp_net.gen.set_index("name")["p_mw"]
        generator_setpoints = generator_setpoints[generator_setpoints.index.isin(network.get_generators().index)]
        network.update_generators(id=generator_setpoints.index, target_p=generator_setpoints.values)

        load_setpoints = self.pp_net.load.set_index("name")["p_mw"]
        load_setpoints = load_setpoints[load_setpoints.index.isin(network.get_loads().index)]
        network.update_loads(id=load_setpoints.index, p0=load_setpoints.values)

        ps.loadflow.run_dc(network)

        self._set_dc_currents_from_active_power()

        diagram = network.get_network_area_diagram(v_levels, depth=depth, nad_parameters=ps.network.NadParameters(edge_info_parameters=ps.network.EdgeInfoParameters(info_middle_side1=ps.network.EdgeInfoType.VALUE_PERMANENT_LIMIT_PERCENTAGE)))
        overloaded_branch_names = self._get_overloaded_branch_names()
        overloaded_edge_svg_ids = [edge["svgId"] for edge in json.loads(diagram.metadata)["edges"]
                                   if edge["equipmentId"] in overloaded_branch_names]
        svg_content = diagram.svg
        for edge_svg_id in overloaded_edge_svg_ids:
            # pypowsybl's default stylesheet makes edges with the nad-overload class blink
            svg_content = svg_content.replace(f'<g id="{edge_svg_id}">', f'<g id="{edge_svg_id}" class="nad-overload">', 1)
        with open(file_name, "w") as svg_file:
            svg_file.write(svg_content)

    def _set_dc_currents_from_active_power(self):
        """After a DC load flow pypowsybl has no reactive power and no bus voltage magnitude, so branch currents
        are NaN. Currents cannot be written directly, but they are derived from p, q and the bus voltage:
        setting q to 0 and the voltage to the nominal one gives I = P / (sqrt(3) * Vnominal), which makes
        VALUE_PERMANENT_LIMIT_PERCENTAGE displayable."""
        buses = network.get_buses()
        nominal_voltage_kv = network.get_voltage_levels()["nominal_v"]
        network.update_buses(id=buses.index, v_mag=nominal_voltage_kv.loc[buses["voltage_level_id"]].values)
        for branch_ids, update_branches in [(network.get_lines().index, network.update_lines),
                                            (network.get_2_windings_transformers().index, network.update_2_windings_transformers)]:
            if len(branch_ids) > 0:
                zero_reactive_power = np.zeros(len(branch_ids))
                update_branches(id=branch_ids, q1=zero_reactive_power, q2=zero_reactive_power)

    def _get_overloaded_branch_names(self):
        """Names of lines and transformers overloaded in the latest pandapower DC results (run by get_overloaded_branch_substations)."""
        overloaded_lines = pp_net.line[pp_net.res_line["loading_percent"] > pp_net.line["max_loading_percent"]]
        overloaded_trafos = pp_net.trafo[
            np.logical_and(
                pp_net.trafo["max_loading_percent"] > 0,
                pp_net.res_trafo["loading_percent"] > pp_net.trafo["max_loading_percent"]
            )]
        return set(overloaded_lines["name"]) | set(overloaded_trafos["name"])

def check():
    print(np.sum(pp_net.res_bus["vm_pu"] > 1.05))
    print(np.sum(np.logical_and(pp_net.trafo["max_loading_percent"] > 0, pp_net.res_trafo["loading_percent"] > pp_net.trafo["max_loading_percent"])))
    print(np.sum(pp_net.res_gen["p_mw"] < pp_net.gen["min_p_mw"]))
    print(np.sum(pp_net.res_gen["p_mw"] > pp_net.gen["max_p_mw"]))
    print(np.sum(pp_net.res_sgen["p_mw"] < pp_net.sgen["min_p_mw"]))
    print(np.sum(pp_net.res_sgen["p_mw"] > pp_net.sgen["max_p_mw"]))
    print(np.sum(pp_net.res_line["loading_percent"] > pp_net.line["max_loading_percent"]))
    print(pp_net.res_trafo[np.logical_and(pp_net.trafo["max_loading_percent"] > 0, pp_net.res_trafo["loading_percent"] > pp_net.trafo["max_loading_percent"])])
    print(pp_net.res_line[pp_net.res_line["loading_percent"] > pp_net.line["max_loading_percent"]])

def inspect(contingency_name):
    change_contingency_state_pp(pp_net, contingency_name, False)
    init_gen = fcr(pp_net)
    pp_net.gen["p_mw"] = init_gen
    pp.rundcpp(pp_net)

if __name__ == "__main__":
    import os 
    
    from dotenv import load_dotenv
    from pathlib import Path
    from add_governor_kgover import read_governor_kgover

    load_dotenv()
    # net = ps.network.load("docs/orchestrator/examples/Nordic/Nordic.iidm")
    # finder = ContingencyFinder("docs/orchestrator/examples/4Bus/4Bus.iidm", 1)
    net = ps.network.load("temp copy.xiidm")
    par_file = Path(os.getenv("PAR_FILE"))
    governor_kgover = read_governor_kgover(net.get_generators().index, par_file)  

    #contingencies = group_power_contingencies(net)
    finder = ContingencyFinder(net, 10, mode="opf", governor_kgover=governor_kgover)

    # contingencies = power_contingencies()
    contingencies = finder.find_contingency(voltage_thresh=0, mode="opf", include_pairs=True)
    # finder.apply_contingency(contingencies.iloc[0].name)
    contingencies.to_csv("contingencies.csv")
    # redispatch = finder.get_solution()

