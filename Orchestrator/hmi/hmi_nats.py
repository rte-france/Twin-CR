"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import argparse
import datetime
from glob import glob
from pathlib import Path
import sys
import math
import json
import signal
from collections import defaultdict
from functools import partial
import os
import asyncio
import tempfile
import time
import clickhouse_connect
import requests
import toml
import nats.aio.msg
from enum import Enum, IntEnum
from nats.aio.client import Client as NATS
from nats.errors import NoRespondersError

from PySide6.QtWidgets import QWidget, QApplication, QLabel, QPushButton, \
    QGridLayout, QVBoxLayout, QSlider, QTextEdit, QLineEdit, QMessageBox, QHBoxLayout, QTabWidget
from PySide6.QtCore import Slot, QTimer, Qt
from PySide6.QtGui import QColor, QFont

from AsyncioPySide6 import AsyncioPySide6

import numpy as np
import matplotlib
import matplotlib.lines
import matplotlib.axes
import matplotlib.collections
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from game_master_starter import GameMasterClient

class Breaker(IntEnum):
    OPEN=1,
    CLOSE=2,
    CMD_OPEN=1,
    CMD_CLOSE=0

matplotlib.use('QTAgg')

# Time frame (x axis)
TIME_WIDTH = 200
FPS = 1

CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", "8123"))
CONFIGURATOR_HOST = os.getenv("CONFIGURATOR_HOST", "localhost")
CONFIGURATOR_PORT = int(os.getenv("CONFIGURATOR_PORT", "8080"))
DSL_SERVER_HOST = os.getenv("DSL_SERVER_HOST", "localhost")
DSL_SERVER_PORT = int(os.getenv("DSL_SERVER_PORT", "8000"))
GAME_MASTER_URL = f"http://{DSL_SERVER_HOST}:{DSL_SERVER_PORT}"
WITH_LEGACY_DSL = os.getenv("WITH_LEGACY_DSL", "false").lower() in ("1", "true", "yes")

def wait_configurator():
    while True:
        try:
            response = requests.get(f"http://{CONFIGURATOR_HOST}:{CONFIGURATOR_PORT}/status", headers={"accept": "application/json"})
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "NOT READY":
                break

            print("Configurator not ready, received", data)

        except requests.exceptions.ConnectionError:
            print("Configurator not reachable yet")
        except requests.exceptions.Timeout:
            print("Configurator request timed out")

        time.sleep(1)

def get_simulation_id_from_configurator():
    wait_configurator()
    response = requests.get(f"http://{CONFIGURATOR_HOST}:{CONFIGURATOR_PORT}/simulation_id", headers={"accept": "application/json"})
    response.raise_for_status()
    data = response.json()
    return data.get("simulation_id")

def get_config_path_from_configurator():
    wait_configurator()
    response = requests.get(f"http://{CONFIGURATOR_HOST}:{CONFIGURATOR_PORT}/config_path", headers={"accept": "application/json"})
    response.raise_for_status()
    data = response.json()
    return data.get("config_path")

def get_file_from_clickhouse(simulation_id, path):
    client = clickhouse_connect.get_client(
        host=CLICKHOUSE_HOST, port=CLICKHOUSE_PORT
    )
    query = (
        "SELECT content "
        f"FROM `{simulation_id}`.InputFiles "
        f"WHERE input_file = '{path}'"
    )

    result = client.query(query)
    rows = result.result_rows
    if not rows:
        raise RuntimeError(f"{path} not found in `{simulation_id}`.InputFiles")
    return rows[0][0]


def find_same_dir_file_with_ext(path: str, exts: list[str]) -> str:
    # Normalize extensions
    norm_exts = []
    for ext in exts:
        if not ext.startswith("."):
            ext = "." + ext
        norm_exts.append(ext)

    directory = os.path.dirname(os.path.abspath(path))

    matches = []
    for ext in norm_exts:
        pattern = os.path.join(directory, f"*{ext}")
        matches.extend(glob(pattern))

    if not matches:
        return ""

    return min(matches, key=len)


async def nats_request(nats_connection: NATS, subject: str, message: bytes, timeout=2.0):
    try:
        print("Sending", message, "to", subject)
        response = await nats_connection.request(subject, message, timeout)
        reply = json.loads(response.data.decode())
        if reply["status"] == "OK":
            print("Action implemented by orchestrator")
        else:
            print("Error:", reply)
    except asyncio.TimeoutError:
        print("timeout")
    except NoRespondersError:
        print("No subscribers to", subject)

def sanitize_nats_topic_name(topic: str) -> str:
    chars = list(topic)

    for i, c in enumerate(chars):
        if c in ('\0', ' ', '.'):  # Keep wildcards (*, >) as is
            chars[i] = '_'
        # else keep as is

    return ''.join(chars)

def get_tase2_extension(tase2_id: str, signalisation_type: str):
    return {
        "tase2_id": tase2_id,
        "signalisation_type": signalisation_type,
        "cause": 3,  # Spontaneous
        "validity": 0,  # Good
        "operatorBlocked": False
    }

class TabGraphData:
    def __init__(self, graph_inputs, name, fps, speedup, history_time):
        self.graph_inputs = graph_inputs
        self.name = name
        self.figure = Figure()
        self.graph_axes = None
        self.t_axis = None
        self.graph_lines = None
        self.scatter_plots = None
        self.scatter_data = None
        self.initialize(fps, speedup, history_time)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.draw()


    def initialize(self, fps, speedup, history_time):
        """
        Create graphs with a time axis from -history_time to 0, with 'fps' points per second, and zeroes on the y axis
        A separate graph (i.e. matplotlib.axes) is created for each key of self.graph_inputs, and contains curves representing
        all inputs listed in self.graph_inputs[graph_name]
        """
        self.graph_axes : dict[str, matplotlib.axes.Axes] = dict()
        for i, graph_name in enumerate(self.graph_inputs):
            subplot = len(self.graph_inputs) * 100 + 10 + (i+1)  # Stack all plots horizontally
            self.graph_axes[graph_name] = self.figure.add_subplot(subplot)
            self.graph_axes[graph_name].set_title(graph_name)
            self.graph_axes[graph_name].set_xlabel("Time (s)")
            self.graph_axes[graph_name].set_ylabel(graph_name)

        self.t_axis = np.linspace(-history_time, 0, int(fps / speedup * history_time) + 1)
        empty_axis = np.empty(self.t_axis.shape)
        empty_axis.fill(np.nan)
        self.graph_lines : dict[str, dict[str, matplotlib.lines.Line2D]] = dict()
        self.scatter_plots: dict[str, dict[str, matplotlib.collections.PathCollection]] = dict()
        self.scatter_data: dict[str, dict[str, list[list[float]]]] = dict()
        for graph_name, graph_input_list in self.graph_inputs.items():
            self.graph_lines[graph_name] = dict()
            self.scatter_plots[graph_name] = dict()
            self.scatter_data[graph_name] = dict()
            for graph_input in graph_input_list:
                line, = self.graph_axes[graph_name].plot(self.t_axis, empty_axis, label=graph_input)
                self.graph_lines[graph_name][graph_input] = line
                self.scatter_data[graph_name][graph_input] = [[], []]
                self.scatter_plots[graph_name][graph_input] = self.graph_axes[graph_name].scatter([], [], s=1)

        self.figure.tight_layout()

        for graph_name in self.graph_inputs:
            # Shrink plots by 20% and put legend there
            box = self.graph_axes[graph_name].get_position()
            self.graph_axes[graph_name].set_position([box.x0, box.y0, box.width * 0.8, box.height])
            self.graph_axes[graph_name].legend(loc='center left', bbox_to_anchor=(1, 0.5), fontsize='xx-small')

    def update(self, time, data: dict):
        """
        Remove the oldest value in graphs (at self.time - self.history_time), and replace it by the current value
        (at self.time). Note that this makes sure that the number of elements in matplotlib plots stays constant
        which is required for it to work.
        """
        self.t_axis = np.delete(self.t_axis, 0)  # Delete oldest time
        self.t_axis = np.append(self.t_axis, time)  # Add current time

        for graph_name, graph_input_list in self.graph_inputs.items():
            for graph_input in graph_input_list:
                y_data = self.graph_lines[graph_name][graph_input].get_ydata()
                y_data = np.delete(y_data, 0)
                y_data = np.append(y_data, data[graph_input])
                self.graph_lines[graph_name][graph_input].set_xdata(self.t_axis)
                self.graph_lines[graph_name][graph_input].set_ydata(y_data)
                self.scatter_plots[graph_name][graph_input].set_offsets(
                    np.column_stack(self.scatter_data[graph_name][graph_input])
                )

            # Reset axis ranges as matplotlib does not do it automatically
            self.graph_axes[graph_name].relim()
            self.graph_axes[graph_name].autoscale()

            y_min, y_max = self.graph_axes[graph_name].get_ybound()
            # Check if there are any finite data points in the plot
            lines = self.graph_axes[graph_name].get_lines()
            all_y = np.concatenate([line.get_ydata() for line in lines])
            finite_y = all_y[np.isfinite(all_y)]
            if finite_y.size > 0:
                # Don't allow matplotlib to zoom in too much
                y_min = math.floor((y_min) / 0.5) * 0.5 - 0.5  # Round down to 0.5 + margin
                y_max = math.ceil((y_max) / 0.5) * 0.5 + 0.5  # Round up to 0.5 + margin
                self.graph_axes[graph_name].set_ylim((y_min, y_max))
            # Sliding time window
            x_min = max(0, int(time)-TIME_WIDTH)
            x_max = max(TIME_WIDTH, time)
            self.graph_axes[graph_name].set_xlim((x_min, x_max))

        self.canvas.draw()
        self.canvas.flush_events()


class Mode(Enum):
    FILESYSTEM = 1  # Where the input files can be fetched from
    CLICKHOUSE = 2


class HMI(QWidget):
    """
    Very simple HMI for testing purposes
    """
    def __init__(self, config_path: str, application: str, start_time: float, mode: Mode):
        super(HMI, self).__init__()
        self.start_time = start_time

        if application not in ["hmi", "game_master"]:
            raise NotImplementedError("application should be hmi or game_master,", application, "given")
        self.application = application

        self.mode = mode
        if mode == Mode.FILESYSTEM:
            self.config_path = os.path.abspath(config_path)
            config = toml.load(open(self.config_path))
            self.simulation_id = None  # Will be provided by the orchestrator on initialisation

            self.default_iidm_path = find_same_dir_file_with_ext(config_path, ["iidm", "xiidm"])
            self.default_dsl_path = config["input_files"].get("dsl_file", "")
            if self.default_dsl_path:
                self.default_dsl_path = Path(self.config_path).parent / self.default_dsl_path

        else:  # Mode.CLICKHOUSE
            self.config_path = get_config_path_from_configurator()
            print(self.config_path)
            self.simulation_id = get_simulation_id_from_configurator()
            config_content = get_file_from_clickhouse(self.simulation_id, self.config_path)
            config = toml.loads(config_content)

            self.default_iidm_path = None  # Handled by the configurator
            self.default_dsl_path = None

        self.is_started = False
        self.speedup = 1# config["master"]["speedup"]

        self.time = 0
        self.fps = FPS
        self.history_time = TIME_WIDTH
        self.initial_timestamp = 0

        app_config = config.get(application, {})

        plot_data = app_config.get("plot_data", {})
        self.graphs: list[TabGraphData] = []
        if not plot_data:
            pass
        elif all(not isinstance(v, dict) for v in plot_data.values()):
            self.graphs.append(TabGraphData(plot_data, None, self.fps, self.speedup, self.history_time))
        else:
            for tab_name, tab_data in plot_data.items():
                if isinstance(tab_data, dict):
                    self.graphs.append(TabGraphData(tab_data, tab_name, self.fps, self.speedup, self.history_time))

        self.data = defaultdict(lambda: np.nan)

        self.game_master_client = GameMasterClient(GAME_MASTER_URL) if WITH_LEGACY_DSL else None
        self.game_master_artifact = "Nordic"
        self.pause_button = None
        self.is_paused = False

        self.state_button_ids = app_config.get("state_button_ids", [])
        self.bool_button_ids = app_config.get("bool_button_ids", [])
        self.simple_button_ids = app_config.get("simple_button_ids", [])
        self.slider_ids = [ obj['id'] for obj in app_config["sliders"] ] if app_config.get("sliders") is not None else []
        self.sliders = [ obj for obj in app_config["sliders"] ]  if app_config.get("sliders") is not None else []
        self.slider_labels = [ obj['label'] for obj in self.sliders ]
        self.slider_min = [ obj['min'] for obj in self.sliders ]
        self.slider_tmin = [ obj['tmin'] for obj in self.sliders ]
        self.slider_max = [ obj['max'] for obj in self.sliders ]
        self.slider_tmax = [ obj['tmax'] for obj in self.sliders ]
        self.slider_val = [ obj['val'] for obj in self.sliders ]
        self.slider_units = [ obj['unit'] for obj in self.sliders ]
        self.tase2_by_id = {}
        if application == "hmi":
            if self.mode == Mode.FILESYSTEM:
                scada_inputs = json.load(open(Path(self.config_path).parent / config["input_files"]["scada_inputs_file"]))
            else:
                scada_inputs = json.loads(get_file_from_clickhouse(self.simulation_id, config["input_files"]["scada_inputs_file"]))
            for scada_input in scada_inputs:
                if "tase2" in scada_input:
                    self.tase2_by_id[scada_input["id"]] = scada_input["tase2"]

        # Check that config is homogeneous
        keys = None
        for obj in self.sliders:
            if keys is None:
                keys = obj.keys()
            else:
                if obj.keys() != keys:
                    print(f'Non-homogeous config[{application}]["sliders"]: {app_config["sliders"]}')
                    sys.exit(1)

        self.init_ui(application)

        nats_url = os.getenv("NATS_URL", "nats://localhost:4222")
        self.nats_connection = NATS()
        # Use AsyncioPySide6.runTask to lauch async calls in Qt app
        print(f"Connecting to NATS server: {nats_url}")
        AsyncioPySide6.runTask(self.nats_connection.connect(nats_url))  # Same as await self.nats_connection.connect
        subscribed_substations = app_config.get("subscribed_substations", [])
        if application == "hmi":
            for substation in subscribed_substations:
                sanitized_substation_name = sanitize_nats_topic_name(substation)
                AsyncioPySide6.runTask(self.nats_connection.subscribe("HMI." + app_config["location"] + "." + sanitized_substation_name, cb=self.message_handler))
            self.pub_name = "HMIControl.Trainee"
        elif application == "game_master":
            for substation in subscribed_substations:
                sanitized_substation_name = sanitize_nats_topic_name(substation)
                AsyncioPySide6.runTask(self.nats_connection.subscribe("GameMaster." + sanitized_substation_name, cb=self.message_handler))
            self.pub_name = "GameMasterControl.Trainer"
        AsyncioPySide6.runTask(self.nats_connection.subscribe("time", cb=self.time_message_handler))

        AsyncioPySide6.runTask(self.nats_connection.subscribe("stop", cb=self.stop_message_handler))
        AsyncioPySide6.runTask(self.nats_connection.subscribe("Dynawo.Timeline", cb=self.json_message_handler))
        AsyncioPySide6.runTask(self.nats_connection.subscribe("Dynawo.Constraints", cb=self.json_message_handler))

    def init_ui(self, name):
        """
        Initializes the QT UI
        """
        if name == 'hmi':
            title = 'SCADA view'
        elif name == 'game_master':
            title = 'Game Master - State view'
        self.setWindowTitle(f"{title}")
        self.setFont(QFont('Ubuntu Regular'))
        self.setStyleSheet('background-color : #2a2a2a; color: white; font-size: 14px')
        layout = QVBoxLayout()

        if name == 'game_master':
            gm_layout = QHBoxLayout()
            text_layout = QVBoxLayout()
            buttons_layout = QVBoxLayout()
            gm_layout.addLayout(text_layout)
            gm_layout.addLayout(buttons_layout)

            # Add buttons to start simulation
            self.input_config_path = QLineEdit()
            self.input_config_path.setText(self.config_path)
            text_layout.addWidget(self.input_config_path)

            button = QPushButton("1. Init orchestrator")
            button.clicked.connect(self.init_button_pressed)
            buttons_layout.addWidget(button)

            disabled_color = "#A00000"
            if self.mode == Mode.CLICKHOUSE:
                self.input_config_path.setText("Initialisation handled by the configurator")
                self.input_config_path.setEnabled(False)
                self.input_config_path.setStyleSheet(f"background-color : {disabled_color}")
                button.setEnabled(False)
                button.setStyleSheet(f"background-color : {disabled_color}")

            if WITH_LEGACY_DSL:
                # Legacy DSL (Python gamemaster): IIDM/DSL must be uploaded and the simulation
                # explicitly initialized before any DSL command can be sent.
                self.input_iidm_path = QLineEdit()
                if self.default_iidm_path:
                    self.input_iidm_path.setText(str(self.default_iidm_path))
                text_layout.addWidget(self.input_iidm_path)

                button = QPushButton("2. Upload iidm to game master")
                button.clicked.connect(self.upload_iidm)
                buttons_layout.addWidget(button)

                if self.mode == Mode.CLICKHOUSE:
                    self.input_iidm_path.setText("Initialisation handled by the configurator")
                    self.input_iidm_path.setEnabled(False)
                    self.input_iidm_path.setStyleSheet(f"background-color : {disabled_color}")
                    button.setEnabled(False)
                    button.setStyleSheet(f"background-color : {disabled_color}")

                self.input_dsl_path = QLineEdit()
                self.input_dsl_path.setPlaceholderText("Default to empty file")
                if self.default_dsl_path:
                    self.input_dsl_path.setText(str(self.default_dsl_path))
                text_layout.addWidget(self.input_dsl_path)

                button = QPushButton("3. Upload DSL to game master and init game master")
                button.clicked.connect(self.upload_dsl_and_start)
                self.dsl_server_started = False
                buttons_layout.addWidget(button)

                if self.mode == Mode.CLICKHOUSE:
                    self.input_dsl_path.setText("Initialisation handled by the configurator")
                    self.input_dsl_path.setEnabled(False)
                    self.input_dsl_path.setStyleSheet(f"background-color : {disabled_color}")
                    button.setEnabled(False)
                    button.setStyleSheet(f"background-color : {disabled_color}")
                    self.dsl_server_started = True

            self.clock_text = QLineEdit()
            self.clock_text.setText("time: 0")
            self.clock_text.setEnabled(False)
            self.clock_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
            text_layout.addWidget(self.clock_text)

            self.start_pause_button = QPushButton("4. Start orchestrator" if WITH_LEGACY_DSL else "2. Start orchestrator")
            self.start_pause_button.clicked.connect(self.start_pause_button_pressed)
            buttons_layout.addWidget(self.start_pause_button)

            self.stop_text = QLineEdit()
            self.stop_text.setText("")
            self.stop_text.setEnabled(False)
            self.stop_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
            text_layout.addWidget(self.stop_text)

            self.stop_button = QPushButton("Stop")
            self.stop_button.clicked.connect(self.stop_button_pressed)
            buttons_layout.addWidget(self.stop_button)

            layout.addLayout(gm_layout)

        else:
            self.clock_text = QLineEdit()
            self.clock_text.setText("time: 0")
            self.clock_text.setEnabled(False)
            self.clock_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(self.clock_text)

        # Set graphs to refresh at target fps
        self.timer = QTimer()
        self.timer.setInterval(1000 / self.fps)
        self.timer.timeout.connect(self.refresh_hmi)
        self.timer.start()

        if not self.graphs:
            pass
        elif len(self.graphs) == 1 and self.graphs[0].name is None:
            layout.addWidget(self.graphs[0].canvas)
        else:
            tabs = QTabWidget()
            for graph in self.graphs:
                tabs.addTab(graph.canvas, graph.name)
            layout.addWidget(tabs)

        if name == 'game_master':
            dsl_layout = QHBoxLayout()
            self.input_dsl_command = QLineEdit()
            self.input_dsl_command.setPlaceholderText(f"DSL command to send")
            dsl_layout.addWidget(self.input_dsl_command)

            button = QPushButton("Send DSL command")
            button.clicked.connect(self.send_dsl_button_pressed)
            dsl_layout.addWidget(button)

            layout.addLayout(dsl_layout)

        # Add line buttons
        self.buttons: dict[str, QPushButton] = dict()
        for state_button_id in self.state_button_ids:
            button = QPushButton()
            button.clicked.connect(partial(self.state_button_pressed, state_button_id))
            if self.data[state_button_id] == 2:
                button.setText(f"Line {state_button_id} ON")
                button.setStyleSheet("background-color : green")
            else:
                button.setText(f"Line {state_button_id} OFF")
                button.setStyleSheet("background-color : red")
            self.buttons[state_button_id] = button
            layout.addWidget(button)

        # Add bool buttons
        for bool_button_id in self.bool_button_ids:
            # Initialise bool buttons to False if no value specified
            if bool_button_id not in self.data:
                self.data[bool_button_id] = -1

            button = QPushButton()
            button.clicked.connect(partial(self.bool_button_pressed, bool_button_id))
            if self.data[bool_button_id] > 0:
                button.setText(f"{bool_button_id} closed")
                button.setStyleSheet("background-color : green")
            else:
                button.setText(f"{bool_button_id} opened")
                button.setStyleSheet("background-color : red")
            self.buttons[bool_button_id] = button
            layout.addWidget(button)

        # Add simple buttons
        for simple_button_id in self.simple_button_ids:
            # Initialise simple buttons to 0 if no value specified
            if simple_button_id not in self.data:
                self.data[simple_button_id] = 0

            button = QPushButton()
            button.clicked.connect(partial(self.simple_button_pressed, simple_button_id))
            if self.data[simple_button_id] > 0:
                button.setText(f"{simple_button_id} TRUE")
                button.setStyleSheet("background-color : red")
            else:
                button.setText(f"{simple_button_id} FALSE")
                button.setStyleSheet("background-color : green")
            self.buttons[simple_button_id] = button
            layout.addWidget(button)

        # Add sliders
        self.sliders = {}
        self.label_unit = {}
        row = 0
        boxlay = QGridLayout()
        for slider_id, smin, smax, sval, slider_label, slider_unit in zip(self.slider_ids, self.slider_min, self.slider_max, self.slider_val, self.slider_labels, self.slider_units):
            lab = QLabel(slider_label)
            self.data[slider_id] = 0
            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(smin*100)
            slider.setMaximum(smax*100)
            slider.setTickInterval((smax-smin)*10)
            slider.setTickPosition(QSlider.TicksBelow)
            slider.setValue(sval*100)
            slider.sliderMoved.connect(partial(self.slider_update, slider_id))
            self.sliders[slider_id] = slider
            lunit = str(sval) + slider_unit
            labunit = QLabel(lunit)
            self.label_unit[slider_id] = labunit
            boxlay.addWidget(lab, row, 0)
            boxlay.addWidget(slider, row, 1)
            boxlay.addWidget(labunit, row, 2)
            row += 1
        layout.addLayout(boxlay)

        # Add Text zone
        # self.spacer = QSpacerItem(10, 20)
        # layout.addWidget(self.spacer)
        self.text = QTextEdit()
        self.text.ensureCursorVisible()
        self.text.setCursorWidth(0)
        self.text.setFixedHeight(142)
        self.text.setStyleSheet('background-color: gray75;')
        layout.addWidget(self.text)

        self.alarm = QTextEdit()
        self.text.setCursorWidth(0)
        self.alarm.ensureCursorVisible()
        self.alarm.setFixedHeight(142)
        layout.addWidget(self.alarm)

        self.setLayout(layout)

        self.red = QColor("red")
        self.orange = QColor("orange")
        self.green = QColor("green")

    @Slot()
    def init_button_pressed(self):
        config_path = self.input_config_path.text().strip()
        if config_path == "":  # Default to own config if not specified
            config_path = self.config_path.strip()
        message = {"config_path": config_path}

        async def run_request():
            try:
                reply_msg = await self.nats_connection.request("Start", json.dumps(message).encode(), timeout=30)
            except asyncio.TimeoutError:
                return {"status": "timedout"}
            except NoRespondersError:
                return {"status": "NoResponder (please launch the orchestrator_exec executable or wait for the docker to initialize)"}
            return json.loads(reply_msg.data.decode())
        # AsyncioPySide6.runTask(run_request())
        loop = asyncio.get_event_loop()
        reply = loop.run_until_complete(run_request())

        if reply is not None:
            self.simulation_id = reply.get("simulation_id")
            if reply.get("status") == "READY":
                if self.simulation_id is None:
                    self.simulation_id = "placeholder"
        if self.simulation_id is None:
            print("Warning: orchestrator initialization was not successful")
            QMessageBox.critical(self, "Error", "Orchestrator initialization was not successful\n" + json.dumps(reply, indent=4))
        else:
            QMessageBox.information(self, "Info", "Orchestrator successfully initialized\n" + json.dumps(reply, indent=4))

    @Slot()
    def upload_iidm(self):
        iidm_path = self.input_iidm_path.text().strip()
        if iidm_path == "":
            iidm_path = self.default_iidm_path
        reply = self.game_master_client.upload_iidm(Path(iidm_path), self.game_master_artifact)
        print("IIDM upload received the following reply\n", reply)
        QMessageBox.information(self, "Info", "IIDM upload reply:\n" + json.dumps(reply, indent=4))
        self.game_master_artifact = reply.get("artifact_id", self.game_master_artifact)  # Use the artifact_id from server if provided; otherwise keep the current one

    @Slot()
    def upload_dsl_and_start(self):
        if self.simulation_id is None:
            QMessageBox.critical(self, "Error", "Orchestrator must be initialized first")
            return

        dsl_path = self.input_dsl_path.text().strip()
        if dsl_path == "":
            # Create a temporary empty dsl file and send it
            with tempfile.NamedTemporaryFile(mode="w", suffix=".dsl", delete=True) as tmp:
                empty_dsl_path = tmp.name
                reply = self.game_master_client.init_simulation(Path(empty_dsl_path), self.simulation_id, self.game_master_artifact)
        else:
            reply = self.game_master_client.init_simulation(Path(dsl_path), self.simulation_id, self.game_master_artifact)
        print("DSL upload received the following reply\n", reply)
        self.dsl_server_started = True
        QMessageBox.information(self, "Info", "DSL upload reply:\n" + json.dumps(reply, indent=4))

    @Slot()
    def start_pause_button_pressed(self):
        if self.simulation_id is None:
            QMessageBox.critical(self, "Error", "Orchestrator must be initialized first")
            return
        pause_text = "PAUSE"
        pause_color = "#006A4E"
        if self.is_started is False:
            message = {
                "command": "start"
            }
            AsyncioPySide6.runTask(self.nats_connection.publish("Start", json.dumps(message).encode()))
            QMessageBox.information(self, "Info", "Orchestrator started")  # TODO: check for reply
            self.start_pause_button.setText(pause_text)
            self.start_pause_button.setStyleSheet(f"background-color : {pause_color}")
            self.is_started = True
        else:
            message = json.dumps({"command": "resume" if self.is_paused else "pause"}).encode()
            AsyncioPySide6.runTask(nats_request(self.nats_connection, "GameMasterControl.Clock", message))
            if self.is_paused is True:
                self.start_pause_button.setText(pause_text)
                self.start_pause_button.setStyleSheet(f"background-color : {pause_color}")
                self.is_paused = False
            else:
                self.start_pause_button.setText("RESUME")
                self.start_pause_button.setStyleSheet("background-color : #8F0B0B")
                self.is_paused = True

    @Slot()
    def stop_button_pressed(self):
        if self.is_started is False:
            QMessageBox.critical(self, "Error", "Orchestrator must be started first")
            return

        message = json.dumps({"command": "stop"}).encode()
        self.stop_button.setText("Stopping...")
        AsyncioPySide6.runTask(nats_request(self.nats_connection, self.pub_name, message))

    @Slot()
    def send_dsl_button_pressed(self):
        dsl_command = self.input_dsl_command.text().strip()
        if dsl_command == "":
            QMessageBox.critical(self, "Error", "Empty DSL command")
            return
        if WITH_LEGACY_DSL:
            if not self.dsl_server_started:
                QMessageBox.critical(self, "Error", "DSL server must be started first")
                return
            reply = self.game_master_client.post_dsl_command(dsl_command)
        else:
            if self.simulation_id is None:
                QMessageBox.critical(self, "Error", "Orchestrator must be initialized first")
                return
            response = requests.post(f"{GAME_MASTER_URL}/trainer/dsl_command", json={"dsl_command": dsl_command, "source": "Python_hmi"})
            reply = response.json()
        print("DSL command upload received the following reply\n", reply)
        QMessageBox.information(self, "Info", "DSL upload reply:\n" + json.dumps(reply, indent=4))

    @Slot()
    def state_button_pressed(self, button_id):
        if self.data[button_id] == 2:
            payload = {"id": button_id, "value": 1}
            if button_id in self.tase2_by_id:
                payload["tase2"] = get_tase2_extension(self.tase2_by_id[button_id], "TC")
            message = json.dumps(payload).encode()
            print(message, flush=True)
            AsyncioPySide6.runTask(nats_request(self.nats_connection, self.pub_name, message))
            self.buttons[button_id].setText(f"Line {button_id} OFF")
            self.buttons[button_id].setStyleSheet("background-color : red")
        else:
            payload = {"id": button_id, "value": 2}
            if button_id in self.tase2_by_id:
                payload["tase2"] = get_tase2_extension(self.tase2_by_id[button_id], "TC")
            message = json.dumps(payload).encode()
            print(message, flush=True)
            AsyncioPySide6.runTask(nats_request(self.nats_connection, self.pub_name, message))
            self.buttons[button_id].setText(f"Line {button_id} ON")
            self.buttons[button_id].setStyleSheet("background-color : green")

    @Slot()
    def bool_button_pressed(self, button_id):
        if self.data[button_id] == Breaker.CMD_CLOSE.value:
            # Open
            payload = {"id": button_id, "value": Breaker.CMD_OPEN.value}
            if button_id in self.tase2_by_id:
                payload["tase2"] = get_tase2_extension(self.tase2_by_id[button_id], "TC")
            message = json.dumps(payload).encode()
            print(f'bool_button_pressed, button is closed ({self.data[button_id]}) -> {message}', flush=True)
            AsyncioPySide6.runTask(nats_request(self.nats_connection, self.pub_name, message))
        else:
            # Close
            payload = {"id": button_id, "value": Breaker.CMD_CLOSE.value}
            if button_id in self.tase2_by_id:
                payload["tase2"] = get_tase2_extension(self.tase2_by_id[button_id], "TC")
            message = json.dumps(payload).encode()
            print(f'bool_button_pressed, button is opened ({self.data[button_id]}) -> {message}', flush=True)
            AsyncioPySide6.runTask(nats_request(self.nats_connection, self.pub_name, message))

    @Slot()
    def simple_button_pressed(self, button_id):
        if self.data[button_id] == 0:
            # Open
            message = json.dumps({"id": button_id, "value": 1}).encode()
            print("Sending", message)
            AsyncioPySide6.runTask(nats_request(self.nats_connection, self.pub_name, message))
        else:
            # Close
            message = json.dumps({"id": button_id, "value": 0}).encode()
            print("Sending", message)
            AsyncioPySide6.runTask(nats_request(self.nats_connection, self.pub_name, message))

    def update_buttons(self):
        for button_id in self.state_button_ids:
            if self.data[button_id] == 1:
                self.buttons[button_id].setText(f"Line {button_id} OFF")
                self.buttons[button_id].setStyleSheet("background-color : red")
            else:
                self.buttons[button_id].setText(f"Line {button_id} ON")
                self.buttons[button_id].setStyleSheet("background-color : green")

        for button_id in self.bool_button_ids:
            if self.data[button_id] == Breaker.CMD_OPEN.value:
                self.buttons[button_id].setText(f"{button_id} opened")
                self.buttons[button_id].setStyleSheet("background-color : red")
            else:
                self.buttons[button_id].setText(f"{button_id} closed")
                self.buttons[button_id].setStyleSheet("background-color : green")

        for button_id in self.simple_button_ids:
            if self.data[button_id] == 1:
                self.buttons[button_id].setText(f"{button_id} TRUE")
                self.buttons[button_id].setStyleSheet("background-color : red")
            else:
                self.buttons[button_id].setText(f"{button_id} FALSE")
                self.buttons[button_id].setStyleSheet("background-color : green")

    @Slot()
    def slider_update(self, slider_id, value):
        idx = self.slider_ids.index(slider_id)
        v = value/100
        lunit = f'{v:.2f}{self.slider_units[idx]}'
        value = (value/100-self.slider_min[idx]) / (self.slider_max[idx]-self.slider_min[idx])
        translated_value = self.slider_tmin[idx] + value*(self.slider_tmax[idx]-self.slider_tmin[idx])
        self.data[slider_id] = translated_value
        payload = {"id": slider_id, "value": translated_value}
        if slider_id in self.tase2_by_id:
            payload["tase2"] = get_tase2_extension(self.tase2_by_id[slider_id], "TVC")
        message = json.dumps(payload).encode()
        print(message, flush=True)
        print(f'Updating slider label: {lunit}')
        self.label_unit[slider_id].setText(lunit)
        #self.label_unit[idx].repaint()
        AsyncioPySide6.runTask(nats_request(self.nats_connection, self.pub_name, message))

    def refresh_hmi(self):
        for graph in self.graphs:
            graph.update(self.time, self.data)
        self.update_buttons()

    async def message_handler(self, msg: nats.aio.msg.Msg):
        # print("Subject", msg.subject)
        data = msg.data.decode()
        message = json.loads(data)

        id = message["id"]
        value = message.get("value")
        if value is None:
            value = message["stVal"]

        if id in self.bool_button_ids or id in self.simple_button_ids or id in self.state_button_ids:
            if self.data[id] != value:
                print(f'message_handler -> State changed for {id}: {value} (old value={self.data[id]})', flush=True)

        time_sent = message.get("time")  # ActualMeasurement
        if time_sent is None:
            time_sent = message.get("time_sent")  # Information Received
        if time_sent is None:
            time_sent = message["ts"]  # Telesignalisation
            if self.initial_timestamp == 0:
                self.initial_timestamp = time_sent - self.start_time
            time_sent -= self.initial_timestamp

        self.data[id] = value

        for graph in self.graphs:
            for graph_name, graph_input_list in graph.graph_inputs.items():
                for graph_input in graph_input_list:
                    if graph_input == id:
                        graph.scatter_data[graph_name][graph_input][0].append(time_sent)
                        graph.scatter_data[graph_name][graph_input][1].append(value)

    async def fake_message_handler(self, msg):
        pass

    async def stop_message_handler(self, msg: nats.aio.msg.Msg):
        print(msg.data.decode())
        QTimer.singleShot(0, QApplication.quit)

    async def json_message_handler(self, msg: nats.aio.msg.Msg):
        message = msg.data.decode()
        data = json.loads(message)
        mdl = data["modelName"]
        secs = str(datetime.timedelta(seconds=int(float(data["time"]))))
        msg = data.get('message')
        if msg is not None:
            if len(mdl) > 9:
                if mdl[7] == '_':
                    mdl = mdl[8:]
                mdl = mdl.removeprefix('DM_')
                mdl = mdl.removeprefix('MODELE_ACMC_')
                mdl = mdl.removesuffix('_OC')
            tabsup = '\t'
            if len(mdl) > 8:
                tabsup = ''
            if len(msg) > 80:
                msg = msg[0:80] + ' ...'
            txt = f'{secs}\t{mdl}{tabsup}\t{msg}'
            self.text.append(txt)
            # print('= logbook =', json.dumps(message))
        else:
            desc = data['description'] # .replace('<', '&lt;').replace('>', '&gt;')
            type = data['eventType']
            tabsup = '\t'
            txt = f'{secs}\t{mdl}{tabsup}\t{type}\t{desc}'
            self.alarm.ensureCursorVisible()
            if type == 'BEGIN':
                self.alarm.setTextColor(self.orange)
            elif type == 'END':
                self.alarm.setTextColor(self.green)
            self.alarm.append(txt)
            # print('= alarms =', json.dumps(message))

    async def time_message_handler(self, msg: nats.aio.msg.Msg):
        message = json.loads(msg.data.decode())
        self.time = float(message["current_time"])
        self.clock_text.setText(f"time: {int(self.time)}")

        # Force update buttons if simulation is launched by another mean than this HMI
        if not self.simulation_id:
            self.simulation_id = "placeholder"
        if not self.is_started:
            self.is_started = True
            pause_text = "PAUSE"
            pause_color = "#006A4E"
            self.start_pause_button.setText(pause_text)
            self.start_pause_button.setStyleSheet(f"background-color : {pause_color}")
            self.is_paused = False

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("config_file")
    parser.add_argument("application")
    parser.add_argument("--start_time", type=float, default=0)
    parser.add_argument("--mode", type=str, default="CLICKHOUSE")
    args = parser.parse_args()

    # Make Qt application close on SIGINT (ctrl+C)
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    # Make Qt application close on SIGTERM
    signal.signal(signal.SIGTERM, signal.SIG_DFL)

    if args.mode == "CLICKHOUSE":
        mode = Mode.CLICKHOUSE
    else:
        mode = Mode.FILESYSTEM

    app = QApplication([])
    AsyncioPySide6.initialize()
    widget = HMI(args.config_file, args.application, args.start_time, mode)
    if args.application == "hmi":
        X = 0
    else:  # game_master
        X = 1920/2
    widget.setGeometry(X, 0, 1920/2-0, 1000)
    widget.show()
    sys.exit(app.exec())
    AsyncioPySide6.dispose()
