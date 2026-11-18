"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

N-2 screening with compound LODF on a pandapower network (DC model).

The DC model is taken from pandapower's own internal case (net._ppc) after
pp.rundcpp, so susceptances (1/(x*tap)), phase shifts, bus fusing and slack
handling are exactly those of pandapower's DC power flow.

    Delta = (I - Phi_KK)^-1 f0_K          (2x2 solve per pair)
    f'    = f0 + Phi[:, K] @ Delta ,  f'_K = 0
    islanding pair  <=>  det(I - Phi_KK) ~ 0

Candidate outages: lines, 2-winding transformers, impedances.
3-winding transformer branches stay in the model (and can be monitored) but
are not outaged. Generators, dclines, xwards, etc. are not covered.
"""

from __future__ import annotations

import copy
import itertools
import os
import warnings
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import numpy as np
import pandas as pd
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy.sparse.csgraph import connected_components
import pandapower as pp
from pandapower.pypower.idx_brch import F_BUS, T_BUS, BR_X, TAP, BR_STATUS, PF
from pandapower.pypower.idx_bus import BUS_TYPE, REF, NONE
from numba import njit
from tqdm import tqdm

from opf import WaterFilling, fcr_headroom, fcr_weights

SQRT3 = np.sqrt(3.0)
OUTAGEABLE = ("line", "trafo", "impedance")
ISLANDING_TOLERANCE = 1e-8
ISLANDING_RESIDUAL_MW = 1e-4


# --------------------------------------------------------------------------
# 0. Branch labelling
# --------------------------------------------------------------------------
def _branch_labels(net) -> list[tuple[str, int]]:
    """(element type, pandapower index) for every row of net._ppc['branch']."""
    n_ppc_branches = net._ppc["branch"].shape[0]
    labels = [None] * n_ppc_branches
    for element_type, (first_row, end_row) in net._pd2ppc_lookups["branch"].items():
        if element_type in ("line", "trafo", "impedance", "xward"):
            element_indices = net[element_type].index
            for position, row in enumerate(range(first_row, end_row)):
                labels[row] = (element_type, int(element_indices[position]))
        elif element_type == "trafo3w":
            element_indices = net.trafo3w.index
            n_trafos = len(element_indices)
            for side_offset, side in enumerate(("hv", "mv", "lv")):
                for position in range(n_trafos):
                    row = first_row + side_offset * n_trafos + position
                    labels[row] = (f"trafo3w_{side}", int(element_indices[position]))
        else:
            for row in range(first_row, end_row):
                labels[row] = (element_type, row - first_row)
    return [label if label is not None else ("unknown", row)
            for row, label in enumerate(labels)]


def _branch_names(net, labels) -> list[str]:
    """pandapower element names for the given (type, index) labels. Falls back to
    the 'type:index' label when the name is missing, and de-duplicates."""
    names = []
    for element_type, element_index in labels:
        table_name = element_type.split("_")[0] if element_type.startswith("trafo3w_") else element_type
        name = None
        if (table_name in net and element_index in net[table_name].index
                and "name" in net[table_name].columns):
            name = net[table_name].at[element_index, "name"]
        if name is None or pd.isna(name) or str(name) == "":
            name = f"{element_type}:{element_index}"
        else:
            name = str(name)
        if element_type.startswith("trafo3w_"):
            name = f"{name}_{element_type.split('_')[1]}"
        names.append(name)
    is_duplicate = pd.Series(names).duplicated(keep=False).to_numpy()
    return [f"{name} ({element_type}:{element_index})" if duplicated else name
            for name, duplicated, (element_type, element_index)
            in zip(names, is_duplicate, labels)]


# --------------------------------------------------------------------------
# 1. Compound LODF screening kernel
# --------------------------------------------------------------------------
@njit(nogil=True, fastmath=True, cache=True)
def _screen_first_outage(first, partners, phi, phi_monitored_T, base_flows,
                         monitored_base_flows, inv_rating, monitored_slot,
                         loading_threshold, islanding_tolerance):
    """All pairs (first, second in partners), one fused pass over the monitored branches.

    phi_monitored_T[b, i] = phi[monitored[i], b] so that both columns read here are contiguous.
    monitored_slot[b] is the position of branch b among the monitored ones (-1 if not).
    Returns (violating second outage, monitored position, flow, islanding second outage)."""
    n_monitored = monitored_base_flows.shape[0]
    capacity = 64
    violating_second = np.empty(capacity, np.int64)
    violating_monitored = np.empty(capacity, np.int64)
    violating_flow = np.empty(capacity)
    n_violations = 0
    islanding_second = np.empty(partners.shape[0], np.int64)
    n_islanding = 0
    loading = np.empty(n_monitored)
    phi_first = phi_monitored_T[first]
    first_slot = monitored_slot[first]
    # 2x2 system (I - Phi_KK) delta = f0_K, K = (first, second)
    a_first_first = 1.0 - phi[first, first]
    for t in range(partners.shape[0]):
        second = partners[t]
        a_second_second = 1.0 - phi[second, second]
        a_first_second = -phi[first, second]
        a_second_first = -phi[second, first]
        determinant = a_first_first * a_second_second - a_first_second * a_second_first
        if abs(determinant) < islanding_tolerance:
            islanding_second[n_islanding] = second
            n_islanding += 1
            continue
        delta_first = (a_second_second * base_flows[first]
                       - a_first_second * base_flows[second]) / determinant
        delta_second = (-a_second_first * base_flows[first]
                        + a_first_first * base_flows[second]) / determinant
        phi_second = phi_monitored_T[second]
        for i in range(n_monitored):               # branch-free, vectorised
            loading[i] = abs(monitored_base_flows[i] + phi_first[i] * delta_first
                             + phi_second[i] * delta_second) * inv_rating[i]
        second_slot = monitored_slot[second]
        if first_slot >= 0:                        # outaged branches carry Delta here,
            loading[first_slot] = 0.0              # their post-outage flow is 0
        if second_slot >= 0:
            loading[second_slot] = 0.0
        if loading.max() <= loading_threshold:
            continue
        for i in range(n_monitored):               # rare: locate violations
            if loading[i] > loading_threshold and i != first_slot and i != second_slot:
                if n_violations == capacity:
                    capacity *= 2
                    violating_second = np.concatenate((violating_second, np.empty(n_violations, np.int64)))
                    violating_monitored = np.concatenate((violating_monitored, np.empty(n_violations, np.int64)))
                    violating_flow = np.concatenate((violating_flow, np.empty(n_violations)))
                violating_second[n_violations] = second
                violating_monitored[n_violations] = i
                violating_flow[n_violations] = (monitored_base_flows[i]
                                                + phi_first[i] * delta_first
                                                + phi_second[i] * delta_second)
                n_violations += 1
    return (violating_second[:n_violations], violating_monitored[:n_violations],
            violating_flow[:n_violations], islanding_second[:n_islanding])


def rank_pairs(violations: pd.DataFrame, top=50) -> pd.DataFrame:
    pairs = violations.groupby(["outage_1", "outage_2"]).agg(
        max_loading=("loading", "max"), n_overloads=("overloaded", "size"),
        overload_index=("loading", lambda loading: float(np.sum((loading) ** 2))))
    pairs.to_csv("overflow_PI.csv")
    return pairs.sort_values("max_loading", ascending=False).head(top)


# --------------------------------------------------------------------------
# 2. DC sensitivity factors
# --------------------------------------------------------------------------
class DCSensitivityFactors:
    """
    DC sensitivity factors of a pandapower network.

    Runs a DC power flow on `net` and builds the LODF ingredients. With L the
    number of in-service branches and N the number of active ppc buses:
      net                : the pandapower network
      branches           : DataFrame (index = pandapower element names) with the
                           element type/index and from/to ppc bus of each branch
      branch_transfer    : (L, L) ndarray, Phi = B_d A X A^T
      base_flows_mw      : (L,) base flows in MW (from side), from pandapower's DC result
      rating_mw          : (L,) thermal rating in MW (NaN when unknown)
      limit_levels_mw    : (L, M) ndarray, every current limit of each branch in MW, ascending,
                           padded with inf. The first one is rating_mw
      limit_durations    : (L, M) ndarray, acceptable duration (s) of each limit level, -1 for
                           the permanent one
      outageable         : boolean mask (lines, 2w trafos, impedances)
      bridges            : boolean mask, branches whose outage islands the grid
      ppc_branch_rows    : rows of net._ppc['branch'] backing each branch
      n_buses            : N
      bus_position       : ppc bus -> position among the active buses (-1 if inactive)
      reference_positions: positions of the buses whose angle is fixed
      non_ref_positions  : positions of the buses whose angle is not fixed
      branch_susceptance : sparse diagonal B_d
      reduced_incidence  : (L, N - n_ref) branch-bus incidence A without reference buses
      reduced_b_lu       : LU factorisation of the reduced bus susceptance matrix
    """

    def __init__(self, net: pp.pandapowerNet, operational_limits: pd.DataFrame | None = None,
                 **rundcpp_kwargs):
        """`operational_limits`: pypowsybl network.get_operational_limits(). It gives the
        temporary limits (acceptable durations) of each branch; without it every branch
        only has its permanent rating."""
        pp.rundcpp(net, **rundcpp_kwargs)
        self.net = net
        self._ptdf = None
        ppc_bus, ppc_branch = net._ppc["bus"], net._ppc["branch"]

        is_active_bus = ppc_bus[:, BUS_TYPE] != NONE
        ppc_from_bus = ppc_branch[:, F_BUS].astype(int)
        ppc_to_bus = ppc_branch[:, T_BUS].astype(int)
        is_in_service = ((ppc_branch[:, BR_STATUS] > 0)
                         & is_active_bus[ppc_from_bus] & is_active_bus[ppc_to_bus]
                         & (ppc_from_bus != ppc_to_bus))
        rows = np.where(is_in_service)[0]
        n_branches = len(rows)

        n_buses = int(is_active_bus.sum())
        bus_position = -np.ones(ppc_bus.shape[0], int)
        bus_position[is_active_bus] = np.arange(n_buses)

        # susceptances exactly as in pypower makeBdc
        tap = ppc_branch[rows, TAP].real.copy()
        tap[tap == 0] = 1.0
        susceptance = 1.0 / (ppc_branch[rows, BR_X].real * tap)

        incidence = sp.csr_matrix(
            (np.tile([1.0, -1.0], n_branches),
             (np.repeat(np.arange(n_branches), 2),
              np.column_stack([bus_position[ppc_from_bus[rows]],
                               bus_position[ppc_to_bus[rows]]]).ravel())),
            shape=(n_branches, n_buses))
        reference_positions = np.where(ppc_bus[is_active_bus, BUS_TYPE] == REF)[0]   # fixed-angle buses
        non_ref_positions = np.setdiff1d(np.arange(n_buses), reference_positions)
        reduced_incidence = incidence[:, non_ref_positions].tocsc()
        branch_susceptance = sp.diags(susceptance)
        reduced_b_lu = spla.splu(
            (reduced_incidence.T @ branch_susceptance @ reduced_incidence).tocsc())

        # PTDF without the reference columns, B_d A B^-1, and Phi = PTDF A^T: one factorisation solve for both.
        # The padded PTDF is built lazily by ptdf().
        self._ptdf_reduced = np.asarray(
            (branch_susceptance @ reduced_incidence)
            @ reduced_b_lu.solve(np.eye(len(non_ref_positions))))
        self.branch_transfer = np.asarray(reduced_incidence @ self._ptdf_reduced.T).T
        labels = _branch_labels(net)
        self.branches = pd.DataFrame(
            {"type": [labels[row][0] for row in rows],
             "index": [labels[row][1] for row in rows],
             "from_bus": ppc_from_bus[rows], "to_bus": ppc_to_bus[rows]},
            index=_branch_names(net, [labels[row] for row in rows]))
        self.base_flows_mw = ppc_branch[rows, PF].real.copy()               # from side
        self.outageable = self.branches["type"].isin(OUTAGEABLE).to_numpy()
        self.bridges = np.abs(1.0 - np.diag(self.branch_transfer)) < ISLANDING_TOLERANCE
        self.ppc_branch_rows = rows
        self.n_buses = n_buses
        self.bus_position = bus_position
        self.reference_positions = reference_positions
        self.non_ref_positions = non_ref_positions
        self.branch_susceptance = branch_susceptance
        self.reduced_incidence = reduced_incidence
        self.reduced_b_lu = reduced_b_lu
        self.rating_mw = self._compute_ratings_mw()
        self.limit_levels_mw, self.limit_durations = self._compute_limit_levels(operational_limits)
        self.already_overloaded = abs(self.base_flows_mw) > self.rating_mw.values

    def _compute_ratings_mw(self) -> pd.Series:
        """Thermal rating in MW: lines sqrt3*Vn*Imax*df*parallel, trafos sn_mva*df
        (scaled by max_loading_percent when set), impedances sn_mva.
        Branches without a rating (incl. 3w trafo legs) -> NaN."""
        net, branches = self.net, self.branches
        rating_mw = pd.Series(np.nan, index=branches.index)

        is_line = branches["type"] == "line"
        if is_line.any():
            lines = net.line.loc[branches.loc[is_line, "index"].to_numpy()]
            nominal_kv = net.bus.loc[lines["from_bus"].to_numpy(), "vn_kv"].to_numpy()
            rating_mw[is_line] = (SQRT3 * nominal_kv * lines["max_i_ka"].to_numpy()
                                  * lines["df"].to_numpy() * lines["parallel"].to_numpy())

        is_trafo = branches["type"] == "trafo"
        if is_trafo.any():
            trafos = net.trafo.loc[branches.loc[is_trafo, "index"].to_numpy()]
            max_loading_percent = trafos["max_loading_percent"].to_numpy()
            loading_factor = np.where(max_loading_percent > 0, max_loading_percent / 100., np.inf)
            rating_mw[is_trafo] = (trafos["sn_mva"].to_numpy() * trafos["df"].to_numpy()
                                   * trafos["parallel"].to_numpy() * loading_factor)

        is_impedance = branches["type"] == "impedance"
        if is_impedance.any():
            impedances = net.impedance.loc[branches.loc[is_impedance, "index"].to_numpy()]
            rating_mw[is_impedance] = impedances["sn_mva"].to_numpy()
        return rating_mw

    def _compute_limit_levels(self, operational_limits):
        """(levels_mw, durations), both (L, M). Same limits as the ones behind rating_mw
        (current limits of lines, side TWO of 2w trafos): the lowest one is rating_mw, the
        others are scaled by their ratio to it. Branches without limit data get their
        rating as a permanent limit. Permanent limits have a duration of -1."""
        rating_mw = np.asarray(self.rating_mw, float)
        has_rating = np.isfinite(rating_mw)
        n_branches = len(rating_mw)
        # (branch position, rank among the branch's limits, level MW, duration s) of the branches with limit data
        limit_positions = limit_ranks = np.empty(0, int)
        limit_levels = limit_durations = np.empty(0, float)

        if operational_limits is not None and len(operational_limits):
            limits = operational_limits
            if "element_id" not in limits.columns:
                limits = limits.reset_index()
            # Side TWO is the one to take for transformers, but is arbitrary for lines. An improvement would be to take the strictest one on lines.
            # Elements with no side TWO limit fall back on their side ONE limits.
            limits = limits[limits["type"] == "CURRENT"]
            elements_with_side_two = set(limits.loc[limits["side"] == "TWO", "element_id"])
            has_side_two = limits["element_id"].isin(elements_with_side_two)
            limits = limits[(limits["side"] == "TWO") | (~has_side_two & (limits["side"] == "ONE"))]
            acceptable_duration = limits["acceptable_duration"].to_numpy(float)
            limits = pd.DataFrame({
                "element_id": limits["element_id"].to_numpy(),
                "value": limits["value"].to_numpy(float),
                # pypowsybl: -1 (or infinite) for the permanent limit
                "duration": np.where((acceptable_duration < 0) | ~np.isfinite(acceptable_duration),
                                     -1, acceptable_duration).astype(int)})
            # Per element: limits sorted ascending, rank in that order, and the lowest one (the reference of the scaling)
            limits = limits.sort_values(["element_id", "value"], kind="stable", ignore_index=True)
            limits["rank"] = limits.groupby("element_id").cumcount()
            limits["lowest_value"] = limits.groupby("element_id")["value"].transform("min")
            limits = limits[limits["lowest_value"] > 0]

            # Name of the pandapower element behind each branch that can take limit data
            branch_element_name = np.full(n_branches, None, dtype=object)
            for element_type in ("line", "trafo"):
                is_type = (self.branches["type"] == element_type).to_numpy()
                if is_type.any():
                    element_indices = self.branches.loc[is_type, "index"].to_numpy()
                    branch_element_name[is_type] = (
                        self.net[element_type]["name"].reindex(element_indices).to_numpy(object))
            has_limit_data = has_rating & pd.notna(branch_element_name)
            branches_with_name = pd.DataFrame({"position": np.where(has_limit_data)[0],
                                               "element_id": branch_element_name[has_limit_data]})
            matched = branches_with_name.merge(limits, on="element_id", how="inner")
            limit_positions = matched["position"].to_numpy(int)
            limit_ranks = matched["rank"].to_numpy(int)
            limit_levels = (rating_mw[limit_positions] * matched["value"].to_numpy(float)
                            / matched["lowest_value"].to_numpy(float))
            limit_durations = matched["duration"].to_numpy(float)

        n_levels = max(1, limit_ranks.max() + 1 if len(limit_ranks) else 1)
        levels_mw = np.full((n_branches, n_levels), np.inf)
        duration_s = np.full((n_branches, n_levels), np.nan)
        # Default: the rating as only, permanent, limit
        levels_mw[has_rating, 0] = rating_mw[has_rating]
        duration_s[has_rating, 0] = -1
        # Branches with limit data: their limits replace the default
        replaced_positions = np.unique(limit_positions)
        levels_mw[replaced_positions] = np.inf
        duration_s[replaced_positions] = np.nan
        levels_mw[limit_positions, limit_ranks] = limit_levels
        duration_s[limit_positions, limit_ranks] = limit_durations
        return levels_mw, duration_s

    def exceeded_limit_durations(self, positions, flows_mw) -> np.ndarray:
        """Acceptable duration (s, -1 = permanent) of the lowest limit that |flows_mw| does not exceed
        on each branch of `positions`."""
        levels = self.limit_levels_mw[positions]
        n_exceeded = (np.abs(flows_mw)[:, None] > levels).sum(axis=1)
        if levels.shape[1] == 1:
            # This is for Nordic: only permanent limits, so we define an arbitrary duration of 300
            return np.full(levels.shape[0], 300)
        return self.limit_durations[positions, np.maximum(n_exceeded, 0)]

    def _overloads_by_outage(self, outages, overloaded_positions, flows_mw) -> dict:
        """{outage: {overloaded branch name: limit duration}} from parallel arrays."""
        branch_names = self.branches.index.to_numpy()
        durations = self.exceeded_limit_durations(overloaded_positions, flows_mw)
        overloads = {}
        for outage, position, duration in zip(outages, overloaded_positions, durations):
            overloads.setdefault(outage, {})[branch_names[position]] = int(duration)
        return overloads

    # ----------------------------------------------------------------------
    # Sensitivity matrices
    # ----------------------------------------------------------------------
    def ptdf(self) -> np.ndarray:
        """
        PTDF (L, N): flow change (MW, from side) on each in-service branch per MW
        injected at each active ppc bus and withdrawn at the reference bus(es)
        (their columns are 0). Bus order = self.bus_position.
        Computed once (topology is fixed), the returned array is shared: do not modify it.
        """
        if self._ptdf is None:
            ptdf = np.zeros((len(self.base_flows_mw), self.n_buses))
            ptdf[:, self.non_ref_positions] = self._ptdf_reduced
            self._ptdf = ptdf
            self._ptdf_reduced = None   # free the unpadded copy
        return self._ptdf

    def lodf(self) -> np.ndarray:
        """
        Single-outage LODF matrix (L, L): LODF[i, k] = Phi[i, k] / (1 - Phi[k, k]),
        i.e. the flow change on branch i per MW pre-outage flow on branch k.
        Diagonal is -1 (outaged branch loses its flow). Columns of bridge
        branches (islanding outages) are NaN.
        """
        denominator = 1.0 - np.diag(self.branch_transfer)
        lodf = self.branch_transfer / np.where(self.bridges, np.nan, denominator)[None, :]
        np.fill_diagonal(lodf, -1.0)
        lodf[:, self.bridges] = np.nan
        return lodf

    # ----------------------------------------------------------------------
    # Compound LODF screening
    # ----------------------------------------------------------------------
    def screen_n2(self, threshold=1.0, candidates=None, monitored=None,
                  islanding_tolerance=ISLANDING_TOLERANCE, n_jobs=None):
        """
        Screen N-2 pairs among `candidates` (positions in self.branches; default: all
        outageable branches). Bridges are dropped from the candidates: pairs containing one
        island the grid and are covered by the N-1 / trip path. One numba kernel call per
        first outage, run on `n_jobs` threads (default: all CPUs; GIL released).

        Returns (violations DataFrame, islanding pairs). Each violation carries the duration
        (s, -1 = permanent) of the highest limit exceeded by the overloaded branch
        (limit_duration). The islanding pairs, as an (P, 2) array of
        positions in self.branches, are those whose joint outage islands the grid
        although neither branch is a bridge on its own (det(I - Phi_KK) ~ 0).
        They are NOT evaluated here (they need a separate island re-solve, see
        iter_trip_flows).
        """
        branch_names = self.branches.index.to_numpy()
        candidates = (np.where(self.outageable)[0] if candidates is None
                      else np.asarray(candidates)).astype(np.int64)
        candidates = candidates[~self.bridges[candidates]]   # pairs with a bridge island the grid: N-1 / trip path
        rating_mw = np.asarray(self.rating_mw, float)
        rating_mw[self.already_overloaded] = np.inf
        monitored = (np.where(np.isfinite(rating_mw))[0] if monitored is None
                     else np.asarray(monitored))
        inv_rating = np.ascontiguousarray(1.0 / rating_mw[monitored])
        monitored_base_flows = np.ascontiguousarray(self.base_flows_mw[monitored])
        monitored_slot = np.full(len(self.base_flows_mw), -1, np.int64)
        monitored_slot[monitored] = np.arange(len(monitored))
        phi_monitored_T = np.ascontiguousarray(self.branch_transfer[monitored].T)
        phi = np.ascontiguousarray(self.branch_transfer)

        def screen_candidate(first_position):
            first = candidates[first_position]
            result = _screen_first_outage(
                first, candidates[first_position + 1:], phi, phi_monitored_T,
                self.base_flows_mw, monitored_base_flows, inv_rating, monitored_slot,
                float(threshold), float(islanding_tolerance))
            return first, result

        parts = []
        # tasks in order: early first outages have the most partners
        with ThreadPoolExecutor(n_jobs or os.cpu_count() or 1) as pool:
            for first, (second, monitored_position, flow, islanding_second) in tqdm(
                    pool.map(screen_candidate, range(len(candidates))), total=len(candidates)):
                parts.append((np.full(len(second), first), second, monitored_position, flow,
                              np.full(len(islanding_second), first), islanding_second))

        if parts:
            (first_outage, second_outage, monitored_position, flow,
             islanding_first, islanding_second) = (np.concatenate(x) for x in zip(*parts))
        else:
            first_outage = second_outage = monitored_position = np.empty(0, np.int64)
            islanding_first = islanding_second = np.empty(0, np.int64)
            flow = np.empty(0)
        violations = pd.DataFrame({
            "outage_1": branch_names[first_outage], "outage_2": branch_names[second_outage],
            "overloaded": branch_names[monitored[monitored_position]], "flow_mw": flow,
            "rating_mw": rating_mw[monitored[monitored_position]],
            "loading": np.abs(flow) * inv_rating[monitored_position],
            "limit_duration": self.exceeded_limit_durations(monitored[monitored_position], flow)})
        islanding = np.column_stack([islanding_first, islanding_second])
        return violations.sort_values("loading", ascending=False, ignore_index=True), islanding

    def voltage_candidates(self, voltage_thresh=0.0):
        """(positions, mask) of outageable branches above `voltage_thresh` kV
        (lines: from-bus nominal voltage, trafos: HV-side, impedances: from-bus).
        Pass the positions as `candidates` to screen_n2. 0 -> all outageable branches."""
        net, branches = self.net, self.branches
        mask = self.outageable.copy()
        if voltage_thresh > 0:
            nominal_kv = pd.Series(np.nan, index=branches.index)
            for element_type, bus_column in (("line", "from_bus"), ("trafo", "hv_bus"),
                                             ("impedance", "from_bus")):
                is_type = branches["type"] == element_type
                if is_type.any():
                    element_indices = branches.loc[is_type, "index"].to_numpy()
                    bus_ids = net[element_type].loc[element_indices, bus_column].to_numpy()
                    nominal_kv[is_type] = net.bus.loc[bus_ids, "vn_kv"].to_numpy()
            mask &= (nominal_kv > voltage_thresh).to_numpy()
        return np.where(mask)[0], mask

    def validate_pair(self, outage_1: str, outage_2: str) -> float:
        """Max abs flow error (MW) between compound-LODF flows and a pandapower
        DC power flow with both elements set out of service."""
        branches, phi, base_flows = self.branches, self.branch_transfer, self.base_flows_mw
        branch_names = list(branches.index)
        outaged = [branch_names.index(outage_1), branch_names.index(outage_2)]
        delta = np.linalg.solve(np.eye(2) - phi[np.ix_(outaged, outaged)], base_flows[outaged])
        model_flows = base_flows + phi[:, outaged] @ delta
        model_flows[outaged] = 0.0

        outaged_net = copy.deepcopy(self.net)
        for name in (outage_1, outage_2):
            element_type, element_index = branches.loc[name, ["type", "index"]]
            outaged_net[element_type].at[element_index, "in_service"] = False
        pp.rundcpp(outaged_net)
        # same rows as the base model (status-0 rows simply carry 0 MW)
        reference_flows = outaged_net._ppc["branch"][self.ppc_branch_rows, PF].real
        is_compared = np.ones(len(branch_names), bool)
        is_compared[outaged] = False
        return float(np.max(np.abs(model_flows[is_compared] - reference_flows[is_compared])))

    def get_problematic_n_minus_1(self, voltage_thresh=0):
        """Returns (problematic outages, overloads): `overloads` maps each problematic outage
        to {overloaded branch: acceptable duration (s, -1 = permanent) of the highest limit
        exceeded}."""
        branches, base_flows = self.branches, self.base_flows_mw
        print(f"{len(branches)} branches, {self.bridges.sum()} bridges")
        n_minus_1_flows = base_flows[:, None] + self.lodf() * base_flows
        is_overloaded = abs(n_minus_1_flows) > self.rating_mw.values[:, None]
        # Exclude already overloaded lines
        is_overloaded = is_overloaded & np.logical_not(self.already_overloaded)[:, None]
        candidates, is_candidate = self.voltage_candidates(voltage_thresh)
        is_problematic = is_candidate & is_overloaded.any(axis=0)
        _, problematic_bridges, bridge_overloads = self.get_problematic_gen_and_bridges_trips(bridge_candidates=candidates)

        overloaded_positions, outage_positions = np.nonzero(is_overloaded & is_candidate[None, :])
        overloads = self._overloads_by_outage(
            branches.index[outage_positions], overloaded_positions,
            n_minus_1_flows[overloaded_positions, outage_positions])
        overloads.update(bridge_overloads)
        return list(branches.index[is_problematic]) + problematic_bridges, overloads

    def get_problematic_n_minus_2(self, voltage_thresh=0):
        """Returns (problematic_n1, pairs, overloads). `overloads` maps every problematic N-1
        outage (name) and N-2 pair (tuple of names) to {overloaded branch: acceptable
        duration (s, -1 = permanent) of the highest limit exceeded}."""
        problematic_n1, overloads = self.get_problematic_n_minus_1(voltage_thresh)

        candidates, _ = self.voltage_candidates(voltage_thresh)
        # drop outages already overloading at N-1
        candidates = candidates[~self.branches.index[candidates].isin(problematic_n1)]
        violations, islanding_pairs = self.screen_n2(candidates=candidates)
        pairs = violations[["outage_1", "outage_2"]].drop_duplicates().values
        for outages, group in violations.groupby(["outage_1", "outage_2"]):
            overloads[outages] = dict(zip(group["overloaded"], group["limit_duration"].astype(int)))

        # pairs islanding a slack-free set behave like a gen trip
        _, problematic_islands, island_overloads = self.get_problematic_gen_and_bridges_trips(
            include_bridges=False, island_pairs=islanding_pairs)
        if problematic_islands:
            pairs = np.concatenate([pairs.reshape(-1, 2), np.array(problematic_islands, dtype=object)])
        overloads.update(island_overloads)
        return problematic_n1, pairs, overloads

    # ----------------------------------------------------------------------
    # Generator trips / bridge outages
    # ----------------------------------------------------------------------
    def _islanding_events(self, gen_bus_position, is_slack, outages, ptdf):
        """
        Outages (tuples of branch positions: one bridge, or one islanding N-2 pair)
        that cut off a set S of buses containing no reference bus (and smaller than
        the side that does).

        The net injection P_S of S is read off the base flows of the outaged branches
        (what S sends to the main island), so it holds whatever the injecting elements
        are (gens, sgens, loads, dclines, shunts...). Losing S is modelled as one
        injection of -P_S at a bus of S, which leaves S balanced, followed, for a pair,
        by the removal of the two branches (compound LODF, done by iter_trip_flows).
        Once the outaged branches are open the main island cannot tell where in S the
        injection was removed, so any bus of S gives the same main-island flows.

        Returns a list of dicts: name (branch name, or tuple of the pair's names),
        key (position of the bridge, or tuple of the pair's positions), outage
        (positions), lost_mw (P_S), lost_flow_mw (flow change per branch of removing
        P_S at a bus of S, slack compensating), gens (positions in net.gen inside S),
        excluded (bool mask over branches: the outaged ones and every branch touching S).
        """
        branches, n_buses = self.branches, self.n_buses
        from_position = self.bus_position[branches["from_bus"].to_numpy()]
        to_position = self.bus_position[branches["to_bus"].to_numpy()]
        reference_positions = self.reference_positions

        events = []
        for outage in outages:
            outage = np.asarray(outage)
            is_kept = np.ones(len(branches), bool)
            is_kept[outage] = False
            graph = sp.coo_matrix((np.ones(is_kept.sum()), (from_position[is_kept], to_position[is_kept])),
                                  shape=(n_buses, n_buses))
            _, component = connected_components(graph, directed=False)
            is_cut_off = component != component[reference_positions[0]]
            is_cut_off[np.isin(component, component[reference_positions])] = False   # any island holding a reference bus
            if not is_cut_off.any() or is_cut_off.sum() > (~is_cut_off).sum():       # slack side is the minority: slack-gen loss
                continue
            is_gen_cut_off = is_cut_off[np.where(gen_bus_position >= 0, gen_bus_position, 0)] & (gen_bus_position >= 0)
            gens_cut_off = np.where(is_gen_cut_off)[0]
            if is_slack[gens_cut_off].any():
                continue
            outage_from_is_cut_off = is_cut_off[from_position[outage]]
            lost_mw = np.where(outage_from_is_cut_off, 1.0, -1.0) @ self.base_flows_mw[outage]   # S -> main
            if len(outage) == 1 and np.isclose(lost_mw, 0) and not len(gens_cut_off):
                continue                                   # nothing injected, nothing shared: no effect
            cut_off_end = np.where(outage_from_is_cut_off, from_position[outage], to_position[outage])[0]
            lost_flow_mw = lost_mw * ptdf[:, cut_off_end]
            excluded = is_cut_off[from_position] | is_cut_off[to_position]
            excluded[outage] = True
            names = tuple(branches.index[outage])
            events.append({"name": names[0] if len(outage) == 1 else names,
                           "key": int(outage[0]) if len(outage) == 1 else tuple(int(o) for o in outage),
                           "outage": outage, "lost_mw": lost_mw, "lost_flow_mw": lost_flow_mw,
                           "gens": gens_cut_off, "excluded": excluded})
        return events

    # The FCR model has been complexified when capping generators to pmax and using weights from .par file
    # An simpler implementation would be to keep margin as weight, but only for generators with non 0 weight
    # It would however differ from the dynawo one
    def _fcr_model(self):
        """Gens and FCR participation, as seen by opf.fcr, for the current state of the net."""
        net = self.net
        gen = net.gen
        # copies: to_numpy can be a view of the net, which is modified in place by callers (pp_net.gen.loc[..., "p_mw"] *= ...)
        dispatch_mw = net.res_gen["p_mw"].to_numpy(float, copy=True)
        setpoint_mw = gen["p_mw"].to_numpy(float, copy=True)
        is_slack = gen["slack"].to_numpy(bool)
        gen_bus_position = self.bus_position[net._pd2ppc_lookups["bus"][gen["bus"].to_numpy()]]
        can_share = (gen["in_service"].to_numpy(bool) & ~np.isclose(dispatch_mw, 0)
                     & (gen_bus_position >= 0))

        # (L, N) and (L, G): flow change per MW injected at each bus / by each gen
        ptdf = self.ptdf()
        gen_ptdf = ptdf[:, np.where(gen_bus_position >= 0, gen_bus_position, 0)]
        slack_ptdf = gen_ptdf[:, is_slack].mean(axis=1)

        # dispatch before the slack absorbed the mismatch
        base_mismatch_mw = (dispatch_mw[is_slack] - setpoint_mw[is_slack]).sum()
        init_gen = pd.Series(dispatch_mw, index=gen.index)
        init_gen[is_slack] -= base_mismatch_mw

        # FCR sharing by sign of the mismatch to absorb: surplus (>= 0) -> gens go up (to max_p_mw),
        # deficit (< 0) -> gens go down (to min_p_mw). The weights are the same in both cases,
        # the headroom differs. Gens without headroom do not share (weight 0).
        participation = fcr_weights(net, pd.Series(can_share, index=gen.index)).to_numpy(float)
        weights, headroom, waterfilling, weighted_ptdf = {}, {}, {}, {}
        for is_surplus in (True, False):
            headroom[is_surplus] = fcr_headroom(gen, init_gen, 1.0 if is_surplus else -1.0).to_numpy(float)
            weights[is_surplus] = np.where(headroom[is_surplus] > 0, participation, 0.0)
            waterfilling[is_surplus] = WaterFilling(weights[is_surplus], headroom[is_surplus])
            weighted_ptdf[is_surplus] = gen_ptdf @ weights[is_surplus]  # (L,)
        return SimpleNamespace(
            gen=gen, dispatch_mw=dispatch_mw, is_slack=is_slack, gen_bus_position=gen_bus_position,
            can_share=can_share, ptdf=ptdf, gen_ptdf=gen_ptdf, slack_ptdf=slack_ptdf,
            participation=participation, weights=weights, headroom=headroom, waterfilling=waterfilling,
            weighted_ptdf=weighted_ptdf,
            base_mismatch_mw=base_mismatch_mw)

    @staticmethod
    def _fcr_share_flow(model, is_surplus, amount, gens_stop_sharing):
        """(L,): flow change of sharing `amount` >= 0 between the gens (up if `is_surplus`, else down), each
        capped by its headroom, the slack keeping what nobody can take. `gens_stop_sharing`: positions of
        the gens that no longer share (tripped). Exact, the sharing being the one of opf.fcr."""
        gen_ptdf, weights, headroom = model.gen_ptdf, model.weights[is_surplus], model.headroom[is_surplus]
        waterfilling = model.waterfilling[is_surplus]
        if len(gens_stop_sharing):
            stopped_weights = weights.copy()
            stopped_weights[gens_stop_sharing] = 0.0
            waterfilling = WaterFilling(stopped_weights, headroom)
        n_saturated, level, unallocated = waterfilling.level(amount)
        saturated = waterfilling.order[:n_saturated]
        flow = gen_ptdf[:, saturated] @ headroom[saturated] + unallocated * model.slack_ptdf
        if n_saturated < len(waterfilling.order):
            # only the gens still free are proportional to the level: remove the others from the weighted sum
            not_free = np.concatenate([saturated, gens_stop_sharing]).astype(int)
            flow = flow + level * (model.weighted_ptdf[is_surplus] - gen_ptdf[:, not_free] @ weights[not_free])
        return flow

    @staticmethod
    def _fcr_flow_response(model, lost_mw, lost_flow_mw, gens_stop_sharing):
        """
        (L,): flow change after losing `lost_mw` of injection (whose own effect on the flows, slack
        compensating, is `lost_flow_mw`) and FCR redispatch of the resulting slack mismatch, which is the
        base mismatch plus the lost power. FCR shares it as opf.fcr: up if the mismatch is >= 0, else down.
        """
        mismatch = model.base_mismatch_mw + lost_mw
        is_surplus = mismatch >= 0
        # from https://engineering.purdue.edu/~kekatos/psoc/lecture9.pdf: effect of the FCR on all other generators - effect of generator outage
        shared = DCSensitivityFactors._fcr_share_flow(model, is_surplus, abs(mismatch), gens_stop_sharing)
        # base mismatch term: the slack goes back to its setpoint (should be most of the time 0 because
        # a prebalance step is executed in ContingencyFinder constructor)
        return (1.0 if is_surplus else -1.0) * shared - model.base_mismatch_mw * model.slack_ptdf - lost_flow_mw

    @staticmethod
    def _fcr_pieces(model, is_surplus, amount_start, amount_end=np.inf):
        """
        Yields (amount_lo, amount_hi, constant, slope), (L,) each: for an amount of power mismatch in
        [amount_lo, amount_hi] (inside [amount_start, amount_end]), the flow change due to the FCR sharing
        it is constant + normalized_free_ptdf * amount. Pieces end where a gen reaches its limit, so they are
        generated lazily, in increasing amount, from the pieces already crossed at `amount_start`.
        """
        gen_ptdf, slack_ptdf = model.gen_ptdf, model.slack_ptdf
        weights, headroom = model.weights[is_surplus], model.headroom[is_surplus]
        waterfilling = model.waterfilling[is_surplus]
        order, breaks = waterfilling.order, waterfilling.breaks
        k = waterfilling.level(amount_start)[0]
        saturated = order[:k]
        saturated_flow = gen_ptdf[:, saturated] @ headroom[saturated]           # flow of the saturated gens
        # Adjusted ptdfs -> put saturated ones at 0
        free_ptdf = model.weighted_ptdf[is_surplus] - gen_ptdf[:, saturated] @ weights[saturated]
        while True:
            lo = max(amount_start, breaks[k - 1] if k else 0.0)
            hi = min(amount_end, breaks[k] if k < len(order) else np.inf)
            cum_headroom = waterfilling.cum_headroom[k]
            if k == len(order):                              # everybody saturated: slack keeps the rest
                fixed_flow, normalized_free_ptdf = saturated_flow - cum_headroom * slack_ptdf, slack_ptdf
            else:
                normalized_free_ptdf = free_ptdf / waterfilling.reverse_cum_weight[k]
                # We remove cum_headroom * normalized_free_ptdf because normalized_free_ptdf multiplies total amount
                # amount = cum_headroom + rest. Rest is the part of amount taken by remaining sharing generators
                # Thus flow = constant + normalized_free_ptdf * amount = saturated_flow + normalized_free_ptdf * rest 
                fixed_flow = saturated_flow - cum_headroom * normalized_free_ptdf
            if hi > lo:
                yield lo, hi, fixed_flow, normalized_free_ptdf
            if hi >= amount_end or k == len(order):
                return
            saturating = order[k]
            saturated_flow = saturated_flow + gen_ptdf[:, saturating] * headroom[saturating]
            free_ptdf = free_ptdf - gen_ptdf[:, saturating] * weights[saturating]
            k += 1

    # ----------------------------------------------------------------------
    # Load and generator clusters
    # ----------------------------------------------------------------------
    # Generators clusters add quite some complexity (due to p_max). Simpler implementation would be possible if we define the problem 
    # in a different way (% increase compared to margin rather than percentage increase capped at p_max)
    # In any case, it does not seem to matter as no generator scenario is identified. It might not be worth the code complexity
    def _segment_regimes(self, model, saturated_lost_mw, group_mw, saturated_lost_flow_mw, group_lost_flow_mw, segment_start, segment_end):
        """
        Yields (fixed_flow, proportional_flow, fraction_start, fraction_end), in increasing fraction: the flows (post FCR) are
        fixed_flow + proportional_flow * fraction on [fraction_start, fraction_end], for a loss of injection of
        saturated_lost_mw + group_mw * fraction, whose own effect on the flows (slack compensating) is
        saturated_lost_flow_mw + group_lost_flow_mw * fraction ((L,) arrays). Both are affine on [segment_start, segment_end].
        Pieces end where the FCR regime (sign of the slack mismatch) changes or a gen reaches its limit (see
        _fcr_pieces); they are generated lazily, there can be many. Nobody stops sharing the FCR.
        """
        base_mismatch_mw = model.base_mismatch_mw
        # slack mismatch = fixed_lost_mw + group_mw * fraction (> 0: gens go up, "surplus" regime)
        fixed_lost_mw = base_mismatch_mw + saturated_lost_mw
        if group_mw == 0:
            # nothing changes with fraction
            flows = self.base_flows_mw + self._fcr_flow_response(model, saturated_lost_mw, saturated_lost_flow_mw, np.empty(0, int))
            yield flows, np.zeros_like(flows), segment_start, segment_end
            return

        # This function is thus translating fcr pieces defined for amount of mismatch to fcr pieces defined for fraction
        # fraction of group_mw
        def regime_pieces(is_surplus, regime_start, regime_end):
            # the FCR amount |mismatch| is affine in fraction, increasing with it iff the regime's sign is the rate's
            sign = 1.0 if is_surplus else -1.0
            to_fraction = lambda amount: (sign * amount - fixed_lost_mw) / group_mw
            to_amount = lambda fraction: sign * (fixed_lost_mw + group_mw * fraction)
            amounts = sorted([to_amount(regime_start), to_amount(regime_end)]) \
                if np.isfinite(regime_end) else [to_amount(regime_start), np.inf]
            pieces = self._fcr_pieces(model, is_surplus, max(amounts[0], 0.0), amounts[1])
            if sign * group_mw < 0:
                pieces = reversed(list(pieces))          # amount decreases with fraction (finite range)
            for amount_lo, amount_hi, fixed_delta_flow, normalized_free_ptdf in pieces:
                fractions = sorted([to_fraction(amount_lo), to_fraction(amount_hi)])
                # flows = base + sign * (constant + normalized_free_ptdf * amount) - base mismatch term - lost flow
                # amount = sign * (fixed_lost_mw + group_mw * fraction)
                fixed_flow = (self.base_flows_mw + sign * fixed_delta_flow + normalized_free_ptdf * fixed_lost_mw
                             - base_mismatch_mw * model.slack_ptdf - saturated_lost_flow_mw)
                yield (fixed_flow, normalized_free_ptdf * group_mw - group_lost_flow_mw,
                       max(fractions[0], regime_start), min(fractions[1], regime_end))

        # The regime can only change here if the mismatch changes sign: it is neglected when the base mismatch is 0
        # (almost the case after ContingencyFinder ps loadflow + pp fcr) and the loss goes the same way
        switch = -fixed_lost_mw / group_mw
        edges = [segment_start, switch, segment_end] if segment_start < switch < segment_end \
            else [segment_start, segment_end]
        for start, end in zip(edges[:-1], edges[1:]):
            middle = start + (min(end, start + 1.0) - start) / 2
            yield from regime_pieces(fixed_lost_mw + group_mw * middle >= 0, start, end)

    def _group_regimes(self, model, ptdfs, segments, fraction_start=0.0):
        """
        (flows at fraction 0, regimes) of a group of elements (ptdfs: (L, K) flow change per MW lost by each
        element, slack compensating) losing an injection of lost0 + lost1 * fraction MW each ((K,) arrays) on each
        of the `segments`: (segment_start, segment_end, lost0, lost1), in increasing fraction. Regimes are the
        (intercept, slope, fraction_start, fraction_end) of _segment_regimes, from `fraction_start` on.
        """
        flows_at_zero = self.base_flows_mw + self._fcr_flow_response(model, 0.0, 0.0, np.empty(0, int))

        def regimes():
            for segment_start, segment_end, fixed_lost, group_mw in segments:
                if segment_end < fraction_start:
                    continue
                for regime in self._segment_regimes(model, fixed_lost.sum(), group_mw.sum(), ptdfs @ fixed_lost, ptdfs @ group_mw,
                                                    segment_start, segment_end):
                    if regime[3] >= fraction_start:
                        yield regime
        return flows_at_zero, regimes()

    def _load_group_regimes(self, model, groups, direction, fraction_start=0.0):
        """
        Yields (name, group load MW, flows at fraction 0, regimes) for each group: the flows (post FCR) as a function
        of fraction >= 0, the fraction of the group's load added (direction = +1) or removed (-1). Regimes are
        (intercept, slope, fraction_start, fraction_end) in increasing fraction (lazy: there can be many), see
        _segment_regimes. A load change is a lost injection of -direction * fraction * P_group, located at the load
        buses.
        """
        net = self.net
        loads = net.load
        load_bus_position = self.bus_position[net._pd2ppc_lookups["bus"][loads["bus"].to_numpy()]]
        load_mw = (loads["p_mw"].to_numpy(float) * loads["scaling"].to_numpy(float)
                   * loads["in_service"].to_numpy(bool))

        for name, load_index in groups.items():
            positions = loads.index.get_indexer(load_index)
            positions = positions[load_bus_position[positions] >= 0]
            group_mw = load_mw[positions]
            segments = [(0.0, np.inf, np.zeros_like(group_mw), direction * group_mw)]
            flows_at_zero, regimes = self._group_regimes(
                model, model.ptdf[:, load_bus_position[positions]], segments, fraction_start)
            yield name, group_mw.sum(), flows_at_zero, regimes

    def _gen_group_regimes(self, model, groups, direction, fraction_start=0.0):
        """
        Same as _load_group_regimes for generators: the p_mw of the gens of each group is multiplied by
        1 + direction * fraction (an increase is capped at max_p_mw, as in contingency_finder.gen_contingency),
        which is a lost injection of -direction * fraction * P_group at the gen buses, piecewise affine because of
        the caps. The gens stay connected, so they keep sharing the imbalance in opf.fcr if they have a weight. As
        their headroom would then change with the fraction, only groups of gens that do not take part in the FCR
        (no governor_kgover, as for wind and solar) are supported.
        """
        gens = model.gen
        max_p = gens["max_p_mw"].to_numpy(float)
        for name, gen_index in groups.items():
            positions = gens.index.get_indexer(gen_index)
            positions = positions[model.can_share[positions] & ~model.is_slack[positions]]   # non-zero dispatch
            participating = positions[model.participation[positions] > 0]
            if len(participating):
                raise NotImplementedError(
                    f"gen group {name}: {len(participating)} gens take part in the FCR (governor_kgover > 0, or "
                    f"max_p_mw weights without governor data), their headroom would change with the group's change")
            dispatch = model.dispatch_mw[positions]
            if direction < 0:
                segments = [(0.0, np.inf, np.zeros_like(dispatch), dispatch)]
            else:
                # This is because generators cannot be infinitely increased (contrary to loads)
                # Otherwise, the whole segment thing is not used
                headroom = np.where(np.isnan(max_p[positions]), np.inf, (max_p[positions] - dispatch).clip(min=0))
                with np.errstate(divide="ignore", invalid="ignore"):
                    caps = headroom / dispatch                  # fraction at which each gen reaches max_p_mw
                edges = [0.0, *np.unique(caps[np.isfinite(caps) & (caps > 0)]), np.inf]

                def capped_segments():
                    for start, end in zip(edges[:-1], edges[1:]):
                        middle = start + (min(end, start + 1.0) - start) / 2
                        is_capped = middle * dispatch >= headroom
                        yield (start, end, np.where(is_capped, -headroom, 0.0), np.where(is_capped, 0.0, -dispatch))
                segments = capped_segments()
            flows_at_zero, regimes = self._group_regimes(model, model.gen_ptdf[:, positions], segments, fraction_start)
            yield name, dispatch.sum(), flows_at_zero, regimes

    @staticmethod
    def _crossing(fixed_flow, proportional_flow, limit_mw, fraction_start, monitored):
        """fraction >= fraction_start at which |fixed_flow + proportional_flow * fraction| reaches limit_mw, per branch
        (fraction_start for branches already over; inf if never or not monitored)."""
        with np.errstate(divide="ignore", invalid="ignore"):
            crossing = (np.sign(proportional_flow) * limit_mw - fixed_flow) / proportional_flow
        crossing = np.where(proportional_flow == 0, np.inf, np.maximum(crossing, fraction_start))
        crossing = np.where(np.abs(fixed_flow + proportional_flow * fraction_start) > limit_mw, fraction_start, crossing)
        return np.where(monitored, crossing, np.inf)
    
    def _group_margins(self, group_regimes, direction, max_fraction, threshold, ignore_base_overloads, mw_column):
        """load_group_margins / gen_group_margins, from the (name, MW, flows at 0, regimes) of each group."""
        limit_mw = threshold * np.asarray(self.rating_mw, float)
        monitored = np.isfinite(limit_mw)
        if max_fraction is None:
            # A decrease by more than 100% is not possible (the output would become negative)
            max_fraction = 1.0 if direction < 0 else np.inf
        branch_names = self.branches.index.to_numpy()

        rows = {}
        for name, group_mw, flows_at_zero, regimes in group_regimes:
            base_overloaded = np.abs(flows_at_zero) > limit_mw
            is_monitored = monitored & ~base_overloaded if ignore_base_overloads else monitored
            best_fraction, best_branch = np.inf, None
            # Regimes are lazy: stop at the first one with a crossing (or past max_fraction)
            for fixed_flow, proportional_flow, fraction_start, fraction_end in regimes:
                if fraction_start > max_fraction:
                    break
                crossing = self._crossing(fixed_flow, proportional_flow, limit_mw, fraction_start, is_monitored)
                crossing = np.where(crossing <= min(fraction_end, max_fraction), crossing, np.inf)
                first = int(np.argmin(crossing))
                if crossing[first] < best_fraction:
                    best_fraction, best_branch = crossing[first], branch_names[first]
                if np.isfinite(best_fraction):
                    break                       # a later regime cannot cross earlier
            rows[name] = {mw_column: group_mw, "critical_percent": direction * best_fraction * 100,
                          "limiting_branch": best_branch,
                          "n_base_overloads": int((base_overloaded & monitored).sum())}
        return pd.DataFrame.from_dict(rows, orient="index",
                                      columns=[mw_column, "critical_percent", "limiting_branch", "n_base_overloads"])

    def _group_overloads(self, group_regimes, fraction, threshold, ignore_base_overloads):
        """load_group_overloads / gen_group_overloads, from the (name, MW, flows at 0, regimes) of each group,
        the regimes starting at abs(fraction)."""
        abs_fraction = abs(fraction)
        limit_mw = threshold * np.asarray(self.rating_mw, float)
        monitored = np.isfinite(limit_mw)
        branch_names = self.branches.index.to_numpy()

        overloads = {}
        for name, _, flows_at_zero, regimes in group_regimes:
            # Get correct regime
            fixed_flow, proportional_flow, _, _ = next(regime for regime in regimes if regime[2] <= abs_fraction <= regime[3])
            flows_mw = fixed_flow + proportional_flow * abs_fraction
            is_overloaded = monitored & (np.abs(flows_mw) > limit_mw)
            if ignore_base_overloads:
                is_overloaded &= ~(np.abs(flows_at_zero) > limit_mw)
            if is_overloaded.any():
                positions = np.where(is_overloaded)[0]
                overloads[name] = dict(zip(branch_names[positions],
                                           self.exceeded_limit_durations(positions, flows_mw[positions]).astype(int)))
        return overloads

    def load_group_margins(self, groups, direction=1, max_fraction=None, threshold=1.0,
                           ignore_base_overloads=True) -> pd.DataFrame:
        """
        Smallest load change of each group that overloads a branch once the imbalance is handled by
        the FCR model of opf.fcr. Flows come from PTDF, nothing is solved.

        `groups`: {group name: pandapower load indices}. The loads of a group all change by the same
        fraction t: increase (direction = +1) or decrease (-1) of their p_mw. The flows being
        piecewise affine in t, the first crossing of each rating is exact (within the DC model), no
        sweep needed. `max_fraction`: search limit (default inf for an increase, 1 = loads at 0 for a
        decrease). `threshold`: overload when |flow| > threshold * rating.
        `ignore_base_overloads`: branches already over their rating with no load change (after FCR) are
        not monitored, otherwise every group has a margin of 0.

        Returns a DataFrame indexed by group name: load_mw, critical_percent (signed: negative for
        a decrease, +-inf when no branch overloads before max_fraction), limiting_branch (None when
        none), n_base_overloads.
        """
        return self._group_margins(self._load_group_regimes(self._fcr_model(), groups, direction), direction,
                                   max_fraction, threshold, ignore_base_overloads, "load_mw")

    def load_group_overloads(self, groups, fraction, threshold=1.0, ignore_base_overloads=True) -> dict:
        """
        Same model as load_group_margins, for one given change: the loads of each group are multiplied
        by 1 + fraction (e.g. -0.5 for a 50 % decrease). Returns {group name: {overloaded branch:
        acceptable duration (s, -1 = permanent) of the highest limit exceeded}}, only for the groups
        that overload something.
        """
        regimes = self._load_group_regimes(self._fcr_model(), groups, 1 if fraction >= 0 else -1, abs(fraction))
        return self._group_overloads(regimes, fraction, threshold, ignore_base_overloads)

    def gen_group_margins(self, groups, direction=-1, max_fraction=None, threshold=1.0,
                          ignore_base_overloads=True) -> pd.DataFrame:
        """
        Same as load_group_margins for groups of generators, `groups` = {group name: pandapower gen indices}:
        the p_mw of the gens of a group all change by the same fraction, increase (direction = +1, capped at
        max_p_mw) or decrease (-1, default: that is what wind / solar clusters do). The gens must not take part
        in the FCR (see _gen_group_regimes). Returns the same DataFrame, with gen_mw (dispatch of the group).
        """
        return self._group_margins(self._gen_group_regimes(self._fcr_model(), groups, direction), direction,
                                   max_fraction, threshold, ignore_base_overloads, "gen_mw")

    def gen_group_overloads(self, groups, fraction, threshold=1.0, ignore_base_overloads=True) -> dict:
        """
        Same as load_group_overloads for groups of generators: the p_mw of the gens of each group are
        multiplied by 1 + fraction (e.g. -0.5), as in contingency_finder.gen_contingency.
        """
        regimes = self._gen_group_regimes(self._fcr_model(), groups, 1 if fraction >= 0 else -1, abs(fraction))
        return self._group_overloads(regimes, fraction, threshold, ignore_base_overloads)

    def iter_trip_flows(self, include_bridges=True, island_pairs=None, bridge_candidates=None):
        """
        Yields (is_bridge, name, key, flows, ignored) for every gen trip (and bridge
        outage) event: `flows` are the (L,) branch flows after the event and FCR
        redispatch, `ignored` flags branches that must not be monitored. `key` is the
        net.gen index of the tripped gen, the row of self.branches of the bridge, or
        the tuple of both rows of an islanding N-2 pair (`island_pairs`, shape (P, 2),
        see screen_n2; pairs count as bridges and are named by a tuple of names).
        `bridge_candidates`: positions the bridge outages are restricted to (see
        voltage_candidates; default: all bridges).
        See get_problematic_gen_and_bridges_trips for the model.
        """
        model = self._fcr_model()
        base_flows_mw, gen, ptdf, gen_ptdf = self.base_flows_mw, model.gen, model.ptdf, model.gen_ptdf
        dispatch_mw, is_slack = model.dispatch_mw, model.is_slack
        gen_bus_position, can_share = model.gen_bus_position, model.can_share

        # events: (is_bridge, name, key, lost MW, flow change of losing that injection,
        #          gens that stop sharing, branches to ignore, outaged pair or None)
        no_ignored_branches = np.zeros(len(base_flows_mw), bool)
        gen_names = gen["name"].where(gen["name"].notna(), pd.Series(gen.index, index=gen.index)).to_numpy()
        events = [(False, gen_names[gen_pos], gen.index[gen_pos], dispatch_mw[gen_pos],
                   dispatch_mw[gen_pos] * gen_ptdf[:, gen_pos], np.array([gen_pos]),
                   no_ignored_branches, None)
                  for gen_pos in np.where(can_share & ~is_slack)[0]]
        bridge_positions = np.where(self.bridges)[0]
        if bridge_candidates is not None:
            bridge_positions = np.intersect1d(bridge_positions, bridge_candidates)
        outages = [(bridge,) for bridge in bridge_positions] if include_bridges else []
        if island_pairs is not None:
            outages += [tuple(pair) for pair in island_pairs]
        events += [(True, event["name"], event["key"], event["lost_mw"], event["lost_flow_mw"],
                    event["gens"], event["excluded"], event["outage"] if len(event["outage"]) == 2 else None)
                   for event in self._islanding_events(gen_bus_position, is_slack, outages, ptdf)]

        for (is_bridge, name, key, lost_mw, lost_flow_mw, gens_stop_sharing,
             ignored_branches, outaged_pair) in events:
            flows_mw = base_flows_mw + self._fcr_flow_response(model, lost_mw, lost_flow_mw, gens_stop_sharing)
            if outaged_pair is not None:
                # Outaged pair removes a topological path between two busses. An additional term is thus necessary to take it into account (based on compound LODF)
                # remove the two branches: singular system (islanding), consistent right-hand side
                transfer = self.branch_transfer[:, outaged_pair]
                system = np.eye(2) - transfer[outaged_pair]
                delta = np.linalg.lstsq(system, flows_mw[outaged_pair], rcond=None)[0]
                residual_mw = np.abs(system @ delta - flows_mw[outaged_pair]).max()
                if residual_mw > ISLANDING_RESIDUAL_MW:
                    # the island is not balanced after removing P_S: no consistent solution.
                    # This means that there is an issue when computing the flow on pre outage branches, should not happen
                    # Indeed solution is correct only if flow has been compensated exactly by FCR (which should be the case)
                    # Residual > 0 means system has no solution
                    warnings.warn(f"islanding pair {name}: residual {residual_mw:.3g} MW, skipped")
                    continue
                flows_mw = flows_mw + transfer @ delta
            yield is_bridge, name, key, flows_mw, ignored_branches

    def get_problematic_gen_and_bridges_trips(self, threshold=1.0, include_bridges=True,
                                              island_pairs=None, bridge_candidates=None):
        """
        Generator trips (each in-service, non-slack gen with non-zero dispatch) that
        overload a branch once the imbalance is handled by the FCR model of opf.fcr.
        Flows come from PTDF, no power flow per trip.

        With `include_bridges`, bridge outages that island a slack-free set of buses
        are handled the same way, as the loss of that set's net injection (gens and
        loads, signed): all gens in the set stop sharing the imbalance, and branches
        touching the set are not monitored. `island_pairs` (see screen_n2) does
        the same for N-2 pairs that island a slack-free set; they are reported with
        the bridges, as a tuple of the two branch names. `bridge_candidates` restricts the
        bridge outages to those positions (e.g. voltage_candidates, to apply a voltage threshold).

        Mirrors opf.fcr: after the trip the slack mismatch M = (slack res p - slack
        setpoint) is spread over the in-service gens with non-zero dispatch, by
        governor_KGover (up to max_p_mw if M >= 0, else down to min_p_mw; what a gen at its limit
        cannot take is re-shared), and the slack goes back to its setpoint. M includes any base-case imbalance M0 (net.res_gen vs
        net.gen setpoints) plus the lost injection P_t. If nobody can pick it up the slack
        keeps it.

        Returns (problematic_gens, problematic_bridges, bridge_overloads): the gen names (index if
        unnamed) and the bridge names (or island pair tuples) whose loss loads a branch above
        `threshold` * rating, and for each problematic bridge {overloaded branch: acceptable
        duration (s, -1 = permanent) of the highest limit exceeded}.
        """
        rating_mw = np.asarray(self.rating_mw, float)
        problematic_gens, problematic_bridges, bridge_overloads = [], [], {}
        for is_bridge, name, _, flows, ignored_branches in self.iter_trip_flows(include_bridges, island_pairs, bridge_candidates):
            is_overloaded = (np.abs(flows) > threshold * rating_mw) & ~ignored_branches & ~self.already_overloaded
            if is_overloaded.any():
                (problematic_bridges if is_bridge else problematic_gens).append(name)
                if is_bridge:
                    positions = np.where(is_overloaded)[0]
                    bridge_overloads[name] = dict(zip(
                        self.branches.index[positions],
                        self.exceeded_limit_durations(positions, flows[positions]).astype(int)))
        return problematic_gens, problematic_bridges, bridge_overloads


# --------------------------------------------------------------------------
# Demo
# --------------------------------------------------------------------------
if __name__ == "__main__":
    import pypowsybl as ps
    from contingency_finder import ContingencyFinder

    ps_net = ps.network.load("temp copy.xiidm")
    finder = ContingencyFinder(ps_net)
    sensitivity_factors = DCSensitivityFactors(finder.pp_net, ps_net.get_operational_limits())
    branches = sensitivity_factors.branches

    voltage_thresh = 300                                     # kV, 0 = all branches
    problematic_n1, problematic_pairs, overloads = sensitivity_factors.get_problematic_n_minus_2(voltage_thresh)

    candidates, _ = sensitivity_factors.voltage_candidates(voltage_thresh)
    n_before = len(candidates)
    # drop outages already overloading at N-1
    candidates = candidates[~branches.index[candidates].isin(problematic_n1)]
    print(f"{n_before} candidate outages above {voltage_thresh} kV, "
          f"{n_before - len(candidates)} removed for N-1 overloads")
    violations, islanding = sensitivity_factors.screen_n2(candidates=candidates)
    print(f"{len(islanding)} islanding pairs, {len(violations)} overloads, "
          f"{len(violations.groupby(['outage_1', 'outage_2']))} problematic pairs")
    print(rank_pairs(violations, 10))
    if len(violations):
        worst = violations.iloc[0]
        print("max |error| vs pandapower DC (MW):",
              sensitivity_factors.validate_pair(worst.outage_1, worst.outage_2))
