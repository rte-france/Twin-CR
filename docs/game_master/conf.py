"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Sphinx configuration for the GameMaster documentation set.

Run ``sphinx-build`` from the repository root, e.g.:

    sphinx-build -b html docs/gamemaster docs/_build/gamemaster
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys
import os

# Ensure the GameMaster package is importable for autodoc / autosummary.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))


project = "GameMaster"
author = "RWTH Aachen University"
copyright = f"{datetime.now():%Y}, {author}"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

autosummary_generate = False
autodoc_member_order = "bysource"
napoleon_google_docstring = True
napoleon_numpy_docstring = False

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = os.getenv("SPHINX_HTML_THEME", "sphinx_rtd_theme")
html_static_path = ["_static"]
html_extra_path = ["assets"]
