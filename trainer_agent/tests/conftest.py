"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# `opf` and its siblings are plain modules in trainer_agent/, not a package.
sys.path.insert(0, str(REPO_ROOT / "trainer_agent"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import powerflow_reference as ref  # noqa: E402


def _network_fixture(path, label):
    """Load an IIDM network, skipping the test if the file is not available.

    The reference network may not be tracked in git, so a fresh checkout may not
    have it - skip rather than fail so the rest of the suite still runs.
    """
    if not path.exists():
        pytest.skip(f"{label} network not available at {path}")
    import pypowsybl as ps

    return ps.network.load(str(path))


@pytest.fixture
def nordic_network():
    """Fresh Nordic network, as stored on disk (solved AC state)."""
    return _network_fixture(ref.NORDIC_IIDM, "Nordic")


@pytest.fixture
def nordic_path():
    if not ref.NORDIC_IIDM.exists():
        pytest.skip(f"Nordic network not available at {ref.NORDIC_IIDM}")
    return ref.NORDIC_IIDM
