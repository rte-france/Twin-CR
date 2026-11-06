"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import json
import pytest
from pathlib import Path

from dynawopy.updater import TestcaseUpdater
from dynawopy.config import Testcase

TESTCASE_DIR_IN = Path(__file__).parents[0] / "jobfiles" / "IEEE14_switch_out"

B6B12_SWITCH = "Bus12_lineB6B12_switch"
B12B13_SWITCH = "Bus12_lineB12B13_switch"
B6B12_LINE = "_BUS____6-BUS___12-1_AC"
B12B13_LINE = "_BUS___12-BUS___13-1_AC"

LOVR_CONFIGS = [
    {"libelle": "LOVR_B6B12", "bay": "B6B12"},
    {"libelle": "LOVR_B12B13", "bay": "B12B13"},
]


def load_testcase(name_breakers_by_bay=False):
    testcase = Testcase.from_directory(TESTCASE_DIR_IN)
    if name_breakers_by_bay:
        for switch_id, bay in ((B6B12_SWITCH, "B6B12"), (B12B13_SWITCH, "B12B13")):
            testcase.xp_iidm(f"//iidm:switch[@id='{switch_id}']")[0].set("name", f"{bay} DJ_OC")
    return testcase


def lovr_ids(testcase):
    return {
        model.get("id")
        for model in testcase.xp_dyd("//dyn:blackBoxModel[@lib='LackOfVoltageRelay']")
    }


def lovr_definition(testcase, lovr_id):
    model = testcase.xp_dyd(f"//dyn:blackBoxModel[@id='{lovr_id}']")[0]
    connects = testcase.xp_dyd(f"//dyn:connect[@id1='{lovr_id}']")
    return dict(model.attrib), sorted(
        (c.get("id1"), c.get("var1"), c.get("id2"), c.get("var2")) for c in connects
    )


def test_add_lovr_switch_only_matches_explicit_form():
    explicit = load_testcase()
    TestcaseUpdater(explicit).add_lovr(
        lovr_id="TEST",
        busbarSection_id="Bus12_1A",
        equipment_id=B6B12_LINE,
    )

    switch_only = load_testcase()
    TestcaseUpdater(switch_only).add_lovr(lovr_id="TEST", switch_id=B6B12_SWITCH)

    assert lovr_definition(switch_only, "TEST") == lovr_definition(explicit, "TEST")
    assert ("TEST", "lackOfVoltageRelay_UMonitoredBusPu", "NETWORK", "Bus12_1A_Upu_value") in (
        lovr_definition(switch_only, "TEST")[1]
    )


def test_add_lovrs_to_substation_adds_one_lovr_per_line_breaker():
    testcase = load_testcase()
    TestcaseUpdater(testcase).add_lovrs_to_substation("_BUS___12_SS")

    assert lovr_ids(testcase) == {
        "bus12_lineB6B12 DT.AMU",
        "bus12_lineB12B13 DT.AMU",
    }


def test_add_lovrs_to_substation_sets_retained_on_breakers():
    testcase = load_testcase()
    TestcaseUpdater(testcase).add_lovrs_to_substation("_BUS___12_SS", add_retained=True)

    for switch_id in (B6B12_SWITCH, B12B13_SWITCH):
        switch = testcase.xp_iidm(f"//iidm:switch[@id='{switch_id}']")[0]
        assert switch.get("retained") == "true"


def test_existing_lovr_lib_reuses_lovr_of_same_substation():
    testcase = load_testcase()
    TestcaseUpdater(testcase).add_lovr(
        lovr_id="TEST",
        busbarSection_id="Bus12_1A",
        equipment_id=B6B12_LINE,
    )

    TestcaseUpdater(testcase, existing_lovr_lib=True).add_lovr(
        lovr_id="TEST2",
        busbarSection_id="Bus12_1A",
        equipment_id=B12B13_LINE,
    )

    sleep_mode_connects = testcase.xp_dyd(
        "//dyn:connect[@id1='TEST2' and @var1='lackOfVoltageRelay_sleepMode']"
    )
    assert len(sleep_mode_connects) == 1
    assert sleep_mode_connects[0].get("id2") == "TEST"


@pytest.mark.parametrize("input_kind", ["list", "json", "jsonl"])
def test_add_lovr_from_list_accepts_all_input_formats(input_kind, tmp_path):
    testcase = load_testcase(name_breakers_by_bay=True)

    if input_kind == "list":
        source = LOVR_CONFIGS
    elif input_kind == "json":
        source = tmp_path / "lovrs.json"
        source.write_text(json.dumps(LOVR_CONFIGS), encoding="utf-8")
    else:
        source = tmp_path / "lovrs.jsonl"
        source.write_text(
            "\n".join(json.dumps(config) for config in LOVR_CONFIGS),
            encoding="utf-8",
        )

    added = TestcaseUpdater(testcase).add_lovr_from_list(source)

    assert added == ["LOVR_B6B12", "LOVR_B12B13"]
    assert lovr_ids(testcase) == {"LOVR_B6B12", "LOVR_B12B13"}


def test_unknown_equipment_id_raises_value_error():
    updater = TestcaseUpdater(load_testcase())

    with pytest.raises(ValueError):
        updater.add_lovr(
            lovr_id="TEST",
            busbarSection_id="Bus12_1A",
            equipment_id="UNKNOWN_LINE",
        )


def test_unknown_busbar_id_raises_value_error():
    updater = TestcaseUpdater(load_testcase())

    with pytest.raises(ValueError):
        updater.add_lovr(
            lovr_id="TEST",
            busbarSection_id="UNKNOWN_BUSBAR",
            equipment_id=B6B12_LINE,
        )


def test_unknown_switch_id_raises_value_error():
    updater = TestcaseUpdater(load_testcase())

    with pytest.raises(ValueError):
        updater.add_lovr(lovr_id="TEST", switch_id="UNKNOWN_SWITCH")


def test_missing_bay_raises_value_error():
    updater = TestcaseUpdater(load_testcase(name_breakers_by_bay=True))

    with pytest.raises(ValueError, match="bay"):
        updater.add_lovr_from_list([{"libelle": "LOVR_X"}])


def test_non_dict_entry_raises_type_error():
    updater = TestcaseUpdater(load_testcase(name_breakers_by_bay=True))

    with pytest.raises(TypeError):
        updater.add_lovr_from_list(["LOVR_X"])


def test_invalid_jsonl_line_reports_line_number(tmp_path):
    source = tmp_path / "lovrs.jsonl"
    source.write_text(
        '{"libelle": "LOVR_B6B12", "bay": "B6B12"}\n{"libelle": "LOVR_X"\n',
        encoding="utf-8",
    )
    updater = TestcaseUpdater(load_testcase(name_breakers_by_bay=True))

    with pytest.raises(ValueError, match="line 2"):
        updater.add_lovr_from_list(source)


def test_ambiguous_breaker_name_raises_value_error():
    testcase = load_testcase(name_breakers_by_bay=True)
    testcase.xp_iidm(f"//iidm:switch[@id='{B12B13_SWITCH}']")[0].set("name", "B6B12 DJ_OC")
    updater = TestcaseUpdater(testcase)

    with pytest.raises(ValueError, match="ambiguous"):
        updater.add_lovr_from_list([{"libelle": "LOVR_X", "bay": "B6B12"}])


if __name__ == "__main__":
    pytest.main(["-s", __file__])
