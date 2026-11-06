"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import logging

from handlers.xml_handler import XmlHandler
from utils import TL_XSD_PATH
from pathlib import Path

logger = logging.getLogger(__name__)

class TimelineHandler(XmlHandler):
    if Path(TL_XSD_PATH).is_file():
        XSD_FILE = TL_XSD_PATH
    else:
        logger.warning(f"{TL_XSD_PATH} does not exist, dynawo timeline file validation will not be performed")

    def absorb(self, other_tl_file):
        tl_handler = TimelineHandler(other_tl_file)
        events_sorted = sorted(list(self._tree.getroot().getchildren() + list(tl_handler._tree.getroot().getchildren())), key=lambda e: float(e.get('time')))
        self._tree.getroot().clear()
        for e in events_sorted:
            self._tree.getroot().append(e)
