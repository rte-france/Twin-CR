"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import copy
import math
import numpy as np
import pandas as pd
import pandapower as pp


network = None


def _patch_opf_model_linear_constraints():
    """pandapower's opf_model.linear_constraints() densifies each constraint
    block into a numpy array and assigns it into a lil_matrix via fancy
    indexing (its own source even flags this: "FIXME: Sparse matrix with
    fancy indexing"). For big networks (~7k buses, ~19k OPF variables)
    that dense-then-lil-assign step dominates runtime (~23s of ~28s per
    pp_opf() call). This replaces it with an equivalent that stays sparse
    throughout (COO triplet assembly), giving identical A/l/u (verified
    bit-for-bit) about 7x faster.
    """
    import numpy as np
    from scipy.sparse import coo_matrix
    from pandapower.pypower.opf_model import opf_model

    def linear_constraints(self):
        if not self.lin["N"]:
            return None, np.array([]), np.array([])

        nvar = self.var["N"]
        nlin = self.lin["N"]
        u = np.full(nlin, np.inf)
        l = -u
        rows_all, cols_all, data_all = [], [], []

        for k in range(self.lin["NS"]):
            name = self.lin["order"][k]
            N = self.lin["idx"]["N"][name]
            if not N:
                continue
            Ak = self.lin["data"]["A"][name].tocsc()
            i1 = self.lin["idx"]["i1"][name]
            iN = self.lin["idx"]["iN"][name]
            kN = 0
            for v in self.lin["data"]["vs"][name]:
                j1 = self.var["idx"]["i1"][v]
                jN = self.var["idx"]["iN"][v]
                k1 = kN
                kN = kN + self.var["idx"]["N"][v]
                sub = Ak[:, k1:kN].tocoo()
                if sub.nnz:
                    rows_all.append(sub.row + i1)
                    cols_all.append(sub.col + j1)
                    data_all.append(sub.data)
            l[i1:iN] = self.lin["data"]["l"][name]
            u[i1:iN] = self.lin["data"]["u"][name]

        if rows_all:
            rows_all = np.concatenate(rows_all)
            cols_all = np.concatenate(cols_all)
            data_all = np.concatenate(data_all)
        else:
            rows_all, cols_all, data_all = np.array([]), np.array([]), np.array([])

        A = coo_matrix((data_all, (rows_all, cols_all)), shape=(nlin, nvar)).tocsr()
        return A, l, u

    opf_model.linear_constraints = linear_constraints


def _patch_enforce_controllable():
    """pandapower 3.x _enforce_controllable_vm_pu_p_mw() builds its
    `not_controllable` mask over in-service generators only (gen_is), but then
    uses it to index the full net.gen columns ("bus", "vm_pu", "p_mw"). As soon
    as one generator is out of service (or isolated by a contingency) the mask
    length no longer matches and rundcopp/runopp crashes with
    "IndexError: boolean index did not match". This restricts those columns to
    the in-service generators first.
    """
    import numpy as np
    import pandapower.build_gen as build_gen
    from pandapower.pypower.idx_bus import VMAX, VMIN
    from pandapower.pypower.idx_gen import PMIN, PMAX

    def _enforce_controllable_vm_pu_p_mw(net, ppc, gen_is, f, t):
        delta = net["_options"]["delta"]
        bus_lookup = net["_pd2ppc_lookups"]["bus"]
        controllable = net["gen"]["controllable"].values[gen_is]
        not_controllable = ~controllable.astype(bool)

        # if there are some non-controllable gens -> set vm_pu and p_mw fixed
        if np.any(not_controllable):
            bus = net["gen"]["bus"].values[gen_is][not_controllable]
            vm_pu = net["gen"]["vm_pu"].values[gen_is][not_controllable]
            p_mw = net["gen"]["p_mw"].values[gen_is][not_controllable]

            not_controllable_buses = bus_lookup[bus]
            ppc["bus"][not_controllable_buses, VMAX] = vm_pu + delta
            ppc["bus"][not_controllable_buses, VMIN] = vm_pu - delta

            not_controllable_gens = np.arange(f, t)[not_controllable]
            ppc["gen"][not_controllable_gens, PMIN] = p_mw - delta
            ppc["gen"][not_controllable_gens, PMAX] = p_mw + delta
        return ppc

    build_gen._enforce_controllable_vm_pu_p_mw = _enforce_controllable_vm_pu_p_mw


def _patch_makeAy():
    """pandapower's makeAy() (builds the pwl-cost "y" auxiliary-variable
    constraint matrix) fills a lil_matrix one scalar at a time in a Python
    loop, explicitly to work around a scipy 0.7.2 bug (the vectorized
    slice-assignment replacement is written but commented out in the same
    file). For big network (5630 pwl generators) this dominates opf_setup: ~13.4s
    of ~122s across 101 contingencies.

    A first version replaced the scalar lil writes with a COO triplet build
    but kept the per-generator Python loop (still ~5629 iterations x2, each
    allocating tiny numpy arrays) - only ~19% faster, since the killed part
    was the pathological one, not the loop itself. Since every pwl
    generator here uses the same cost-segment count (verified: NCOST==3,
    i.e. 2 segments, for all 5629 pwl rows, none reactive), the whole
    row/col/data build can be vectorized across all generators at once with
    no Python loop - verified bit-identical Ay/by against the per-generator
    version. Falls back to that per-generator loop when segment counts
    aren't uniform, so this stays correct for other pandapower users too.
    """
    import numpy as np
    from scipy.sparse import coo_matrix
    from numpy import diff, any as np_any, zeros, array, int64
    from numpy import flatnonzero as find
    from pandapower.pypower.idx_cost import MODEL, PW_LINEAR, NCOST, COST
    import pandapower.pypower.opf_setup as opf_setup_mod

    def makeAy_per_generator(baseMVA, ng, gencost, iycost, pgbas, qgbas, ybas):
        ny = iycost.shape[0]
        m_total = int(np.sum(gencost[iycost, NCOST].astype(int64)))
        nrows = m_total - ny

        rows_list, cols_list, data_list, by_list = [], [], [], []
        k = 0
        for i in iycost:
            ns = int(gencost[i, NCOST])
            p = gencost[i, COST:COST + 2 * ns - 1:2] / baseMVA
            c = gencost[i, COST + 1:COST + 2 * ns:2]
            mslope = diff(c) / diff(p)
            if np_any(diff(p) == 0):
                print('makeAy: bad x axis data in row %d of gencost matrix' % i)
            b = mslope * p[:ns - 1] - c[:ns - 1]
            by_list.append(b)
            sidx = (qgbas + (i - ng) - 1) if i > ng else (pgbas + i - 1)
            seg = ns - 1
            rows_list.append(np.arange(k, k + seg))
            cols_list.append(np.full(seg, sidx))
            data_list.append(mslope)
            k += seg

        k = 0
        for j, i in enumerate(iycost):
            ns = int(gencost[i, NCOST])
            seg = ns - 1
            rows_list.append(np.arange(k, k + seg))
            cols_list.append(np.full(seg, ybas + j - 1))
            data_list.append(-np.ones(seg))
            k += seg

        return rows_list, cols_list, data_list, by_list, nrows

    def makeAy(baseMVA, ng, gencost, pgbas, qgbas, ybas):
        iycost = find(gencost[:, MODEL] == PW_LINEAR)
        ny = iycost.shape[0]
        ncols = ybas + ny - 1
        if ny == 0:
            return zeros((0, ncols)), array([])

        ns_vals = gencost[iycost, NCOST].astype(int64)
        ns0 = ns_vals[0]

        if np.any(ns_vals != ns0):
            rows_list, cols_list, data_list, by_list, nrows = \
                makeAy_per_generator(baseMVA, ng, gencost, iycost, pgbas, qgbas, ybas)
        else:
            seg = int(ns0) - 1
            p_cols = np.arange(COST, COST + 2 * ns0 - 1, 2)
            c_cols = np.arange(COST + 1, COST + 2 * ns0, 2)
            P = gencost[np.ix_(iycost, p_cols)] / baseMVA
            C = gencost[np.ix_(iycost, c_cols)]
            dP = diff(P, axis=1)
            dC = diff(C, axis=1)
            if np_any(dP == 0):
                print('makeAy: bad x axis data in gencost matrix')
            mslope = dC / dP
            b = mslope * P[:, :seg] - C[:, :seg]

            sidx = np.where(iycost > ng,
                             (qgbas if np.size(qgbas) else 0) + (iycost - ng) - 1,
                             pgbas + iycost - 1)

            row_base = np.arange(ny) * seg
            rows_pg = (row_base[:, None] + np.arange(seg)[None, :]).ravel()
            cols_pg = np.repeat(sidx, seg)
            cols_y = np.repeat(ybas + np.arange(ny) - 1, seg)

            rows_list = [rows_pg, rows_pg]
            cols_list = [cols_pg, cols_y]
            data_list = [mslope.ravel(), np.full(ny * seg, -1.0)]
            by_list = [b.ravel()]
            nrows = ny * seg

        rows_all = np.concatenate(rows_list)
        cols_all = np.concatenate(cols_list)
        data_all = np.concatenate(data_list)
        by = np.concatenate(by_list) if by_list else array([])

        Ay = coo_matrix((data_all, (rows_all, cols_all)), shape=(nrows, ncols)).tocsr()
        return Ay, by

    # opf_setup.py did `from pandapower.pypower.makeAy import makeAy`, so the
    # name to patch is the one bound in opf_setup's own namespace, not the
    # makeAy module's.
    opf_setup_mod.makeAy = makeAy


def _patch_fill_gencost_pwl():
    """pandapower's _fill_gencost_pwl()/costs_from_areas() convert each
    generator's pwl cost segments into cumulative (breakpoint, cost) pairs
    with a pure-Python per-generator, per-segment loop (~2.3s of ~122s
    across 101 contingencies here, called once per pwl generator per solve
    - 5630 generators). When every generator in a cost group has the same
    number of segments (true for this script's redispatch cost, always 2
    segments), the whole group can be vectorized with numpy in one shot.
    Falls back to the original per-row implementation for any group with a
    non-uniform segment count, so this stays correct for other pandapower
    users too.
    """
    import numpy as np
    from pandapower.pypower.idx_cost import COST, NCOST
    import pandapower.opf.make_objective as mo_mod

    orig_costs_from_areas = mo_mod.costs_from_areas

    def _fill_gencost_pwl(ppci, net):
        for power_mode, cost in net.pwl_cost.groupby("power_type"):
            gens, cost, signs = mo_mod._map_costs_to_gen(net, cost)
            if power_mode == "q":
                gens = gens + len(ppci["gen"])
            if len(gens) == 0:
                continue

            pts = cost.points.values
            lengths = {len(p) for p in pts}
            if len(lengths) != 1:
                for gen, points, sign in zip(gens, pts, signs):
                    costs = orig_costs_from_areas(points, sign)
                    ppci["gencost"][gen, COST:COST + len(costs)] = costs
                    ppci["gencost"][gen, NCOST] = len(costs) / 2
                continue

            nseg = lengths.pop()
            arr = np.array([list(p) for p in pts], dtype=float)  # (ngen, nseg, 3)
            lower, upper, slope = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
            sign = signs.astype(float)

            if nseg > 1 and np.any(lower[:, 1:] != upper[:, :-1]):
                raise ValueError("Non-consecutive cost function areas")

            deltas = (upper - lower) * slope * sign[:, None]
            y0 = lower[:, 0] * slope[:, 0] * sign
            cum_deltas = np.cumsum(deltas, axis=1)
            breakpoints_x = np.concatenate([lower[:, :1], upper], axis=1)
            breakpoints_y = np.concatenate([y0[:, None], y0[:, None] + cum_deltas], axis=1)

            ncols = 2 * (nseg + 1)
            costs_interleaved = np.empty((len(gens), ncols))
            costs_interleaved[:, 0::2] = breakpoints_x
            costs_interleaved[:, 1::2] = breakpoints_y

            ppci["gencost"][gens[:, None], COST + np.arange(ncols)] = costs_interleaved
            ppci["gencost"][gens, NCOST] = nseg + 1

    # _make_objective() calls _fill_gencost_pwl by bare name within the same
    # module, so patching the module attribute here is sufficient.
    mo_mod._fill_gencost_pwl = _fill_gencost_pwl


def _patch_add_dcline_gens():
    """pandapower's _add_dcline_gens() loops net.dcline rows and calls the
    validation-heavy create_gen() twice per row (~3.8s of ~122s across 101
    contingencies here, for all DC lines re-added on every OPF solve).
    This replaces it with two vectorized arrays fed through pandapower's own
    bulk create_gens() in one call, interleaved as (to, from) pairs per DC
    line to preserve the exact row order downstream code relies on
    (_get_gen_index() in make_objective.py assumes the last 2*n_dcline gen
    rows are (to, from) pairs indexed by dcline position).
    """
    import numpy as np
    import pandapower.auxiliary as aux_mod

    def _add_dcline_gens(net):
        from pandapower.create import create_gens
        dc = net.dcline
        n = len(dc)
        if n == 0:
            return
        p_mw = np.abs(dc["p_mw"].values.astype(float))
        loss_percent = dc["loss_percent"].values.astype(float)
        loss_mw = dc["loss_mw"].values.astype(float)
        max_p_mw = dc["max_p_mw"].values.astype(float)
        p_loss = p_mw * (1 - loss_percent / 100) - loss_mw
        pos = np.sign(dc["p_mw"].values) > 0

        p_to = np.where(pos, p_loss, -p_mw)
        p_from = np.where(pos, -p_mw, p_loss)
        p_max_to = np.where(pos, max_p_mw, 0.0)
        p_min_to = np.where(pos, 0.0, -max_p_mw)

        # rows are interleaved (to, from) per dcline, matching the row order
        # _get_gen_index() in make_objective.py assumes for the trailing
        # 2*n_dcline gen rows
        def interleave(to_vals, from_vals, dtype=float):
            out = np.empty(2 * n, dtype=dtype)
            out[0::2] = to_vals
            out[1::2] = from_vals
            return out

        buses = interleave(dc["to_bus"].values, dc["from_bus"].values, dtype=dc["to_bus"].values.dtype)
        p_mw_arr = interleave(p_to, p_from)
        vm_pu_arr = interleave(dc["vm_to_pu"].values, dc["vm_from_pu"].values)
        min_p_arr = interleave(p_min_to, -p_max_to)
        max_p_arr = interleave(p_max_to, -p_min_to)
        maxq_arr = interleave(dc["max_q_to_mvar"].values, dc["max_q_from_mvar"].values)
        minq_arr = interleave(dc["min_q_to_mvar"].values, dc["min_q_from_mvar"].values)
        inservice_arr = interleave(dc["in_service"].values, dc["in_service"].values, dtype=bool)

        create_gens(net, buses=buses, p_mw=p_mw_arr, vm_pu=vm_pu_arr,
                    min_p_mw=min_p_arr, max_p_mw=max_p_arr,
                    max_q_mvar=maxq_arr, min_q_mvar=minq_arr,
                    in_service=inservice_arr)

    # _add_auxiliary_elements() calls _add_dcline_gens by bare name within
    # the same module, so patching the module attribute here is sufficient.
    aux_mod._add_dcline_gens = _add_dcline_gens


def _patch_pips_csr_stacking():
    """pips.py's Newton loop rebuilds the full KKT matrix on every iteration
    via vstack([hstack([M, dg]), hstack([dg.T, zero])]) with no format hint,
    so scipy assembles it in whatever format concatenation naturally
    produces before the explicit Ab.tocsr() call two lines later - wasting a
    conversion pass on every one of the ~30 iterations per contingency.
    Wrapping vstack/hstack to default format="csr" (only when the caller
    didn't already specify one, e.g. the nonlinear-path calls elsewhere in
    the same function) makes that follow-up .tocsr() a no-op. Verified
    bit-identical across every iteration's KKT matrix, not just the final
    result.
    """
    import pandapower.pypower.pips as pips_mod

    orig_vstack = pips_mod.vstack
    orig_hstack = pips_mod.hstack

    def vstack_csr(blocks, format=None, dtype=None):
        return orig_vstack(blocks, format=format or "csr", dtype=dtype)

    def hstack_csr(blocks, format=None, dtype=None):
        return orig_hstack(blocks, format=format or "csr", dtype=dtype)

    pips_mod.vstack = vstack_csr
    pips_mod.hstack = hstack_csr


def _patch_pips_diagonal_elim():
    """pips.py's Newton loop builds two niq x niq diagonal sparse matrices
    from scratch every iteration - zinvdiag = diag(1/z) and mudiag = diag(mu)
    - and uses them only to rescale the columns of the (constant, for our
    non-nonlinear DC OPF) sparse Jacobian "dh", or to rescale a dense vector.
    Both are plain elementwise operations in disguise: scaling dh's columns
    by a vector needs no diagonal matrix or sparse-sparse matmul at all, just
    dh.data *= scale[column_of_each_entry]. This removes 2 sparse diagonal
    constructions and 2 sparse-sparse matmuls per iteration, leaving only the
    one genuine matrix product (dh_scaled * dh.T) needed to form the KKT
    block M. Verified bit-identical (M and N match exactly, every iteration)
    against the original, ~1.35x faster per solve on the big network.

    dh = Ai.T where Ai is CSR - and scipy's CSR.transpose() returns CSC, not
    CSR - so dh.indices holds ROW indices, not column indices. The per-entry
    column index has to be derived from CSC's indptr structure instead
    (repeat(arange(ncols), diff(indptr))), precomputed once since dh's
    sparsity pattern never changes when nonlinear=False. The nonlinear path
    (unused by this script - DC OPF has no nonlinear constraints) reassigns
    dh every iteration, so it keeps pandapower's original zinvdiag/mudiag
    code entirely untouched rather than risk misapplying this shortcut
    there.

    Also replaces the builtin min()/max() calls that reduce over full-sized
    arrays (niq ~= 27000 for big network) with their vectorized .min()/.max()
    methods: max(h) and min(z[k]/-dz[k])/min(mu[k]/-dmu[k]) iterate
    element-by-element in pure Python over arrays sized by the number of
    inequality constraints, not the tiny 2-element lists the *other*
    min()/max() calls in this function operate on (those are left as
    builtins - converting them would add array-construction overhead for
    no benefit). Verified bit-identical res_gen output, ~7% faster per
    solve on top of the diagonal-elimination change above.

    Both fixes are applied to the same source text and executed together in
    one exec() call (patching pips.py source text so the ~95% of this ~300
    line solver function this doesn't touch - convergence tolerances,
    step-size logic, multiplier bookkeeping - stays byte-identical to
    pandapower's own code, not retyped by hand). Raises if the expected
    source text isn't found, rather than silently falling back, so an
    incompatible pandapower version fails loudly instead of silently
    reverting to the (still-correct, just slower) original.
    """
    import inspect
    import numpy as np
    import pandapower.pypower.pips as pips_mod
    import pandapower.pypower.qps_pips as qps_pips_mod

    src = inspect.getsource(pips_mod)

    old_setup = '''        dh = None if Ai is None else Ai.T     # 1st derivative of inequalities
        dg = None if Ae is None else Ae.T     # 1st derivative of equalities'''
    new_setup = '''        dh = None if Ai is None else Ai.T     # 1st derivative of inequalities
        dg = None if Ae is None else Ae.T     # 1st derivative of equalities
        if dh is not None:
            dh = dh.tocsc()
            _dh_col_idx = repeat(arange(dh.shape[1]), diff(dh.indptr))
        else:
            _dh_col_idx = None'''

    old_block = '''        rz = range(len(z))
        zinvdiag = sparse((1.0 / z, (rz, rz))) if len(z) else None
        rmu = range(len(mu))
        mudiag = sparse((mu, (rmu, rmu))) if len(mu) else None
        dh_zinv = None if dh is None else dh * zinvdiag
        M = Lxx if dh is None else Lxx + dh_zinv * mudiag * dh.T
        N = Lx if dh is None else Lx + dh_zinv * (mudiag * h + gamma * e)'''
    new_block = '''        if dh is None:
            dh_zinv = None
            M = Lxx
            N = Lx
        elif nonlinear:
            rz = range(len(z))
            zinvdiag = sparse((1.0 / z, (rz, rz))) if len(z) else None
            rmu = range(len(mu))
            mudiag = sparse((mu, (rmu, rmu))) if len(mu) else None
            dh_zinv = dh * zinvdiag
            M = Lxx + dh_zinv * mudiag * dh.T
            N = Lx + dh_zinv * (mudiag * h + gamma * e)
        else:
            zinv = 1.0 / z
            scale = zinv[_dh_col_idx]
            dh_zinv = dh.copy()
            dh_zinv.data = dh.data * scale
            dh_scaled = dh.copy()
            dh_scaled.data = dh.data * scale * mu[_dh_col_idx]
            M = Lxx + dh_scaled * dh.T
            N = Lx + dh_zinv * (mu * h + gamma * e)'''

    old_dmu = '        dmu = -mu if dh is None else -mu + zinvdiag * (gamma * e - mudiag * dz)'
    new_dmu = '''        if dh is None:
            dmu = -mu
        elif nonlinear:
            dmu = -mu + zinvdiag * (gamma * e - mudiag * dz)
        else:
            dmu = -mu + zinv * (gamma * e - mu * dz)'''

    minmax_replacements = [
        ("    maxh = zeros(1) if len(h) == 0 else max(h)",
         "    maxh = zeros(1) if len(h) == 0 else h.max()"),
        ("        alphap = min([xi * min(z[k] / -dz[k]), 1]) if len(k) else 1.0",
         "        alphap = min([xi * (z[k] / -dz[k]).min(), 1]) if len(k) else 1.0"),
        ("        alphad = min([xi * min(mu[k] / -dmu[k]), 1]) if len(k) else 1.0",
         "        alphad = min([xi * (mu[k] / -dmu[k]).min(), 1]) if len(k) else 1.0"),
        ("            maxh = max(h)",
         "            maxh = h.max()"),
    ]

    if old_setup not in src or old_block not in src or old_dmu not in src or \
            any(old not in src for old, _ in minmax_replacements):
        raise RuntimeError(
            "pandapower.pypower.pips source doesn't match the expected text "
            "(pandapower version mismatch?) - refusing to apply the "
            "diagonal-elimination/min-max patch rather than risk a silent bug"
        )

    patched_src = (
        src.replace(old_setup, new_setup)
           .replace(old_block, new_block)
           .replace(old_dmu, new_dmu)
    )
    for old, new in minmax_replacements:
        patched_src = patched_src.replace(old, new)

    namespace = dict(pips_mod.__dict__)
    namespace["diff"] = np.diff
    namespace["arange"] = np.arange
    namespace["repeat"] = np.repeat
    exec(compile(patched_src, pips_mod.__file__, "exec"), namespace)

    # qps_pips.py did `from pandapower.pypower.pips import pips`, so the
    # name to patch is the one bound in qps_pips's own namespace.
    qps_pips_mod.pips = namespace["pips"]


_patch_opf_model_linear_constraints()
_patch_makeAy()
_patch_enforce_controllable()
_patch_fill_gencost_pwl()
_patch_add_dcline_gens()
_patch_pips_csr_stacking()
_patch_pips_diagonal_elim()


def _pypowsybl_to_pandapower(psn, governor_kgover=None):
    """Convert a pypowsybl network to pandapower without a MATPOWER round-trip.

    IIDM units used by pypowsybl:
      Lines         – r, x in Ω (total series), g1/b1/g2/b2 in S (shunt each end)
      Transformers  – r, x in Ω referenced to the LV (side-2) rated voltage,
                      g, b in S; rated_s in MVA
      Shunts        – g, b in S, accumulated for the active section count
    Tap-changer rho (if present) is absorbed into vn_hv_kv (not vn_lv_kv) so
    pandapower sees the correct effective turns ratio for the current tap
    position without perturbing the LV-referenced impedance base used to
    convert vk_percent/vkr_percent back to ohms internally.
    """
    net = pp.create_empty_network(f_hz=50)

    # ---- buses ----
    buses = psn.get_buses()
    vlevels = psn.get_voltage_levels()[["nominal_v"]]
    vn_kv = buses["voltage_level_id"].map(vlevels["nominal_v"])
    pp_bus_idx = pp.create_buses(net, nr_buses=len(buses),
                                  vn_kv=vn_kv.values, name=buses.index.tolist())
    bus_lookup = pd.Series(pp_bus_idx, index=buses.index)
    # Synchronous components linked to the main grid only through HVDC (e.g. UK) cannot be solved together with it
    # by pandapower: the main grid is the largest synchronous component, everything else is a foreign island.
    synchronous_component_by_bus = buses["synchronous_component"]
    main_synchronous_component = synchronous_component_by_bus.value_counts().idxmax()

    # ---- permanent current limits ----
    all_lim = psn.get_operational_limits()
    # Remove limits of lines < 200kv
    lines = psn.get_lines()
    # lines = lines.join(vlevels, on="voltage_level1_id")
    # all_lim = all_lim[~all_lim.index.isin(lines.loc[lines["nominal_v"] < 200].index)]
    cur_lim = all_lim[all_lim.index.get_level_values("type") == "CURRENT"]
    line_ilim = (
        cur_lim[cur_lim["element_type"] == "LINE"]
        .groupby("element_id")["value"].min()
    )
    trafo_ilim = (
        cur_lim[(cur_lim["element_type"] == "TWO_WINDINGS_TRANSFORMER") &
                (cur_lim.index.get_level_values("side") == "TWO")]
        .groupby("element_id")["value"].min()
    )

    # ---- lines (bulk) ----
    lines = lines[
        lines["bus1_id"].isin(bus_lookup.index) &
        lines["bus2_id"].isin(bus_lookup.index)
    ]
    b_tot = lines["b1"].values + lines["b2"].values
    g_tot = lines["g1"].values + lines["g2"].values
    line_max_i_ka = line_ilim.reindex(lines.index).values / 1000
    # np.nan_to_num(line_max_i_ka, copy=False, posinf=1e2)
    max_loading_percent = line_max_i_ka / line_max_i_ka * 100
    np.nan_to_num(max_loading_percent, copy=False)
    pp.create_lines_from_parameters(
        net,
        from_buses=lines["bus1_id"].map(bus_lookup).astype(int).values,
        to_buses=lines["bus2_id"].map(bus_lookup).astype(int).values,
        length_km=1.0,
        r_ohm_per_km=lines["r"].values,
        x_ohm_per_km=lines["x"].values,
        c_nf_per_km=b_tot / (2 * math.pi * 50) * 1e9,
        g_us_per_km=g_tot * 1e6,
        max_i_ka=line_max_i_ka,
        name=lines.index.tolist(),
        in_service=(lines["connected1"] & lines["connected2"]).values,
        max_loading_percent=max_loading_percent
    )

    # ---- ratio tap changer rho at current tap position ----
    tap_rho = {}
    rtc = psn.get_ratio_tap_changers()
    rtc_steps = psn.get_ratio_tap_changer_steps()
    for tid, tap_pos in rtc["tap"].items():
        try:
            tap_rho[tid] = float(rtc_steps.loc[(tid, int(tap_pos)), "rho"])
        except (KeyError, TypeError):
            pass

    # ---- phase tap changer alpha and rho (phase-shifting transformers) at current tap ----
    # Real PSTs are usually combined ratio+angle devices, so their steps carry a "rho" too
    # (on top of "alpha"), separate from - and never on the same transformer as - a ratio
    # tap changer. Feeding it into the same tap_rho map used above is therefore safe.
    tap_alpha = {}
    ptc = psn.get_phase_tap_changers()
    ptc_steps = psn.get_phase_tap_changer_steps()
    for tid, tap_pos in ptc["tap"].items():
        try:
            step = ptc_steps.loc[(tid, int(tap_pos))]
            tap_alpha[tid] = float(step["alpha"])
            tap_rho[tid] = float(step["rho"])
        except (KeyError, TypeError):
            pass

    # ---- 2-winding transformers (bulk) ----
    trafos = psn.get_2_windings_transformers()
    trafos = trafos[
        trafos["bus1_id"].isin(bus_lookup.index) &
        trafos["bus2_id"].isin(bus_lookup.index)
    ]
    i_lim = trafo_ilim.reindex(trafos.index).values
    sn = trafos["rated_s"].values
    vn_hv = trafos["rated_u1"].values
    vn_lv = trafos["rated_u2"].values
    missing_sn = np.isnan(sn)
    if missing_sn.any():
        sn_est = math.sqrt(3) * vn_lv * i_lim / 1000
        # 42% of transformers have neither rated_s nor a side-TWO current
        # limit, leaving sn_est NaN; that NaN reaches vk_percent/vkr_percent/
        # i0_percent and pandapower then raises FloatingPointError in _wye_delta.
        # A placeholder is safe for flows: sn cancels out of the impedance
        # conversion (pandapower rebuilds ohms as vk_percent/100 * vn_lv**2/sn_mva),
        # and max_loading below is already NaN -> 0 for exactly these transformers
        # since it is driven by the same missing i_lim.
        sn_est = np.where(np.isnan(sn_est), 100.0, sn_est)
        sn = np.where(missing_sn, sn_est, sn)
    r = trafos["r"].values
    x = trafos["x"].values
    g = trafos["g"].values
    b = trafos["b"].values
    z_base = vn_lv ** 2 / sn
    rho = trafos.index.to_series().map(tap_rho).fillna(1.0).values
    # pandapower's shift_degree is the negative of IIDM's alpha (verified empirically
    # against pypowsybl's own DC solve on the big network, which has 50 active
    # phase-shifting transformers: shift_degree=alpha doubled the flow error at every
    # PST-adjacent line, while shift_degree=-alpha matched to ~1 MW).
    shift_degree = -trafos.index.to_series().map(tap_alpha).fillna(0.0).values
    # Claude proposal contained a default 100 value, but it is hit in iidm, so I don't put it
    max_loading = 100.0 * math.sqrt(3) * vn_lv * i_lim / 1000 / sn
    np.nan_to_num(max_loading, copy=False)

    # vk_percent must carry the SIGN of x: pandapower recovers reactance as
    # x_sc = sign(z_sc) * sqrt(z_sc**2 - r_sc**2) (build_branch._calc_r_x_from_dataframe),
    # so an unsigned sqrt(r**2 + x**2) silently flips every negative-reactance transformer
    # (111 of them in big network, down to -7.3 ohm - real for 400/225 kV autotransformers),
    # inverting its susceptance and badly corrupting loop flows around it.
    vk_percent = np.where(x < 0, -1.0, 1.0) * np.maximum(
        np.sqrt(r ** 2 + x ** 2) / z_base * 100, 0.001
    )

    pp.create_transformers_from_parameters(
        net,
        hv_buses=trafos["bus1_id"].map(bus_lookup).astype(int).values,
        lv_buses=trafos["bus2_id"].map(bus_lookup).astype(int).values,
        sn_mva=sn,
        vn_hv_kv=vn_hv / rho,
        vn_lv_kv=vn_lv,
        vkr_percent=np.maximum(r / z_base * 100, 0.0),
        vk_percent=vk_percent,
        pfe_kw=np.maximum(g * vn_lv ** 2 * 1000, 0.0),
        i0_percent=np.maximum(np.sqrt(g ** 2 + b ** 2) * z_base * 100, 0.0),
        shift_degree=shift_degree,
        name=trafos.index.tolist(),
        in_service=True,
        max_loading_percent=max_loading,
    )

    # ---- generators (bulk) ----
    generators = psn.get_generators(all_attributes=True)
    generators = generators[generators["bus_id"].isin(bus_lookup.index)]
    # Generators of foreign synchronous components (e.g. UK, only linked through HVDC) are not modelled
    generators = generators[generators["bus_id"].map(synchronous_component_by_bus) == main_synchronous_component]
    generator_in_service = (
        generators["connected"] if "connected" in generators else pd.Series(True, index=generators.index)
    )

    nans = np.isnan(generators["p"])
    # nan generators are disconnected one way or another, correct pandapower value is 0
    generators.loc[nans, "p"] = 0
    generators.loc[generators["q"].isna(), "q"] = 0

    # Generators that do not regulate voltage are PQ injections, not PV nodes. Modelling them as PV
    # pins their bus at a made-up voltage (1.0 pu) and floods the grid with reactive power: on the big
    # network it triples the active losses (~2600 MW -> ~7600 MW) and Newton-Raphson diverges.
    # Like batteries they become sgens (not controllable: the redispatch OPF only moves PV generators).
    is_voltage_regulating = generators["voltage_regulator_on"].astype(bool)
    pq_generators = generators[~is_voltage_regulating]
    generators = generators[is_voltage_regulating]
    if len(pq_generators):
        pp.create_sgens(
            net,
            buses=pq_generators["bus_id"].map(bus_lookup).astype(int).values,
            p_mw=-pq_generators["p"].values,
            q_mvar=-pq_generators["q"].values,
            name=pq_generators.index.tolist(),
            min_p_mw=pq_generators["min_p"].values,
            max_p_mw=pq_generators["max_p"].values,
            in_service=generator_in_service.loc[pq_generators.index].values,
            type=pq_generators["energy_source"].str.lower().values,
            controllable=False,
        )

    # pandapower cannot regulate a remote bus, so a generator that regulates another bus (possibly at
    # another voltage level) holds the voltage of its own bus instead. Dividing its target_v by its own
    # nominal voltage would give absurd setpoints (405 kV target on a 10 kV bus = 39 pu).
    gen_vn_kv = generators["voltage_level_id"].map(vlevels["nominal_v"])
    is_remote_regulation = generators["regulated_bus_id"].notna() & (
        generators["regulated_bus_id"] != generators["bus_id"]
    )
    own_bus_vm_pu = generators["bus_id"].map(buses["v_mag"]) / gen_vn_kv
    # Co-located generators must share one setpoint (see below); a remote regulator's own-bus voltage is
    # only used when the stored state has one, otherwise it falls back to the 1.0 pu default.
    gen_raw_vm_pu = (generators["target_v"] / gen_vn_kv).where(generators["target_v"] > 0)
    gen_raw_vm_pu = gen_raw_vm_pu.where(~is_remote_regulation, own_bus_vm_pu)
    gen_vm_pu = gen_raw_vm_pu.groupby(generators["bus_id"]).transform("first").fillna(1.0).values

    if governor_kgover is None:
        print("WARNING: governor_kgover not specified. FCR model will use p max instead")

    pp.create_gens(
        net,
        buses=generators["bus_id"].map(bus_lookup).astype(int).values,
        p_mw=-generators["p"].values,
        vm_pu=gen_vm_pu,
        name=generators.index.tolist(),
        min_p_mw=generators["min_p"].values,
        max_p_mw=generators["max_p"].values,
        min_q_mvar=generators["min_q"].values,
        max_q_mvar=generators["max_q"].values,
        slack=False,
        slack_weight=(generators["max_p"] + generators["p"]).clip(lower=0).fillna(0).values,
        type=generators["energy_source"].str.lower().values,
        in_service=generator_in_service.loc[generators.index].values,
        governor_kgover=(0 if governor_kgover is None
                         else governor_kgover.reindex(generators.index).values),
        #controllable=np.logical_not(generators["energy_source"].str.lower().isin(["solar", "wind"]).values),
    )

    # ---- loads (bulk) ----
    loads = psn.get_loads()
    loads = loads[loads["bus_id"].isin(bus_lookup.index)]
    nans = np.isnan(loads["p"])
    # nan loads are disconnected one way or another, correct pandapower value is 0
    loads.loc[nans, "p"] = 0
    loads.loc[nans, "q"] = 0
    # Remove loads of foreign synchronous components (e.g. UK, only linked through HVDC) to avoid having two
    # separate synchronous components in the pandapower model
    loads = loads[loads["bus_id"].map(synchronous_component_by_bus) == main_synchronous_component]
    load_in_service = (
        loads["connected"].values if "connected" in loads else True
    )
    pp.create_loads(
        net,
        buses=loads["bus_id"].map(bus_lookup).astype(int).values,
        p_mw=loads["p"].values,
        q_mvar=loads["q"].values,
        name=loads.index.tolist(),
        in_service=load_in_service,
        controllable=False
    )

    # ---- batteries (bulk) ----
    # IIDM batteries carry no voltage setpoint, so they are plain PQ injections (sgen),
    # not PV nodes. Small individually (<=3 MW here) but they were the largest remaining
    # source of DC flow error once the transformer reactance sign was fixed.
    batteries = psn.get_batteries()
    batteries = batteries[batteries["bus_id"].isin(bus_lookup.index)]
    if len(batteries):
        bat_nans = np.isnan(batteries["p"])
        batteries.loc[bat_nans, "p"] = 0
        batteries.loc[bat_nans, "q"] = 0
        pp.create_sgens(
            net,
            buses=batteries["bus_id"].map(bus_lookup).astype(int).values,
            p_mw=-batteries["p"].values,
            q_mvar=-batteries["q"].values,
            name=batteries.index.tolist(),
            min_p_mw=batteries["min_p"].values,
            max_p_mw=batteries["max_p"].values,
            min_q_mvar=batteries["min_q"].values,
            max_q_mvar=batteries["max_q"].values,
            in_service=(
                batteries["connected"].values if "connected" in batteries else True
            ),
            controllable=False,
        )

    # ---- shunt compensators (bulk) ----
    shunts = psn.get_shunt_compensators(all_attributes=True)
    shunts = shunts[shunts["bus_id"].isin(bus_lookup.index)]
    vn_shunt = shunts["voltage_level_id"].map(vlevels["nominal_v"]).values
    shunt_in_service = (
        shunts["connected"].values if "connected" in shunts else True
    )
    pp.create_shunts(
        net,
        buses=shunts["bus_id"].map(bus_lookup).astype(int).values,
        p_mw=shunts["g"].fillna(0.0).values * vn_shunt ** 2,
        q_mvar=-shunts["b"].fillna(0.0).values * vn_shunt ** 2,
        vn_kv=vn_shunt,
        name=shunts.index.tolist(),
        in_service=shunt_in_service,
    )

    # ---- HVDC lines ----
    hvdc = psn.get_hvdc_lines()
    if len(hvdc):
        conv = pd.concat([
            psn.get_vsc_converter_stations()[["bus_id", "loss_factor", "connected", "target_v", "voltage_level_id", "p"]],
            psn.get_lcc_converter_stations()[["bus_id", "loss_factor", "connected", "voltage_level_id", "p"]],
        ])
        conv = conv[conv["bus_id"].isin(bus_lookup.index)]
        hvdc = hvdc[
            hvdc["converter_station1_id"].isin(conv.index) &
            hvdc["converter_station2_id"].isin(conv.index)
        ]
        hvdc = hvdc.join(psn.get_vsc_converter_stations(), on="converter_station2_id", rsuffix="az")
        for hid, row in hvdc.iterrows():
            st1 = conv.loc[row["converter_station1_id"]]
            st2 = conv.loc[row["converter_station2_id"]]
            if row["converters_mode"] == "SIDE_1_RECTIFIER_SIDE_2_INVERTER":
                from_st, to_st = st1, st2
            else:
                from_st, to_st = st2, st1
            from_synchronous_component = synchronous_component_by_bus[from_st["bus_id"]]
            to_synchronous_component = synchronous_component_by_bus[to_st["bus_id"]]
            if from_synchronous_component != to_synchronous_component:
                # HVDC line towards a foreign synchronous component (e.g. UK) which is not modelled: represent the
                # line by an injection at its main-grid end equal to the opposite of the power drawn there
                main_grid_station = from_st if from_synchronous_component == main_synchronous_component else to_st
                vm_pu = main_grid_station["target_v"] / vlevels.loc[main_grid_station["voltage_level_id"], "nominal_v"]
                pp.create_gen(net, int(bus_lookup[main_grid_station["bus_id"]]), -main_grid_station["p"], vm_pu=vm_pu, name=hid,
                              min_p_mw=-row["max_p"], max_p_mw=row["max_p"], slack=False, type="hvdc",
                              in_service=bool(row["connected1"] and row["connected2"] and st1["connected"] and st2["connected"]))
            else:
                pp.create_dcline(
                    net,
                    from_bus=int(bus_lookup[from_st["bus_id"]]),
                    to_bus=int(bus_lookup[to_st["bus_id"]]),
                    p_mw=row["p"],
                    loss_percent=st1["loss_factor"] + st2["loss_factor"],
                    loss_mw=0.0,
                    vm_from_pu=from_st["target_v"] / vlevels.loc[from_st["voltage_level_id"], "nominal_v"],
                    vm_to_pu=to_st["target_v"] / vlevels.loc[to_st["voltage_level_id"], "nominal_v"],
                    name=hid,
                    in_service=bool(row["connected1"] and row["connected2"]
                                    and st1["connected"] and st2["connected"]),
                    max_p_mw=row["max_p"]
                )

    return net


def _drop_isolated_buses(pp_net):
    import pandapower.topology as pptop
    import networkx as nx
    slack_bus = int(pp_net.gen.loc[pp_net.gen["slack"], "bus"].iloc[0])
    mg = pptop.create_nxgraph(pp_net, respect_switches=False)
    if slack_bus not in mg:
        return
    reachable = nx.node_connected_component(mg, slack_bus)
    isolated = set(pp_net.bus.index) - reachable
    if isolated:
        pp.drop_buses(pp_net, list(isolated))

def dcpf(pp_net):
    # # DCOPF ignores losses. So as an ACPF was run by grid2op and we want to compare the result of the DCOPF with
    # # the init solution, we share the losses among loads to ensure energy balance and run a DCOPF 
    # losses = pp_net.gen["p_mw"].sum() - pp_net.load["p_mw"].sum()
    # #pp_net.load["p_mw"] += losses / len(pp_net.load["p_mw"])
    # pp_net.load["p_mw"] += losses * pp_net.load["p_mw"] / pp_net.load["p_mw"].sum()
    pp.rundcpp(pp_net)
    # pp_net.gen["p_mw"] = copy.deepcopy(pp_net.res_gen["p_mw"])
    return pp_net

def _select_slack_with_largest_margin(pp_net):
    """Flag as slack the in-service generator with the largest two-sided margin.

    The margin of a generator is min(p - min_p, max_p - p): the distance from its
    set point to the closest of its two P bounds, so the chosen slack can absorb
    imbalances in both directions. HVDC equivalent generators are excluded.
    Returns the pandapower index of the chosen generator.
    """
    gens = pp_net.gen
    candidate_mask = gens["in_service"].astype(bool) & (gens["type"] != "hvdc")
    if not candidate_mask.any():
        candidate_mask = gens["in_service"].notna()  # fall back to every generator

    candidates = gens[candidate_mask]
    margin_to_min_p = candidates["p_mw"] - candidates["min_p_mw"]
    margin_to_max_p = candidates["max_p_mw"] - candidates["p_mw"]
    two_sided_margin = pd.concat([margin_to_min_p, margin_to_max_p], axis=1).min(axis=1)

    slack_gen_index = two_sided_margin.idxmax()
    gens["slack"] = False
    gens.loc[slack_gen_index, "slack"] = True
    print(f"Slack generator: {gens.at[slack_gen_index, 'name']} "
          f"(margin {two_sided_margin[slack_gen_index]:.1f} MW)")
    return slack_gen_index


def powsybl2pandapower(network, governor_kgover):
    pp_net = _pypowsybl_to_pandapower(network, governor_kgover)
    _select_slack_with_largest_margin(pp_net)
    # _drop_isolated_buses(pp_net)
    pp_net = dcpf(pp_net)
    _setup_redispatch_cost(pp_net)
    return pp_net


def _setup_redispatch_cost(pp_net, init_gen=None):
    """Build the piecewise-linear redispatch cost once per pp_net.

    Every generator's cost only depends on its type, current (post-dcpf)
    dispatch and P bounds - none of which change across contingencies - so
    this must be called once (from powsybl2pandapower, right after dcpf)
    rather than inside pp_opf() on every one of the ~100+ per-contingency
    calls, where it was previously rebuilt (including a 5630-generator
    Python list comprehension) on every single call for no reason.
    """
    if init_gen is None:
        init_gen = pp_net.gen["p_mw"]

    # Quadratic redispatch cost: cost*(P - P0)^2, minimum at current dispatch P0.
    # Quadratic cp2*P^2 + cp1*P has its minimum at P = -cp1/(2*cp2) = P0 when cp1 = -2*cp2*P0.
    pp_net.poly_cost.drop(pp_net.poly_cost.index, inplace=True)

    _COST_BY_TYPE = {
        "hydro": 10.0, "wind": 20.0, "solar": 20.0,
        "nuclear": 30.0, "thermal": 40.0, "naturalgas": 40.0, "biomass": 40.0,
    }
    base_cp2 = pp_net.gen["type"].map(_COST_BY_TYPE).fillna(50.0)

    # Small per-generator tiebreaker so cost is unique within each type, ranked by
    # margin left (biggest margin first) rather than order of appearance, so the OPF
    # prefers generators with more room to redispatch. Margin is direction-dependent:
    # negative redispatch (moving toward min_p) ranks by left_margin, positive
    # redispatch (moving toward max_p) ranks by right_margin. Each segment of the pwl
    # cost gets its own tiebreaker so the two directions are prioritized independently.
    def _margin_rank(margin):
        return margin.groupby(pp_net.gen["type"]).rank(method="first", ascending=False) - 1

    left_margin = pp_net.gen["p_mw"] - pp_net.gen["min_p_mw"]
    right_margin = pp_net.gen["max_p_mw"] - pp_net.gen["p_mw"]
    cp2_neg = (base_cp2 + _margin_rank(left_margin) * 1e-3).values
    cp2_pos = (base_cp2 + _margin_rank(right_margin) * 1e-3).values
    # Breakpoints must stay within each generator's real [min_p, max_p] range: a
    # big-M bound (e.g. 1e9) makes the epigraph "y" variable's implicit range
    # astronomically large, badly conditioning PIPS's barrier method across
    # thousands of generators (observed as a step norm ~1e12 before diverging).
    # Falling back to p0 +/- 0.1 also covers generators with min_p > p0 or
    # max_p < p0 (e.g. negative-dispatch pumped storage), which otherwise
    # produced an inverted [lower, p0] segment.
    init_p = init_gen.values
    pmin = pp_net.gen["min_p_mw"].values
    pmax = pp_net.gen["max_p_mw"].values
    points = [
        [[float(min(pm, p0 - 0.1)), float(p0), float(-c_neg)],
         [float(p0), float(max(pM, p0 + 0.1)), float(c_pos)]]
        for p0, c_neg, c_pos, pm, pM in zip(init_p, cp2_neg, cp2_pos, pmin, pmax)
    ]
    pp_net.pwl_cost = pd.DataFrame({
        "element": pp_net.gen.index.tolist(),
        "et": "gen",
        "points": points,
        "power_type": "p",
    })
        # From the doc: https://pandapower.readthedocs.io/en/v2.2.0/opf/formulation.html#cost-functions
        # Piecewise cost for reactive power is not working (from two segments)
        # gen_init_q = ps_generators.loc[generator, "target_q"]
        # pp.create_pwl_cost(pp_net, gen_pp_idx, "gen", [[0, gen_init_q, -1], [gen_init_q, 1e9, 1]], "q")

class WaterFilling:
    """Share an amount proportionally to `weights`, each element being capped by its `headroom`.

    Element i gets min(weights[i] * level, headroom[i]); the common `level` is the one for which
    the shares add up to the amount. Elements are sorted by the level at which they saturate, so
    the response to any amount is found with a binary search (and is piecewise linear in it).
    If every weighted element is saturated, the rest of the amount is unallocated.

    order: positions of the weighted elements (weights > 0), by increasing saturation level.
    breaks[k]: amount at which order[k] saturates. cum_headroom[k] / reverse_cum_weight[k]: sum of the
    headroom of order[:k] / of the weights of order[k:].
    """

    def __init__(self, weights, headroom):
        weights = np.asarray(weights, float)
        self.weights = weights
        self.headroom = np.asarray(headroom, float)
        positions = np.flatnonzero(weights > 0)
        with np.errstate(divide="ignore", invalid="ignore"):
            levels = self.headroom[positions] / weights[positions]
        self.order = positions[np.argsort(levels, kind="stable")]
        sorted_weights, sorted_headroom = weights[self.order], self.headroom[self.order]
        self.cum_headroom = np.concatenate([[0.0], np.cumsum(sorted_headroom)])
        self.reverse_cum_weight = np.concatenate([np.cumsum(sorted_weights[::-1])[::-1], [0.0]])
        with np.errstate(invalid="ignore"):
            # cum headroom of previously saturated generators +
            # current headroom / current weight = how much power is needed to saturate current generator
            # current weight = weight / cum weight
            self.breaks = self.cum_headroom[:-1] + (sorted_headroom / sorted_weights) * self.reverse_cum_weight[:-1]

    def level(self, amount):
        """(n_saturated, level, unallocated): order[:n_saturated] get their headroom, the others weight * level."""
        n_saturated = int(np.searchsorted(self.breaks, amount, side="right"))
        if n_saturated == len(self.order):
            return n_saturated, np.inf, max(amount - self.cum_headroom[-1], 0.0)
        return n_saturated, (amount - self.cum_headroom[n_saturated]) / self.reverse_cum_weight[n_saturated], 0.0

    def shares(self, amount):
        """(shares, unallocated), shares being an array like `weights`."""
        n_saturated, remaining_to_share_scaled, unallocated = self.level(amount)
        shares = np.zeros(len(self.weights))
        saturated = self.order[:n_saturated]
        shares[saturated] = self.headroom[saturated]
        free = self.order[n_saturated:]
        shares[free] = self.weights[free] * remaining_to_share_scaled
        return shares, unallocated


def fcr_weights(pp_net, can_share):
    """FCR participation weights of net.gen (zero where `can_share` is False): governor_KGover,
    or the generators' max_p_mw when no governor data is available."""
    weights = pd.Series(0.0, index=pp_net.gen.index)
    if "governor_kgover" in pp_net.gen:
        weights = pp_net.gen["governor_kgover"].fillna(0).clip(lower=0).where(can_share, 0.0)
    if np.isclose(weights.sum(), 0):
        weights = pp_net.gen["max_p_mw"].fillna(0).clip(lower=0).where(can_share, 0.0)
    return weights


def fcr_headroom(gen, init_gen, direction):
    """Power each generator can still move in `direction` (+1 up to max_p_mw, -1 down to min_p_mw)."""
    limit = gen["max_p_mw"] if direction > 0 else gen["min_p_mw"]
    return (direction * (limit - init_gen)).fillna(np.inf).clip(lower=0)


def fcr(pp_net):
    """Dispatch after frequency containment: the system mismatch is shared proportionally to governor_KGover.

    rundcpp has no distributed-slack mode (pandapower only implements distributed slack for the
    AC Newton-Raphson solver), so the single slack=True generator absorbs the whole system
    mismatch. DC power flow ignores losses, so that mismatch is just one scalar, which is
    redistributed here. Generators never leave their [min_p, max_p]: the power a generator
    cannot take is re-shared among the others. Generators without governor_KGover (NaN) do not
    participate; without any governor data, max_p_mw is used instead.
    """
    pp.rundcpp(pp_net)
    slack_mask = pp_net.gen["slack"].values
    mismatch = (pp_net.res_gen.loc[slack_mask, "p_mw"] - pp_net.gen.loc[slack_mask, "p_mw"]).sum()
    # dispatch before the slack absorbed the mismatch
    init_gen = pp_net.res_gen["p_mw"].copy()
    init_gen[slack_mask] -= mismatch

    can_share = np.logical_and(pp_net.gen["in_service"], np.logical_not(np.isclose(pp_net.res_gen["p_mw"], 0)))
    weights = fcr_weights(pp_net, can_share)
    # mismatch > 0: generation must increase (up to max_p); otherwise decrease (down to min_p)
    direction = 1.0 if mismatch >= 0 else -1.0
    headroom = fcr_headroom(pp_net.gen, init_gen, direction)

    shares, unallocated = WaterFilling(weights.values, headroom.values).shares(abs(mismatch))
    init_gen += direction * shares
    # if every participating generator is saturated, the slack generator keeps what is left
    init_gen[slack_mask] += direction * unallocated
    return init_gen

def pp_opf(pp_net, set_cost=False, pre_check=False, available_time=None):
    """available_time: minutes before the contingency's first overload, during which generators can
    ramp up their max_p_mw. None (or negative) means unknown: no ramp."""

    # pp_net.line["max_loading_percent"] = 100.
    # pp_net.trafo["max_loading_percent"] = 100.
    # pp_net.bus["min_vm_pu"] = 0.9
    # pp_net.bus["max_vm_pu"] = 1.1

    # pp_net.gen["max_q_mvar"] *= 10
    # pp_net.gen["min_q_mvar"] *= 10
    # pp_net.gen["max_p_mw"] *= 10
    # pp_net.gen["min_p_mw"] *= 10

    # l2rpn_wcci_2020 stores the network with sn_mva=1 (MW as native unit) instead of
    # the MATPOWER convention of 100 MVA. The PIPS interior-point solver uses baseMVA
    # for scaling its KKT conditions, so sn_mva=1 makes generator outputs ~400 pu instead
    # of ~4 pu, causing the Hessian/Jacobian to be ~10000x more ill-conditioned.
    #pp_net.sn_mva = 100.
    init_gen = fcr(pp_net)
    if pre_check:
        # pre-check whether opf is necessary
        previous_gen = copy.deepcopy(pp_net.gen["p_mw"])
        pp_net.gen["p_mw"] = init_gen
        pp.rundcpp(pp_net)
        pp_net.gen["p_mw"] = previous_gen
        if not np.any(np.logical_and(pp_net.trafo["max_loading_percent"] > 0, pp_net.res_trafo["loading_percent"] > pp_net.trafo["max_loading_percent"])) \
            and not np.any(pp_net.res_gen["p_mw"] < pp_net.gen["min_p_mw"]) \
            and not np.any(pp_net.res_gen["p_mw"] > pp_net.gen["max_p_mw"]) \
            and not np.any(pp_net.res_sgen["p_mw"] < pp_net.sgen["min_p_mw"]) \
            and not np.any(pp_net.res_sgen["p_mw"] > pp_net.sgen["max_p_mw"]) \
            and not np.any(pp_net.res_line["loading_percent"] > pp_net.line["max_loading_percent"]):
            return True, 0, 0, []
    try:
        if True or set_cost:
            _setup_redispatch_cost(pp_net, init_gen)
        # We cannot define max load percent on transfos because we don't have max power on transfos (Nordic)
        #pp_net.trafo["max_loading_percent"] = 200.
        _RAMP_BY_TYPE = {
            "hydro": 0.5,
            "nuclear": 0.03, "thermal": 0.08, "naturalgas": 0.08, "biomass": 0.03,
        }
        p_max = copy.deepcopy(pp_net.gen["max_p_mw"])
        p_min = copy.deepcopy(pp_net.gen["min_p_mw"])

        # Unknown (None) or negative available time: no ramp, generators keep their max_p_mw
        if available_time is not None and available_time >= 0:
            ramp_per_min = pp_net.gen["type"].map(_RAMP_BY_TYPE)
            pp_net.gen["max_p_mw"] = np.fmin(p_max, init_gen + p_max * ramp_per_min * available_time / 60)
            pp_net.gen["min_p_mw"] = np.fmax(p_min, init_gen - p_max * ramp_per_min * available_time / 60)

        renewables = pp_net.gen["type"].isin(["solar", "wind"])
        pp_net.gen.loc[renewables, "max_p_mw"] = init_gen[renewables]
        
        pp.rundcopp(pp_net, verbose=False)#, init="pf")
        # pp_net.gen["p_mw"] = pp_net.res_gen["p_mw"]
        # TODO Change objective for AC refinment ?
        # pp_net.poly_cost.drop(pp_net.poly_cost.index, inplace=True)
        # pp_net.pwl_cost.drop(pp_net.pwl_cost.index, inplace=True)
        # for gen_pp_idx in pp_net.gen.index:
        #     gen_init_p = pp_net.gen.loc[gen_pp_idx, "p_mw"]
        #     if pp_net.gen.loc[gen_pp_idx, "type"] == "hydro":
        #         cp2 = 10
        #     elif pp_net.gen.loc[gen_pp_idx, "type"] in ["wind", "solar"]:
        #         cp2 = 20
        #     elif pp_net.gen.loc[gen_pp_idx, "type"] == "nuclear":
        #         cp2 = 30
        #     elif pp_net.gen.loc[gen_pp_idx, "type"] in ["thermal", "naturalgas", "biomass"]:
        #         cp2 = 40
        #     else:
        #         cp2 = 50
        #     pp.create_poly_cost(pp_net, gen_pp_idx, "gen", cp2_eur_per_mw2=cp2, cp1_eur_per_mw=-2 * cp2 * gen_init_p)
            
        #pp.runopp(pp_net, verbose=True, calculate_voltage_angles=False)#, init="pf"
        p_redispatch = pp_net.res_gen["p_mw"] - init_gen
        #q_redispatch = ps_generators["target_q"].reset_index(drop=True) - pp_net.res_gen["q_mvar"]

        # difficulty = np.sum(pp_net.res_line["i_ka"] * pp_net.line["max_loading_percent"] / 100 >= pp_net.line["max_i_ka"])
        difficulty = np.sum(np.abs(p_redispatch) > 1) #+ np.sum(np.abs(q_redispatch) > 100)
        pwl_points = pp_net.pwl_cost.set_index("element")["points"].reindex(p_redispatch.index)
        neg_slope = pwl_points.apply(lambda pts: pts[0][2])
        pos_slope = pwl_points.apply(lambda pts: pts[1][2])
        cost = np.sum(np.where(p_redispatch < 0, p_redispatch * neg_slope, p_redispatch * pos_slope))
        converged = True
    except pp.auxiliary.OPFNotConverged as e:
        converged = False
        difficulty = -1
        cost = -1
        p_redispatch = pd.Series()
        # To debug this, put verbose = True, search for bus with high Lambda P
        # Index needs to be converted from ppc to pandapower:
        pp_index = np.where(pp_net._pd2ppc_lookups["bus"] == 2465)[0][0]
        pp_net.res_line[pp_net.line["to_bus"] == pp_index]
        pp_net.load[pp_net.load["bus"] == pp_index]
        pp_net.res_trafo[pp_net.trafo["lv_bus"] == pp_index]
        pp_net.bus.loc[pp_index]
    finally:
        pp_net.gen.loc[p_max.index, "max_p_mw"] = p_max
        pp_net.gen.loc[p_min.index, "min_p_mw"] = p_min
    
    return converged, difficulty, cost, p_redispatch



