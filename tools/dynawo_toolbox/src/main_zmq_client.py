"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import argparse
import logging
from pathlib import Path

from action_sender import ActionSender
from handlers.dyd_handler import DydHandler
from handlers.par_handler import ParHandler
from logging_config import setup_logging

class Events:
    pass

def load_events(dyd_file, par_file):
    dyd_handler = DydHandler(dyd_file)
    par_handler = ParHandler(par_file)

    event_dict = dyd_handler.get_events()
    for e in event_dict.values():
        for k, v in par_handler.get_values(e.par_id).items():
            e.update_value(k, v)
    return event_dict

if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser()
    parser.add_argument("--dyd-event", "-d", help="Events dyd file")
    parser.add_argument("--par-event", "-p", help="Events par file")
    args = parser.parse_args()
    if args.dyd_event is not None and args.par_event is not None:
        dyd_file = Path(args.dyd_event).resolve()
        par_file = Path(args.par_event).resolve()
        if dyd_file.exists() and par_file.exists():
            events = load_events(dyd_file, par_file)

    sender = ActionSender()
