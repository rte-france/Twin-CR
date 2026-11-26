"""
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Continuation power flow (ANDES) on every N-1 branch contingency and on the load / generator group increases.
For each case the maximum loading factor ``max_lambda`` is returned (lambda = 1 means the loading targeted by
``CPF_LOAD_SCALE``, see continuation_powerflow.py): the smaller it is, the closer the case is to voltage collapse.

The pypowsybl network is converted to ANDES once per worker. A contingency is applied by opening the branch in ANDES
(and the shunts that the conversion created for it), a group increase by changing the setpoints of its elements; the
base case is restored after each case.
"""

import multiprocessing as mp
import os

import andes
import numpy as np
import pandas as pd
import pypowsybl as ps

from tqdm import tqdm

from clusters import get_clusters
from fast_cpf import install_fast_cpf
from pypowsybl_to_andes import pypowsybl_to_andes

INCREASE_LOAD_PERCENT = 30
CPF_LOAD_SCALE = 2.0

BRANCH_KIND = "branch"
LOAD_GROUP_KIND = "load_group"
GENERATOR_GROUP_KIND = "generator_group"


def group_elements_by_cluster(network, element_type, substation_clusters):
    """
    Pypowsybl ids of the connected loads (``element_type="load"``) or wind / solar generators
    (``element_type="generator"``), by group: the substation cluster, or the country for substations without cluster.
    """
    if element_type == "generator":
        elements = network.get_generators(attributes=["connected", "voltage_level_id", "energy_source"])
        elements = elements[elements["energy_source"].isin(["SOLAR", "WIND"])]
    else:
        elements = network.get_loads(attributes=["connected", "voltage_level_id"])
    elements = elements[elements["connected"]]

    elements = elements.join(network.get_voltage_levels()[["substation_id"]], on="voltage_level_id")
    elements = elements.join(network.get_substations()[["country"]], on="substation_id")
    elements = elements.reset_index().merge(substation_clusters, how="left", on="substation_id")
    elements["group"] = elements["group"].fillna(elements["country"])

    return {group: list(group_elements["id"]) for group, group_elements in elements.groupby("group")}


def get_component_type(network, contingency_id):
    if contingency_id in network.get_lines().index:
        return "line"
    if contingency_id in network.get_2_windings_transformers().index:
        return "transformer"
    return "group"


class CpfRunner:
    """Holds one ANDES system and runs a continuation power flow on variations of it."""

    def __init__(self, network):
        self.system = pypowsybl_to_andes(network)
        self.system.PFlow.run()
        install_fast_cpf(self.system)  # factorize only the sparse Jacobian instead of the bordered one

        generators = network.get_generators(attributes=["target_p", "max_p"])
        self.generator_target_p_mw = generators["target_p"]
        self.generator_max_p_mw = generators["max_p"]

        self.shunt_names = np.asarray(self.system.Shunt.name.v)
        self._base_state = self._snapshot_state()

    def _snapshot_state(self):
        system = self.system
        return dict(
            load_p0=system.PQ.p0.v.copy(),
            load_q0=system.PQ.q0.v.copy(),
            generator_p0=system.PV.p0.v.copy(),
            generator_p=system.PV.p.v.copy(),
            line_u=system.Line.u.v.copy(),
            shunt_u=system.Shunt.u.v.copy(),
            dae_x=system.dae.x.copy(),
            dae_y=system.dae.y.copy(),
        )

    def _restore_state(self):
        system, base_state = self.system, self._base_state
        system.PQ.p0.v[:] = base_state["load_p0"]
        system.PQ.q0.v[:] = base_state["load_q0"]
        system.PV.p0.v[:] = base_state["generator_p0"]
        system.PV.p.v[:] = base_state["generator_p"]
        system.Line.u.v[:] = base_state["line_u"]
        system.Shunt.u.v[:] = base_state["shunt_u"]
        system.dae.x[:] = base_state["dae_x"]
        system.dae.y[:] = base_state["dae_y"]
        system.vars_to_models()

    def _open_branch(self, branch_id):
        line_names = np.asarray(self.system.Line.name.v)
        self.system.Line.u.v[line_names == branch_id] = 0
        # The conversion adds shunts named "<branch id>(asymmetry 1)", "(magnetizing)", "(open end)"... for a branch
        shunt_belongs_to_branch = np.array([name.startswith(branch_id + "(") for name in self.shunt_names], dtype=bool)
        self.system.Shunt.u.v[shunt_belongs_to_branch] = 0

    def _increase_loads(self, load_ids, increase_fraction):
        load_in_group = np.isin(self.system.PQ.name.v, load_ids)
        self.system.PQ.p0.v[load_in_group] *= 1 + increase_fraction
        self.system.PQ.q0.v[load_in_group] *= 1 + increase_fraction

    def _increase_generators(self, generator_ids, increase_fraction):
        """Generators are capped at max_p. Voltage regulating generators are PV in ANDES, the others PQ (negative
        load). The generators of the slack bus are aggregated in the Slack: they absorb the imbalance anyway."""
        base_mva = self.system.config.mva
        for generator_id in generator_ids:
            increased_p_mw = min(self.generator_target_p_mw[generator_id] * (1 + increase_fraction),
                                 self.generator_max_p_mw[generator_id])
            increased_p_pu = increased_p_mw / base_mva
            self.system.PV.p0.v[np.asarray(self.system.PV.name.v) == generator_id] = increased_p_pu
            self.system.PV.p.v[np.asarray(self.system.PV.name.v) == generator_id] = increased_p_pu
            self.system.PQ.p0.v[np.asarray(self.system.PQ.name.v) == generator_id] = -increased_p_pu

    def _apply(self, kind, element_ids):
        increase_fraction = INCREASE_LOAD_PERCENT / 100.
        if kind == BRANCH_KIND:
            for branch_id in element_ids:
                self._open_branch(branch_id)
        elif kind == LOAD_GROUP_KIND:
            self._increase_loads(element_ids, increase_fraction)
        else:
            self._increase_generators(element_ids, increase_fraction)

    def run_case(self, kind, case_name, element_ids):
        """Apply the case, run the power flow then the CPF, restore the base case. A case whose power flow or CPF does
        not converge (including an islanded network) gets ``max_lambda = 0``."""
        try:
            self._apply(kind, element_ids)
            converged = bool(self.system.PFlow.run()) and bool(self.system.CPF.run(load_scale=CPF_LOAD_SCALE))
            max_lambda = float(self.system.CPF.max_lam) if converged else 0.0
        except Exception as error:  # singular Jacobian, ... ANDES raises various errors on a broken network
            print(f"CPF failed for {case_name}: {error!r}")
            converged, max_lambda = False, 0.0
        finally:
            self._restore_state()
        return [case_name, max_lambda, converged]


# Worker side. Pypowsybl networks cannot be pickled: each worker receives the network as an XIIDM string.
_runner = None


def _initialize_worker(network_xiidm):
    global _runner
    andes.config_logger(stream_level=40)
    _runner = CpfRunner(ps.network.load_from_string("network.xiidm", network_xiidm))


def _run_case(case):
    return _runner.run_case(*case)


class CpfContingencyFinder:

    def __init__(self, network, n_jobs=10):
        self.network = network
        self.n_jobs = n_jobs
        if not network.get_buses()["v_mag"].notna().any():
            ps.loadflow.run_ac(network)
        substation_clusters = get_clusters(25)
        self.load_groups = group_elements_by_cluster(network, "load", substation_clusters)
        self.generator_groups = group_elements_by_cluster(network, "generator", substation_clusters)

    def _branch_ids(self, voltage_thresh):
        lines = self.network.get_lines()
        transformers = self.network.get_2_windings_transformers()
        if voltage_thresh > 0:
            nominal_voltage = self.network.get_voltage_levels()["nominal_v"]
            lines = lines[lines["voltage_level1_id"].map(nominal_voltage) > voltage_thresh]
            transformers = transformers[transformers["rated_u1"] > voltage_thresh]
        return list(lines.index) + list(transformers.index)

    def _cases(self, voltage_thresh):
        cases = [(BRANCH_KIND, branch_id, [branch_id]) for branch_id in self._branch_ids(voltage_thresh)]
        cases += [(LOAD_GROUP_KIND, "load" + group, load_ids) for group, load_ids in self.load_groups.items()]
        cases += [(GENERATOR_GROUP_KIND, "gen" + group, generator_ids)
                  for group, generator_ids in self.generator_groups.items()]
        return cases

    def find_contingency(self, voltage_thresh=0):
        """DataFrame indexed by case id (branch id, "load<group>" or "gen<group>"), sorted by ascending max_lambda."""
        cases = self._cases(voltage_thresh)
        print("Starting continuation power flow analysis of", len(cases), "cases")

        if self.n_jobs > 1:
            # Spawn: forking after BLAS / pypowsybl native runtimes were used can hang the children
            with mp.get_context("spawn").Pool(self.n_jobs, initializer=_initialize_worker,
                                              initargs=(self.network.save_to_string("XIIDM"),)) as pool:
                results = list(tqdm(pool.imap(_run_case, cases, chunksize=4), total=len(cases)))
        else:
            _initialize_worker(self.network.save_to_string("XIIDM"))
            results = [_run_case(case) for case in tqdm(cases)]

        contingencies = pd.DataFrame(results, columns=["id", "max_lambda", "converged"]).set_index("id")
        contingencies["component_type"] = [
            get_component_type(self.network, contingency_id) for contingency_id in contingencies.index]
        return contingencies.sort_values("max_lambda")


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    net = ps.network.load("temp copy.xiidm")
    finder = CpfContingencyFinder(net, n_jobs=1)
    cpf_contingencies = finder.find_contingency(voltage_thresh=300)
    cpf_contingencies.to_csv("cpf_contingencies.csv")
    print(cpf_contingencies.head(20))
