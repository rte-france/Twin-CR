"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import argparse
import clickhouse_connect
import pandas as pd
import matplotlib.pyplot as plt
import os

def get_time_field(table_name):
    if table_name in ["MeasurementSent", "ControlSent"]:
        return "time_sent"
    elif table_name in ["MeasurementReceived", "ControlReceived"]:
        return "time_received"
    else:
        return "time"

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Fetch and plot measurement/control data from ClickHouse")
parser.add_argument(
    "ids",
    nargs="*",
    help="One or more IDs to fetch measurement data for (default: all IDs)"
)
parser.add_argument(
    "--topic", default=None, help="Filter by topic (default: all topics)"
)
parser.add_argument(
    "--host", default="localhost", help="ClickHouse host (default: localhost)"
)
parser.add_argument(
    "--port", type=int, default=8123, help="ClickHouse HTTP port (default: 8123)"
)
parser.add_argument(
    "--user", default="default", help="ClickHouse username (default: default)"
)
parser.add_argument(
    "--password", default="", help="ClickHouse password (default: empty)"
)
parser.add_argument(
    "--database", default=None, help="Database name (default: latest sim_YYYY_MM_DD_HH_MM_SS)"
)
parser.add_argument(
    "--table", default="MeasurementReceived", help="Measurement table name (default: MeasurementReceived)"
)
parser.add_argument(
    "--include-control-annotations", action="store_true", help="Also fetch ControlReceived and show them as annotations"
)
parser.add_argument(
    "--outdir", default="outputs", help="Directory to store CSV and plots"
)
args = parser.parse_args()

# Connect to ClickHouse
client = clickhouse_connect.get_client(
    host=args.host,
    port=args.port,
    username=args.user,
    password=args.password,
)

# Find latest simulation DB if not provided
if args.database is None:
    dbs = client.query("SHOW DATABASES").result_rows
    sim_dbs = sorted([row[0] for row in dbs if row[0].startswith("sim_")])
    if not sim_dbs:
        print("No simulation databases found (sim_YYYY_MM_DD_HH_MM_SS)")
        exit(1)
    args.database = sim_dbs[-1]  # Alphabetical order -> last is most recent one
    print(f"No database specified, using latest: {args.database}")

# Switch client to selected DB
client.command(f"USE {args.database}")

# Build query
where_clauses = []
params = {}

if args.ids:
    where_clauses.append("id IN %(ids)s")
    params["ids"] = args.ids

if args.topic:
    where_clauses.append("topic = %(topic)s")
    params["topic"] = args.topic

where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

time_field = get_time_field(args.table)
query = f"""
    SELECT id, value, {time_field}
    FROM {args.table}
    {where_sql}
    ORDER BY {time_field}
"""

table_data = client.query(query, parameters=params)

if not table_data.result_rows:
    print("Warning: No data found for the requested parameters")
    exit(0)

df = pd.DataFrame(table_data.result_rows, columns=table_data.column_names)

# Pivot so columns are "time", "id1", "id2", etc. If there is no value for a given id at a given time, it will automatically be filled with a "NaN" (and thus skipped in matplotlib)
df_pivot = df.pivot_table(
    index=f"{time_field}",
    columns="id",
    values="value"
).reset_index()

df_pivot = df_pivot.rename(columns={f"{time_field}": "time"})

# Fetch control data if requested
df_ctrl = None
if args.include_control_annotations:
    ctrl_tables = ["ControlReceived", "ActualControl"]
    dfs = []
    for table in ctrl_tables:
        time_field = get_time_field(table)
        query_ctrl = f"""
            SELECT id, value, {time_field}
            FROM {table}
            ORDER BY {time_field}
        """

        data_ctrl = client.query(query_ctrl)
        if data_ctrl.result_rows:
            df = pd.DataFrame(data_ctrl.result_rows, columns=data_ctrl.column_names)
            df = df.rename(columns={f"{time_field}": "time"})
            dfs.append(df)
    if dfs:
        df_ctrl = pd.concat(dfs, ignore_index=True)
        df_ctrl = df_ctrl.pivot_table(
            index=f"{time_field}",
            columns="id",
            values="value"
        ).reset_index()

        df_ctrl = df_ctrl.rename(columns={f"{time_field}": "time"})

os.makedirs(args.outdir, exist_ok=True)

# Build output filenames
topic_suffix = f"_{args.topic}" if args.topic else ""
ctrl_suffix = "_withControl" if args.include_control_annotations else ""
csv_file = os.path.join(args.outdir, f"{args.database}{topic_suffix}.csv")
csv_file_ctrl = os.path.join(args.outdir, f"{args.database}{topic_suffix}_ctrl.csv")
plot_file = os.path.join(args.outdir, f"{args.database}{topic_suffix}{ctrl_suffix}.png")

# Save CSV
df_pivot.to_csv(csv_file, index=False)
print(f"Data saved to {csv_file}")
if df_ctrl is not None and not df_ctrl.empty:
    df_ctrl.to_csv(csv_file_ctrl, index=False)
    print(f"Data saved to {csv_file_ctrl}")

# Plot
plt.figure(figsize=(12, 7))

# Plot curves
for col in df_pivot.columns[1:]:  # skip "time"
    plt.plot(df_pivot["time"], df_pivot[col], marker="o", linestyle="-", label=col)

# Annotate controls
if df_ctrl is not None and not df_ctrl.empty:
    for col in df_ctrl.columns[1:]:  # skip "time"
        for _, row in df_ctrl.iterrows():
            plt.annotate(
                f"{col}:{row[col]}",
                xy=(row["time"], row[col]),
                xytext=(0, 10),
                textcoords="offset points",
                fontsize=8,
                rotation=30,
                ha="left",
                va="bottom",
                arrowprops=dict(arrowstyle="->", lw=0.5)
            )

plt.xlabel("Time")
plt.ylabel("Value")
title = f"Values from {args.database}"
if args.topic:
    title += f" (topic={args.topic})"
plt.title(title)
plt.legend(title="Measurement IDs")
plt.grid(True)
plt.tight_layout()

plt.savefig(plot_file)
plt.close()
print(f"Plot saved to {plot_file}")
