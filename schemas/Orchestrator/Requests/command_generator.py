"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import asyncio
import json
import textwrap
import tkinter as tk
from tkinter import ttk
from pathlib import Path
import jsonschema
from nats.aio.client import Client as NATS
from nats.errors import NoServersError, NoRespondersError, ConnectionClosedError

nats_connection = NATS()
loop = asyncio.get_event_loop()

connected = False
try:
    loop.run_until_complete(nats_connection.connect("nats://127.0.0.1:4222", connect_timeout=1, allow_reconnect=True, max_reconnect_attempts=1, reconnect_time_wait=1))
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

async def nats_request(nats_connection: NATS, subject: str, message: bytes, timeout=5.0):
    try:
        print("Sending", message, "to", subject)
        response = await nats_connection.request(subject, message, timeout)
        reply = response.data.decode()
        return reply
    except asyncio.TimeoutError:
        return "timeout"
    except NoRespondersError:
        return f"No subscribers to {subject}"


class SchemaLoader:
    def __init__(self):
        self.cache = {}

    def load(self, path):
        if path not in self.cache:
            with open(path) as f:
                self.cache[path] = json.load(f)
        return self.cache[path]

loader = SchemaLoader()

class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = str(text).strip() if text is not None else ""
        self.label = None

        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _=None):
        if self.label or not self.text:
            return

        root = self.widget.winfo_toplevel()

        self.label = tk.Label(
            root,
            text=self.text,
            background="#ffffe0",
            foreground="black",
            relief="solid",
            borderwidth=1,
            wraplength=400,
            justify="left",
            anchor="w"
        )

        x = self.widget.winfo_rootx() - root.winfo_rootx() + 20
        y = self.widget.winfo_rooty() - root.winfo_rooty() + 20

        self.label.place(x=x, y=y)
        self.label.lift()

    def hide(self, _=None):
        if self.label:
            self.label.destroy()
            self.label = None



class ArrayEditor(tk.Frame):
    def __init__(self, parent, item_schema):
        super().__init__(parent)
        self.item_schema = item_schema
        self.items = []

        ttk.Button(self, text="+ Add", command=self.add_item).pack(anchor="w")

    def add_item(self):
        row = tk.Frame(self)
        row.pack(fill="x", pady=2)

        form = SchemaForm(row, self.item_schema)
        form.pack(side="left", fill="x", expand=True)

        ttk.Button(row, text="✖", command=lambda: self.remove_item(row, form)).pack(side="right")

        self.items.append(form)

    def remove_item(self, row, form):
        row.destroy()
        self.items.remove(form)

    def get_value(self):
        values = []
        for form in self.items:
            v = form.get_value()
            if v:
                values.append(v)
        return values


class SchemaForm(tk.Frame):
    def __init__(self, parent, schema, required=True):
        super().__init__(parent)
        self.schema = schema
        self.required = required
        self.widgets = {}
        self.build(schema)

    def resolve(self, schema):
        if "$ref" in schema:
            return loader.load(schema["$ref"])
        return schema

    def build(self, schema):
        schema = self.resolve(schema)

        # --- allOf: merge schemas ---
        if "allOf" in schema:
            for subschema in schema["allOf"]:
                subform = SchemaForm(self, subschema)
                subform.pack(fill="both", expand=True)
                self.widgets.update(subform.widgets)
            return

        # --- oneOf: dropdown selector ---
        if "oneOf" in schema:
            self.build_oneof(schema["oneOf"])
            return

        # --- object ---
        if schema.get("type") == "object":
            required_props = set(schema.get("required", []))
            for name, prop in schema.get("properties", {}).items():
                row = tk.Frame(self)
                row.pack(fill="x", pady=2)

                label = tk.Label(row, text=name, width=25, anchor="w")
                label.pack(side="left")

                is_required = name in required_props
                widget = self.build_field(row, prop, is_required)
                description = self.resolve(prop).get("description")
                if description:
                    Tooltip(label, description)
                    Tooltip(widget, description)
                self.widgets[name] = widget
            return

        if schema.get("type") in ["number", "integer", "string", "boolean"]:
            self._scalar = True
            self._scalar_type = schema.get("type")

            row = tk.Frame(self)
            row.pack(fill="x", pady=2)

            widget = self.build_field(row, schema, required=True)
            self.widgets["_value"] = widget
            return

        print("Warning: unhandled type", schema.get("type"))

    def option_label(self, schema, index):
        if "title" in schema:
            return schema["title"]

        if "$ref" in schema:
            return Path(schema["$ref"]).stem

        return f"option {index}"

    def build_oneof(self, variants):
        labels = []
        forms = []

        option_descriptions = []

        if not self.required:
            labels.append("None")
            forms.append(None)
            option_descriptions.append("Leave field unset")

        for i, v in enumerate(variants):
            labels.append(self.option_label(v, i))
            forms.append(SchemaForm(self, v))
            option_descriptions.append(v.get("description", ""))

        selector = ttk.Combobox(self, values=labels, state="readonly")
        selector.pack(fill="x")

        Tooltip(selector, "\n".join(
            f"{label}: {desc}"
            for label, desc in zip(labels, option_descriptions)
            if desc
        ))

        container = tk.Frame(self)
        container.pack(fill="both", expand=True)

        def on_select(event=None):
            for f in forms:
                if f is not None:
                    f.pack_forget()
            idx = selector.current()
            if forms[idx] is not None:
                forms[idx].pack(fill="both", expand=True)

        selector.bind("<<ComboboxSelected>>", on_select)
        selector.current(0)
        on_select()

        self.widgets["_oneOf"] = (selector, forms)

    def build_field(self, parent, schema, required):
        schema = self.resolve(schema)
        default = schema.get("default")

        if "const" in schema:
            e = ttk.Entry(parent)
            e.insert(0, schema["const"])
            e.config(state="disabled")
            e.pack(fill="x")
            return e

        t = schema.get("type")

        if t == "string":
            v = tk.StringVar(value=default)
            e = ttk.Entry(parent, textvariable=v)
            e._type = t
            e._v = v  # Avoids garbage collection
            if default is not None:
                e.insert(0, str(default))
            e.pack(fill="x")
            return e

        if t == "number":
            v = tk.StringVar(value=default)
            e = ttk.Entry(parent, textvariable=v)
            e._type = t
            e._v = v  # Avoids garbage collection
            e.pack(fill="x")

            # Prevent invalid characters
            def validate_number(P):
                if P == "":
                    return True
                try:
                    float(P)
                    return True
                except ValueError:
                    return False

            reg = parent.register(validate_number)
            e.config(validate="key", validatecommand=(reg, "%P"))
            return e

        if t == "integer":
            v = tk.StringVar(value=default)
            e = ttk.Entry(parent, textvariable=v)
            e._type = t
            e._v = v  # Avoids garbage collection
            if default is not None:
                e.insert(0, str(default))
            e.pack(fill="x")

            def validate_integer(P):
                if P == "":
                    return True
                try:
                    int(P)
                    return True
                except ValueError:
                    return False

            reg = parent.register(validate_integer)
            e.config(validate="key", validatecommand=(reg, "%P"))
            return e

        if t == "boolean":
            var = tk.BooleanVar()
            if default is not None:
                var.set(bool(default))
            cb = ttk.Checkbutton(parent, variable=var)
            cb.pack()
            return cb

        if t == "object" or "oneOf" in schema or "allOf" in schema:
            f = SchemaForm(parent, schema, required)
            f.pack(fill="both", expand=True)
            return f

        if schema.get("type") == "array":
            editor = ArrayEditor(parent, schema["items"])
            editor.pack(fill="x")
            return editor

        return None

    def get_value(self):
        result = {}

        for name, widget in self.widgets.items():
            if getattr(self, "_scalar", False):
                widget = self.widgets.get("_value")
                if widget is None:
                    return None
                if isinstance(widget, ttk.Entry):
                    text = widget.get().strip()
                    if text == "":
                        return None
                    if self._scalar_type == "number":
                        return float(text)
                    if self._scalar_type == "integer":
                        return int(text)
                    return text
                if isinstance(widget, ttk.Checkbutton):
                    return widget.instate(["selected"])
            elif name == "_oneOf":
                selector, forms = widget
                form = forms[selector.current()]
                if form is not None:
                    result.update(form.get_value())
            elif isinstance(widget, SchemaForm):
                value = widget.get_value()
                if value:  # Only include if non-empty dict
                    result[name] = value
            elif isinstance(widget, ttk.Checkbutton):
                result[name] = widget.instate(['selected'])  # Return True if box is selected
            elif isinstance(widget, ArrayEditor):
                arr = widget.get_value()
                if arr:
                    result[name] = arr
            elif isinstance(widget, ttk.Entry):
                # Convert string input to appropriate type
                text = widget.get().strip()
                if text != "":
                    # Check widget type (assume stored in widget._type during creation)
                    if getattr(widget, "_type", None) == "number":
                        result[name] = float(text)
                    elif getattr(widget, "_type", None) == "integer":
                        result[name] = int(text)
                    else:
                        result[name] = text
            elif widget:
                value = widget.get()
                if value not in ("", None):
                    result[name] = value

        return result


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Command Generator")

        self.schema = loader.load("command.json")
        self.form = SchemaForm(self, self.schema)
        self.form.pack(fill="both", expand=True)
        self.resolver = jsonschema.RefResolver(base_uri=f"file://{__file__}", referrer=self.schema)

        # Output area for JSON
        self.json_text = tk.Text(self, height=15, width=120)
        self.json_text.pack(padx=10, pady=5)

        # Warning label
        self.warning_text = tk.Text(self, height=5, width=120)
        self.warning_text.pack()

        # Output area for orchestrator reply
        self.reply_text = tk.Text(self, height=15, width=120)
        self.reply_text.pack(padx=10, pady=5)

        # Buttons
        self.generate_btn = tk.Button(self, text="Generate JSON", command=self.generate)
        self.generate_btn.pack(pady=5)

        self.send_btn = tk.Button(self, text="Send Command", command=self.send_command)
        self.send_btn.pack(pady=5)

    def generate(self):
        data = self.form.get_value()
        json_str = json.dumps(data, indent=2)
        self.json_text.delete("1.0", tk.END)
        self.json_text.insert(tk.END, json_str)

        # Validate JSON against schema
        self.warning_text.delete("1.0", tk.END)
        try:
            jsonschema.validate(instance=data, schema=self.schema, resolver=self.resolver)
            self.warning_text.insert(tk.END, "Valid command")
            self.warning_text.config(fg="green")
        except jsonschema.ValidationError as e:
            wrapped = "\n".join(textwrap.wrap(str(e), width=80))
            self.warning_text.insert(tk.END, wrapped)
            self.warning_text.config(fg="red")

    def send_command(self):
        self.generate()
        data = self.form.get_value()
        cmd = json.dumps(data, indent=2)

        if nats_connection:
            try:
                reply = loop.run_until_complete(nats_request(nats_connection, "GameMasterControl.command_generator", cmd.encode()))
            except ConnectionClosedError:
                print("Connection was closed. Reconnecting...")
                loop.run_until_complete(nats_connection.connect("nats://127.0.0.1:4222", connect_timeout=1, allow_reconnect=True, max_reconnect_attempts=1, reconnect_time_wait=1))
                reply = loop.run_until_complete(nats_request(nats_connection, "GameMasterControl.command_generator", cmd.encode()))
        else:
            reply = "Not NATS connection, cannot launch command"
        print(reply)

        self.reply_text.delete("1.0", tk.END)
        self.reply_text.insert(tk.END, reply)

if __name__ == "__main__":
    App().mainloop()
