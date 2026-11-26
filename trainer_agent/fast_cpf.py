"""
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Faster corrector for ANDES' continuation power flow (CPF).

The stock corrector factorizes the augmented Jacobian [[J, dfg_dlam], [dP_dxy, dP_dlam]].
The dense border row/column makes the sparse LU about 5x slower than for J alone, the
matrix is rebuilt with a slow generic ``sparse([[...]])`` call, and the size change between
tangent solves (size nm) and corrector solves (size nm + 1) invalidates the cached symbolic
factorization at every iteration.

Here only the sparse J is factorized (symbolic factorization cached) and the border is
handled with a block elimination (two back-substitutions). Near the nose J becomes singular:
in that case we fall back to the stock augmented solve.
"""

import types

import numpy as np
from kvxopt import klu, matrix
from numpy.linalg import norm

from andes.shared import sparse

# |denominator| below this fraction of its natural scale -> J is considered too singular
SINGULARITY_RELATIVE_TOLERANCE = 1e-9


def _bordered_solve(cpf, jacobian, dfg_dlam, border_row, border_corner, rhs_top, rhs_bottom):
    """
    Solve [[J, dfg_dlam], [border_row, border_corner]] @ [dxy; dlam] = [rhs_top; rhs_bottom]
    factorizing only J. Returns ``None`` when J is (nearly) singular.
    """
    nm = jacobian.size[0]

    if getattr(cpf, "_klu_symbolic", None) is None:
        cpf._klu_symbolic = klu.symbolic(jacobian)

    try:
        try:
            numeric = klu.numeric(jacobian, cpf._klu_symbolic)
        except ValueError:  # sparsity pattern changed since the cached symbolic factorization
            cpf._klu_symbolic = klu.symbolic(jacobian)
            numeric = klu.numeric(jacobian, cpf._klu_symbolic)

        two_rhs = matrix(np.column_stack([rhs_top, dfg_dlam]), (nm, 2), "d")
        klu.solve(jacobian, cpf._klu_symbolic, numeric, two_rhs)
    except ArithmeticError:  # exactly singular
        return None

    solution = np.array(two_rhs)
    solve_rhs, solve_dfg_dlam = solution[:, 0], solution[:, 1]

    border_dot_solve_dfg = float(np.dot(border_row, solve_dfg_dlam))
    denominator = border_corner - border_dot_solve_dfg
    scale = abs(border_corner) + abs(border_dot_solve_dfg)
    if not np.isfinite(denominator) or abs(denominator) <= SINGULARITY_RELATIVE_TOLERANCE * max(scale, 1e-300):
        return None

    dlam = (rhs_bottom - float(np.dot(border_row, solve_rhs))) / denominator
    dxy = solve_rhs - solve_dfg_dlam * dlam
    if not (np.all(np.isfinite(dxy)) and np.isfinite(dlam)):
        return None

    return np.append(dxy, dlam)


def _fast_corrector(self, lam, xy_prev, lam_prev, step, z, dfg):
    """Same algorithm as ``CPF._corrector`` with the bordered solve instead of the augmented one."""
    system = self.system
    dae = system.dae
    n, m = dae.n, dae.m
    nm = n + m
    param = self._param

    self._set_loading(lam)

    for niter in range(self.config.max_iter):
        self._fg_update()

        mismatch = 0.0
        if n > 0:
            mismatch = max(mismatch, np.max(np.abs(dae.f)))
        if m > 0:
            mismatch = max(mismatch, np.max(np.abs(dae.g)))

        xy = np.concatenate([dae.x[:n], dae.y[:m]])
        parameterization_value = param.constraint(xy, lam, xy_prev, lam_prev, step, z, nm)
        mismatch = max(mismatch, abs(parameterization_value))

        if mismatch < self.config.tol:
            return True, niter + 1, lam

        if np.isnan(mismatch):
            return False, niter + 1, lam

        system.j_update(self._pflow_models())
        jacobian = sparse([[dae.fx, dae.gx], [dae.fy, dae.gy]]) if n > 0 else dae.gy

        border_row_sparse, border_corner = param.jacobian(xy, lam, xy_prev, lam_prev, z, nm)
        border_row = np.zeros(nm)
        border_row[list(border_row_sparse.J)] = list(border_row_sparse.V)

        rhs_top = np.concatenate([-dae.f[:n], -dae.g[:m]])
        rhs_bottom = -parameterization_value

        increment = _bordered_solve(
            self, jacobian, dfg, border_row, border_corner, rhs_top, rhs_bottom)

        if increment is None:  # near the nose: use the (slower but nose-proof) augmented system
            augmented = self._build_augmented(jacobian, dfg, border_row_sparse, border_corner)
            increment = self._solve_sparse(augmented, np.append(rhs_top, rhs_bottom))

        dae.x[:n] += increment[:n]
        dae.y[:m] += increment[n:nm]
        lam += increment[nm]
        self._set_loading(lam)
        system.vars_to_models()

    return False, self.config.max_iter, lam


def install_fast_cpf(system):
    """Replace the corrector of ``system.CPF`` by the faster bordered one (in place)."""
    system.CPF._klu_symbolic = None
    system.CPF._corrector = types.MethodType(_fast_corrector, system.CPF)
    return system
