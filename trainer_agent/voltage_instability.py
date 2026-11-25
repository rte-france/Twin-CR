"""
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Static voltage stability indices for a pandapower network on which a power flow
(Newton-Raphson, or any algorithm that stores Ybus/V in net._ppc) has been run.
 
    min_singular_value(net, reduced=False)  -> float
    l_index(net)                            -> (pd.Series per bus, float system index)
 
Both read the converged state (Ybus, V, bus types) from net._ppc["internal"],
so they reflect what the solver actually used (out-of-service elements, Q-limit
conversions PV->PQ if enforce_q_lims=True, etc.).
"""

import numpy as np
import pandas as pd
from scipy.sparse import bmat, csc_matrix
from scipy.sparse.linalg import LinearOperator, splu, spsolve, svds
 
from pandapower.pypower.dSbus_dV import dSbus_dV
 
_BUS_TYPE = 1  # column of ppc["bus"] holding the bus type
_NONE = 4      # bus type of isolated / out-of-service buses
 
 
# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _state(net):
    """Converged state of the last power flow, in ppci (solver) indexing."""
    if net.get("_ppc") is None or "internal" not in net._ppc:
        raise RuntimeError("Run a power flow first (pp.runpp(net)).")
    i = net._ppc["internal"]
    for key in ("Ybus", "V", "pv", "pq", "ref"):
        if key not in i:
            raise RuntimeError(f"'{key}' not found in net._ppc['internal']; "
                               "use runpp(..., algorithm='nr').")
    return i["Ybus"].tocsr(), np.asarray(i["V"]), i["ref"], i["pv"], i["pq"]
 
 
def _pp_bus_to_ppci(net):
    """Series: pandapower bus index -> ppci index (-1 if not in the solved grid)."""
    ppc_bus = net._ppc["bus"]
    active = ppc_bus[:, _BUS_TYPE] != _NONE
    ppc2ppci = np.full(len(ppc_bus), -1, dtype=int)
    ppc2ppci[active] = np.arange(active.sum())
    lookup = np.asarray(net._pd2ppc_lookups["bus"])  # pp bus index -> ppc index
    out = pd.Series(-1, index=net.bus.index, dtype=int)
    valid = (net.bus.index.values < len(lookup))
    ppc_idx = np.full(len(net.bus), -1, dtype=int)
    ppc_idx[valid] = lookup[net.bus.index.values[valid]]
    ok = ppc_idx >= 0
    out[ok] = ppc2ppci[ppc_idx[ok]]
    return out
 
 
def _jacobian(Ybus, V, ref, pv, pq):
    """Full polar power-flow Jacobian [[dP/dth, dP/dV], [dQ/dth, dQ/dV]]
    (p.u., rad), evaluated at the converged V. Rows/cols ordered pv, pq | pq."""
    dS_dVm, dS_dVa = dSbus_dV(Ybus, V)
    pvpq = np.r_[pv, pq]
    J = bmat([
        [dS_dVa[pvpq][:, pvpq].real, dS_dVm[pvpq][:, pq].real],
        [dS_dVa[pq][:, pvpq].imag,   dS_dVm[pq][:, pq].imag],
    ], format="csc")
    return J, len(pvpq), len(pq)
 
 
def _sigma_min_dense(J, n_pvpq, n_pq, reduced):
    J = J.toarray()
    if reduced:
        Jpt, Jpv = J[:n_pvpq, :n_pvpq], J[:n_pvpq, n_pvpq:]
        Jqt, Jqv = J[n_pvpq:, :n_pvpq], J[n_pvpq:, n_pvpq:]
        J = Jqv - Jqt @ np.linalg.solve(Jpt, Jpv)
    return np.linalg.svd(J, compute_uv=False)[-1]
 
 
def _sigma_min_sparse(J, n_pvpq, n_pq, reduced):
    """sigma_min = 1 / sigma_max(inverse), the latter found with ARPACK using an
    LU of J only (no squaring of the condition number).
    The inverse of the reduced Jacobian is the QV block of inv(J) (Schur complement)."""
    lu = splu(J)
    n = J.shape[0]
    if reduced:
        n_op = n_pq
        def matvec(v):
            rhs = np.zeros(n); rhs[n_pvpq:] = np.ravel(v)
            return lu.solve(rhs)[n_pvpq:]
        def rmatvec(w):
            rhs = np.zeros(n); rhs[n_pvpq:] = np.ravel(w)
            return lu.solve(rhs, trans="T")[n_pvpq:]
    else:
        n_op = n
        matvec = lambda v: lu.solve(np.ravel(v))
        rmatvec = lambda w: lu.solve(np.ravel(w), trans="T")
    Jinv = LinearOperator((n_op, n_op), matvec=matvec, rmatvec=rmatvec, dtype=float)
    smax = svds(Jinv, k=1, which="LM", return_singular_vectors=False)[0]
    return 1.0 / smax
 
 
# --------------------------------------------------------------------------- #
# 1. Minimum singular value of the power flow Jacobian
# --------------------------------------------------------------------------- #
def min_singular_value(net, reduced=False, dense_max=500):
    """Minimum singular value of the power flow Jacobian (or of the reduced
    Jacobian J_R = J_QV - J_Qth J_Pth^-1 J_PV if reduced=True).
 
    It goes to 0 at the saddle-node bifurcation. Values are in p.u. and are only
    comparable between states of the *same* network (same base, same bus
    types, same set of PV/PQ buses). Not linear in MW margin.
    """
    Ybus, V, ref, pv, pq = _state(net)
    J, n_pvpq, n_pq = _jacobian(Ybus, V, ref, pv, pq)
    if reduced and n_pq == 0:
        raise ValueError("No PQ bus: reduced Jacobian is empty.")
    size = n_pq if reduced else J.shape[0]
    if size <= dense_max or size < 3:
        return float(_sigma_min_dense(J, n_pvpq, n_pq, reduced))
    return float(_sigma_min_sparse(J, n_pvpq, n_pq, reduced))
 
 
# --------------------------------------------------------------------------- #
# 2. L-index (Kessel & Glavitsch)
# --------------------------------------------------------------------------- #
def l_index(net):
    """L-index of every load (PQ) bus and the system index max_j L_j.
 
    With the bus admittance matrix partitioned into load (L) and generator (G,
    i.e. PV + slack) buses:
        F = -Y_LL^-1 Y_LG ,   L_j = | 1 - sum_i F_ji V_i / V_j |   (i in G)
    L_j lies in [0, 1]; 1 means voltage collapse at bus j.
 
    Returns
    -------
    L_bus : pd.Series indexed by net.bus index (NaN for non-PQ / not solved buses)
    L_sys : float, max over all load buses
    """
    Ybus, V, ref, pv, pq = _state(net)
    gen = np.r_[ref, pv]
 
    Y_LL = csc_matrix(Ybus[pq][:, pq])
    Y_LG = Ybus[pq][:, gen]
 
    # F V_G = -Y_LL^-1 (Y_LG V_G): a single sparse solve, no explicit inverse
    FV = -spsolve(Y_LL, Y_LG @ V[gen])
    L = np.abs(1.0 - FV / V[pq])
 
    # map back to pandapower bus indices
    ppci_of_pp = _pp_bus_to_ppci(net)
    L_ppci = pd.Series(L, index=pq)
    L_bus = pd.Series(np.nan, index=net.bus.index, name="L_index")
    for bus, k in ppci_of_pp.items():
        if k in L_ppci.index:
            L_bus[bus] = L_ppci[k]
    return L_bus, float(L.max())
 