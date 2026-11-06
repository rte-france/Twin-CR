"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Small interface to show the cyber part of a system and send network modifications (thorugh scenarios) to the orchestrator.
Only tested on the Nordic example
Usage: python network_player.py ../../docs/orchestrator/examples/Nordic/cyber_config.json
"""

import sys
import asyncio
import networkx as nx

from numpy.linalg import norm
import numpy as np
from nats.aio.client import Client as NATS
from nats.errors import NoServersError, NoRespondersError
import json

from kivy.app import App
from kivy.config import Config
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, PushMatrix, PopMatrix, Translate, Ellipse, Line, Rectangle
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label

from network_config_parser import CyberConfigParser

Config.set('input', 'mouse', 'mouse,disable_multitouch')

nats_connection = NATS()
loop = asyncio.get_event_loop()

connected = False
try:
    loop.run_until_complete(nats_connection.connect("nats://127.0.0.1:4222", connect_timeout=1, allow_reconnect=False, max_reconnect_attempts=1, reconnect_time_wait=1))
    connected = True
except ConnectionRefusedError as e:
    print('\033[93m' + f"Warning: Connection refused: {e}")
except NoServersError as e:
    print('\033[93m' + f"Warning: No server: {e}")
except OSError as e:
    print('\033[93m' + f"Warning: OS-level error: {e}")

if not connected:
    print('\033[93m' + "[ERROR  ] Warning connection to NATS server failed, continuing in demo mode")
    nats_connection = None


async def nats_request(nats_connection: NATS, subject: str, message: bytes, timeout=2.0):
    try:
        print("Sending", message, "to", subject)
        response = await nats_connection.request(subject, message, timeout)
        reply = response.data.decode()
        return reply
    except asyncio.TimeoutError:
        return "timeout"
    except NoRespondersError:
        return f"No subscribers to {subject}"

def is_point_near_line(px, py, p1, p2, threshold):
    line = np.array(p2) - np.array(p1)
    point = np.array([px, py])
    length = norm(line)
    if length == 0:
        return False
    t = np.dot(point - p1, line) / (length**2)
    t = max(0, min(1, t))
    proj = p1 + t * line
    return norm(proj - point) <= threshold


class GraphWidget(Widget):
    def __init__(self, cyber_config_file, **kwargs):
        super().__init__(**kwargs)
        self.G: nx.DiGraph = CyberConfigParser.parse_config(cyber_config_file)

        fixed_pos = {node: data['pos'] for node, data in self.G.nodes(data=True) if 'pos' in data}
        if fixed_pos:
            layout = nx.spring_layout(self.G, seed=42, pos=fixed_pos, fixed=fixed_pos.keys())
        else:
            layout = nx.spring_layout(self.G, seed=42)

        scale = 2000
        self.node_positions = {
            node: (pos[0] * scale, pos[1] * scale)
            for node, pos in layout.items()
        }
        self.edge_colors = {}
        self.node_colors = {}

        self.pan = [Window.width / 2, Window.height / 2]
        self.scale = 1.0
        self._touch_start = None
        self.node_radius = 20
        self.context_menu = None

        self.size_hint = (1, 1)
        self.bind(pos=self.redraw, size=self.redraw)
        Window.bind(on_scroll=self.on_scroll)

        self.redraw()

    def on_touch_down(self, touch):
        is_right_click = touch.button == 'right'  # True right click
        is_ctrl_click = touch.button == 'left' and ('ctrl' in Window._modifiers)  # Mac "right click"
        if is_right_click or is_ctrl_click:
            x_canvas, y_canvas = (touch.x - self.pan[0]) / self.scale, (touch.y - self.pan[1]) / self.scale
            # Check if click near a node
            for node, (x, y) in self.node_positions.items():
                dx = x - x_canvas
                dy = y - y_canvas
                if dx * dx + dy * dy <= self.node_radius**2:
                    self.show_node_context_menu(node, touch.pos)
                    return True

            # Check if click near an edge
            edge_threshold = 10  # adjust for click tolerance
            for u, v in self.G.edges():
                p1 = self.node_positions[u]
                p2 = self.node_positions[v]
                if is_point_near_line(x_canvas, y_canvas, p1, p2, edge_threshold):
                    self.show_edge_context_menu((u, v), touch.pos)
                    return True
            return True
        if touch.button == "scrolldown":
            self.on_scroll(Window, 0, 1, *touch.pos)
            return True
        if touch.button == "scrollup":
            self.on_scroll(Window, 0, -1, *touch.pos)
            return True
        if touch.button == 'left':
            self._touch_start = (touch.x, touch.y)
        return super().on_touch_down(touch)

    def on_scroll(self, window, scroll_x, scroll_y, x, y):
        factor = 1.1 if scroll_y > 0 else 0.9
        self.zoom(factor, (x, y))

    def zoom(self, factor, center):
        mx, my = center
        self.scale *= factor
        self.pan[0] += (1 - factor) * (mx - self.pan[0])
        self.pan[1] += (1 - factor) * (my - self.pan[1])
        self.redraw()

    def on_touch_move(self, touch):
        if self._touch_start:
            dx = touch.x - self._touch_start[0]
            dy = touch.y - self._touch_start[1]
            self.pan[0] += dx
            self.pan[1] += dy
            self._touch_start = (touch.x, touch.y)
            self.redraw()
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        self._touch_start = None
        return super().on_touch_up(touch)

    def redraw(self, *args):
        self.canvas.clear()

        with self.canvas.before:
            # pass
            Color(1, 1, 1)
            Rectangle(pos=self.pos, size=self.size)

        with self.canvas:
            PushMatrix()
            Translate(*self.pan)
            # Scale(self.scale)  # Does not seem to work, so do it manually

            r = self.node_radius * self.scale # Node radius
            for u, v in self.G.edges():
                x1, y1 = self.node_positions[u]
                x2, y2 = self.node_positions[v]
                x1 *= self.scale
                x2 *= self.scale
                y1 *= self.scale
                y2 *= self.scale
                color = self.edge_colors.get((u, v)) or self.edge_colors.get((v, u)) or (0.5, 0.5, 0.5)
                Color(*color)
                Line(points=[x1, y1, x2, y2], width=1)

            for node, (x, y) in self.node_positions.items():
                x *= self.scale
                y *= self.scale
                if node == "CC":
                    Color(0, 0, 1)
                elif node == "S_1042":
                    Color(0, 0, 1)
                else:
                    Color(0.3, 0.7, 0)

                if self.node_colors.get(node):
                    Color(*self.node_colors[node])

                Ellipse(pos=(x - r, y - r), size=(2*r, 2*r))

                # Create label using CoreLabel
                label = CoreLabel(text=node, font_size=12)
                label.refresh()

                # Center label horizontally, place slightly below the node
                texture = label.texture
                Rectangle(
                    texture=texture,
                    pos=(x - texture.size[0] / 2, y - self.node_radius - texture.size[1] - 2),
                    size=texture.size
                )

            PopMatrix()

    def mark_edge_deleted(self, edge):
        self.edge_colors[edge] = (1, 0, 0)  # Red
        if self.context_menu:
            self.context_menu.dismiss()
        self.redraw()

    def mark_node_deleted(self, node):
        self.node_colors[node] = (1, 0, 0)  # Red
        if self.context_menu:
            self.context_menu.dismiss()
        self.redraw()

    def show_node_context_menu(self, node, pos):
        if self.context_menu:
            self.context_menu.dismiss()

        def attack(_):
            box.clear_widgets()

            # Example title/info
            box.add_widget(Label(text=f"Node: {node}", size_hint_y=None, height=30))
            box.add_widget(Label(text="Enter command:", size_hint_y=None, height=30))

            # Text input field
            input_field = TextInput(
                multiline=True,
                size_hint_y=None,
                height=500,
                # hint_text="e.g., reboot, inspect"
            )
            box.add_widget(input_field)

            # Submit button
            def submit_command(b):
                command = input_field.text
                if not command:
                    self.context_menu.dismiss()
                    return
                cmd = {}
                cmd["t_start_from_now"] = 0
                cmd["command"] = "change_network_characteristics"
                cmd["links"] = []
                cmd["nodes"] = [node]
                try:
                    cmd += json.loads(command)
                except json.decoder.JSONDecodeError:
                    print("Could not decode JSON from input characteristics")
                    self.context_menu.dismiss()
                    return
                if nats_connection:
                    loop.run_until_complete(nats_request(nats_connection, "GameMasterControl.network_player", json.dumps(cmd).encode()))
                # print(f"Command for node {node}: {json.dumps(cmd, indent=4)}")
                self.mark_node_deleted(node)
                self.context_menu.dismiss()

            box.add_widget(Button(
                text="Submit",
                size_hint_y=None,
                height=30,
                on_release=submit_command
            ))

            # Optional close button
            box.add_widget(Button(
                text="Close",
                size_hint_y=None,
                height=30,
                on_release=lambda b: self.context_menu.dismiss()
            ))

        def delete(btn):
            self.mark_node_deleted(node)
            self.context_menu.dismiss()
            cmd = {}
            cmd["t_start_from_now"] = 0
            cmd["command"] = "change_network_characteristics"
            cmd["links"] = []
            cmd["nodes"] = [node]
            cmd["drop_function"] = {"type": "fixed", "value": True}
            if nats_connection:
                loop.run_until_complete(nats_request(nats_connection, "GameMasterControl.network_player", json.dumps(cmd).encode()))
            else:
                print("Demo mode: sending command")
                print(json.dumps(cmd, indent=4))

        def inspect(btn):
            self.context_menu.dismiss()
            cmd = {}
            cmd["t_start_from_now"] = 0
            cmd["command"] = "get_node_characteristics"
            cmd["node"] = node
            if nats_connection:
                reply = loop.run_until_complete(nats_request(nats_connection, "GameMasterControl.network_player", json.dumps(cmd).encode()))
                popup = Popup(title="Node characteristics", size_hint=(0.9, 0.9),
                      content=TextInput(text=reply, readonly=True))
                popup.open()
            else:
                print("Demo mode: sending command")
                print(json.dumps(cmd, indent=4))

        def get_path_info(btn):
            self.context_menu.dismiss()
            cmd = {}
            cmd["t_start_from_now"] = 0
            cmd["command"] = "get_path_characteristics"
            cmd["source"] = node
            cmd["destination"] = "CC"
            if nats_connection:
                reply = loop.run_until_complete(nats_request(nats_connection, "GameMasterControl.network_player", json.dumps(cmd).encode()))
                print(reply)
                popup = Popup(title="Node characteristics", size_hint=(0.9, 0.9),
                      content=TextInput(text=reply, readonly=True))
                popup.open()
            else:
                print("Demo mode: sending command")
                print(json.dumps(cmd, indent=4))

        box = BoxLayout(orientation='vertical', spacing=10, size_hint_y=None)
        box.bind(minimum_height=box.setter('height'))
        box.add_widget(Button(text=f"Inspect '{node}'", size_hint_y=None, height=60, on_release=inspect))
        box.add_widget(Button(text=f"Get path to 'CC'", size_hint_y=None, height=60, on_release=get_path_info))
        box.add_widget(Button(text=f"Attack '{node}'", size_hint_y=None, height=60, on_release=attack))
        box.add_widget(Button(text=f"Delete '{node}'", size_hint_y=None, height=60, on_release=delete))

        self.context_menu = Popup(
            title=f"Node: {node}",
            content=box,
            size_hint=(0.4, None),
            height=120 + (60 + 10) * 4,
            auto_dismiss=True,
        )

        Clock.schedule_once(lambda dt: self.context_menu.open(), 0)
        self.context_menu.pos = (pos[0], pos[1])


    def show_edge_context_menu(self, edge, pos):
        if self.context_menu:
            self.context_menu.dismiss()

        def attack(_):
            box.clear_widgets()

            u, v = edge
            box.add_widget(Label(text=f"Link: {u} - {v}", size_hint_y=None, height=30))
            box.add_widget(Label(text="Enter command:", size_hint_y=None, height=30))

            # Text input field
            input_field = TextInput(
                multiline=True,
                size_hint_y=None,
                height=500,
                # hint_text="e.g., reboot, inspect"
            )
            box.add_widget(input_field)

            # Submit button
            def submit_command(b):
                command = input_field.text
                if not command:
                    self.context_menu.dismiss()
                    return
                cmd = {}
                cmd["t_start_from_now"] = 0
                cmd["command"] = "change_network_characteristics"
                cmd["links"] = [{"from": u, "to": v}]
                cmd["nodes"] = []
                try:
                    cmd += json.loads(command)
                except json.decoder.JSONDecodeError:
                    print("Could not decode JSON from input characteristics")
                    self.context_menu.dismiss()
                    return
                if nats_connection:
                    loop.run_until_complete(nats_request(nats_connection, "GameMasterControl.network_player", json.dumps(cmd).encode()))
                # print(f"Command for edge {u} - {v}: {json.dumps(cmd, indent=4)}")
                self.mark_edge_deleted(edge)
                self.context_menu.dismiss()

            box.add_widget(Button(
                text="Submit",
                size_hint_y=None,
                height=30,
                on_release=submit_command
            ))

            # Optional close button
            box.add_widget(Button(
                text="Close",
                size_hint_y=None,
                height=30,
                on_release=lambda b: self.context_menu.dismiss()
            ))

        def delete(btn):
            self.mark_edge_deleted(edge)
            self.context_menu.dismiss()
            cmd = {}
            cmd["t_start_from_now"] = 0
            cmd["command"] = "change_network_characteristics"
            u, v = edge
            cmd["links"] = [{"from": u, "to": v}]
            cmd["nodes"] = []
            cmd["drop_function"] = {"type": "fixed", "value": True}
            if nats_connection:
                loop.run_until_complete(nats_request(nats_connection, "GameMasterControl.network_player", json.dumps(cmd).encode()))
            else:
                print("Demo mode: sending command")
                print(json.dumps(cmd, indent=4))

        def inspect(btn):
            self.context_menu.dismiss()
            cmd = {}
            cmd["t_start_from_now"] = 0
            cmd["command"] = "get_link_characteristics"
            u, v = edge
            cmd["link"] = {"from": u, "to": v}
            if nats_connection:
                reply = {}
                reply[f"{u}-{v}"] = json.loads(loop.run_until_complete(nats_request(nats_connection, "GameMasterControl.network_player", json.dumps(cmd).encode())))
                cmd["link"] = {"from": v, "to": u}
                reply[f"{v}-{u}"] = json.loads(loop.run_until_complete(nats_request(nats_connection, "GameMasterControl.network_player", json.dumps(cmd).encode())))
                popup = Popup(title="Node characteristics", size_hint=(0.9, 0.9),
                      content=TextInput(text=json.dumps(reply, indent=4), readonly=True))
                popup.open()
            else:
                print("Demo mode: sending command")
                print(json.dumps(cmd, indent=4))

        u, v = edge
        box = BoxLayout(orientation='vertical', spacing=5, padding=5)
        box.add_widget(Button(text="Inspect", size_hint_y=None, height=60, on_release=inspect))
        box.add_widget(Button(text="Attack", size_hint_y=None, height=60, on_release=attack))
        box.add_widget(Button(text="Delete", size_hint_y=None, height=60, on_release=delete))

        self.context_menu = Popup(
            title=f"Edge: {u} - {v}",
            content=box,
            size_hint=(0.4, None),
            height=120 + (60 + 10) * 3,
            auto_dismiss=True,
        )

        Clock.schedule_once(lambda dt: self.context_menu.open(), 0)
        self.context_menu.pos = pos


class NetworkPlayer(App):
    def __init__(self, cyber_config_file, **kwargs):
        super().__init__(**kwargs)
        self.cyber_config_file = cyber_config_file

    def build(self):
        layout = FloatLayout()
        graph = GraphWidget(self.cyber_config_file)
        layout.add_widget(graph)
        return layout


if __name__ == '__main__':
    config_file = sys.argv[1]
    NetworkPlayer(config_file).run()
