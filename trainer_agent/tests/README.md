# pypowsybl → pandapower conversion tests

Reference tests for `opf._pypowsybl_to_pandapower`, which converts a pypowsybl
(IIDM) network to pandapower without going through a CGMES/MATPOWER round-trip.
They validate the converted network by comparing its load flow against
pypowsybl's own solution on the same network.

## Running

```bash
pytest trainer_agent/tests/ -v                       # ~5 s
python trainer_agent/tests/powerflow_reference.py    # ad-hoc report on Nordic
python trainer_agent/tests/powerflow_reference.py --iidm path/to/network.iidm
```

The Nordic network is tracked in `docs/orchestrator/examples/Nordic/Nordic.iidm`;
tests **skip** (not fail) when the file is absent.

## How the comparison works

Per-line active power: pandapower's `res_line.p_from_mw` against pypowsybl's
`get_lines()["p1"]`, matched by element name. Same sign convention on both
sides, so they compare directly.

**The pre-balancing step is essential and is why the DC assertions can be
tight.** DC load flow ignores resistive losses, so a network whose generation
exceeds its load by the real transmission losses (~450 MW on Nordic) carries a
phantom surplus in DC. All of it lands on whichever bus is the reference, and
pandapower and pypowsybl choose different ones — comparing raw DC output shows
100+ MW differences that say nothing about whether the conversion is correct.

`prebalance_dc()` replicates `ContingencyFinder.update_network`: pin generator
`target_p` / load `p0` to the solved state, then re-solve DC with
`balance_type=PROPORTIONAL_TO_LOAD` so the mismatch is absorbed by loads.
Generation then equals load to ~1e-9 MW and the comparison becomes
reference-bus-insensitive.

The AC comparison needs no pre-balancing: the stored AC state is already
self-consistent, so the slack absorbs only a near-zero residual.

## Accuracy at the time of writing

| network | flow | max abs | mean abs |
|---|---|---|---|
| Nordic | DC | 3.4e-12 MW | ~0 |
| Nordic | AC | 8.7e-03 MW | 2.3e-03 MW |

Test tolerances sit above these with headroom, so numerical drift will not fail
the suite but a regression would.

## Regressions covered

Each has a `test_regression_*` test.

| Bug | Symptom |
|---|---|
| `rtc["tap_position"]` renamed to `tap` in pypowsybl, lookup wrapped in a bare `except Exception: pass` | Silent: **all** tap changers ignored, rho stuck at 1.0 network-wide |
| Tap ratio folded into `vn_lv_kv` | pandapower reuses `vn_lv_kv` as the impedance base, so every tapped transformer's reactance was rescaled by rho² (~15%) |
| Generator `vm_pu` hardcoded to 1.0 | Newton-Raphson did not converge at all |

Nordic has no phase shifters, batteries, HVDC or negative-reactance transformers,
so further regressions on those elements are covered by larger private networks.

# pypowsybl → ANDES conversion tests

`test_pypowsybl_to_andes.py` validates `pypowsybl_to_andes.pypowsybl_to_andes` (direct conversion to an ANDES
system) against pypowsybl's own AC load flow on Nordic. It reuses the comparison functions of
`trainer_agent/check_pypowsybl_to_andes.py`, which can also be run standalone for a printed report on any network:

```bash
pytest trainer_agent/tests/test_pypowsybl_to_andes.py -v                  # <1 s
python trainer_agent/check_pypowsybl_to_andes.py path/to/network.iidm [--no-reactive-limits]
```

Checks (main synchronous component, ANDES slack set to pypowsybl's reference bus):

| Check | Tolerance | Measured on Nordic |
|---|---|---|
| ANDES power flow converges | - | converged |
| Bus voltage magnitude | 1e-3 pu | 1e-5 pu |
| Bus angle (after removing the median offset between slacks) | 0.05 deg | 1.1e-3 deg |
| Line and transformer P / Q at side 1 | 0.5 MW / Mvar | 0.028 MW / 0.014 Mvar |
| Total losses | 1 MW | 0.0 MW difference |

Like the tests above, they skip when `Nordic.iidm` is absent.

The checks themselves live in `andes_conversion_checks.py` (not collected on its own). A test module per network
does `from andes_conversion_checks import *` and defines a module-scoped `network_path` fixture; it can also
override the `conversion_tolerances` fixture. `tests_private/test_mqis_andes_conversion.py` reuses them this way for
the MQIS network, with looser voltage and reactive-flow tolerances (the cause of the larger reactive gaps there is not
established; see the comment in that file).
