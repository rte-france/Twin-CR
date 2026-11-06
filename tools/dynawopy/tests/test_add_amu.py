"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import pytest
from pathlib import Path

from dynawopy.updater import TestcaseUpdater
from dynawopy.config import Testcase

TESTCASE_DIR_IN = Path(__file__).parents[0] / "jobfiles" / "IEEE14_switch_out"


def test_add_amu(tmp_path):
    testcase = Testcase.from_directory(TESTCASE_DIR_IN)
    testcase_updater = TestcaseUpdater(testcase)
    testcase_updater.add_lovr(
        lovr_id="TEST",
        busbarSection_id="Bus12_1A",
        equipment_id="_BUS___12-BUS___13-1_AC",
    )
    testcase_updater.add_lovr(
        lovr_id="TEST2",
        busbarSection_id="Bus12_1A",
        equipment_id="_BUS____6-BUS___12-1_AC",
    )

    models = testcase.xp_dyd("//dyn:blackBoxModel[@lib='LackOfVoltageRelay']")
    assert {m.get("id") for m in models} == {"TEST", "TEST2"}

    connects_test = testcase.xp_dyd("//dyn:connect[@id1='TEST']")
    assert len(connects_test) == 5

    connects_test2 = testcase.xp_dyd("//dyn:connect[@id1='TEST2']")
    # 5 monitor connections + 1 sleepMode connection to TEST
    assert len(connects_test2) == 6

    testcase.save(directory=tmp_path)

    for ext in Testcase.exts:
        assert (tmp_path / f"IEEE14_switch.{ext}").exists()

    reloaded = Testcase.from_directory(tmp_path)
    reloaded_models = reloaded.xp_dyd("//dyn:blackBoxModel[@lib='LackOfVoltageRelay']")
    assert {m.get("id") for m in reloaded_models} == {"TEST", "TEST2"}

if __name__ == "__main__":
    pytest.main(["-s", __file__])
