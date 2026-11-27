# 1. Introduction

This repository contains the source code of the proof-of-concept cyber-physical simulator developed for RTE. This simulator makes use of [Dynawo](https://github.com/dynawo/dynawo) for the physical simulation, and an information flow model for the cyber-simulation.

# 2. Installation

The easiest way to build the Orchestrator system is via the docker-compose system

```bash
docker-compose build # or build twincr-core to only build the orchestrator
```
and run with
```bash
docker-compose up -d
```


If you need to run it natively, you should first, install the orchestrator dependencies
```bash
# For Ubuntu/Debian
apt install -y build-essential cmake git libssl-dev libcurl4-openssl-dev python3 python3-pip libzmq3-dev

# For Mac
brew install zeromq cppzmq
```

and if you also don't run ClickHouse via the docker system
```bash
# For Ubuntu/Debian
sudo apt-get install -y apt-transport-https ca-certificates dirmngr
sudo mkdir -p /etc/apt/keyrings
wget -qO - https://packages.clickhouse.com/CLICKHOUSE-KEY.GPG | sudo tee /etc/apt/keyrings/clickhouse.asc
echo "deb [signed-by=/etc/apt/keyrings/clickhouse.asc] https://packages.clickhouse.com/deb stable main" | sudo tee /etc/apt/sources.list.d/clickhouse.list

sudo apt-get update
sudo apt-get install clickhouse-server clickhouse-client

sudo systemctl enable clickhouse-server
sudo systemctl start clickhouse-server

# For Mac
brew install clickhouse
brew services start clickhouse

# On Windows
docker run -d --name clickhouse-server --ulimit nofile=262144:262144 \
    -p 8123:8123 -p 9000:9000 -p 9009:9009 \
    clickhouse/clickhouse-server
```

Then build and install the orchestrator,

```bash
cd Twin-CR/Orchestrator
mkdir build
cd build
cmake ..
make -j$(nproc)
sudo make install
sudo ldconfig
```

Note: if behind a corporate proxy, https_proxy must be configured during `cmake ..`

### Tests

The DSL regression cases can be run with

```bash
cmake -DORCHESTRATOR_BUILD_TESTS=ON ..
make dsl-tests
```

Each case under `Orchestrator/DSL/tests/cases/` is one CTest entry. A case is a `script.dsl`, an optional `case.toml` giving the run length and any measurements to feed `when` clauses, and an `expected.json` recording every command the engine handed its ScenarioHandler and the time it did so.

After an intended behaviour change, regenerate a case's golden with `dsl_test <case directory> --update` and read the diff before committing it.

## 2.1. Dynawo installation

2 alternatives:
* build Dynawo from source
* use a pre-compiled version

### 2.1.1 Build Dynawo from source
This code makes use of an experimental Dynawo API which is currently only available on this [branch](https://github.com/dynawo/dynawo/tree/3301_rt_dynawo_experiments). Please refer to the Dynawo documentation on how to compile this branch from source.

### 2.1.2 Use a pre-compiled version
`./setup.sh` downloads the public Dynawo (`simulators.zip` of the Twin-CR release set in `envs/dynawo.version`) to the root folder. Alternatively, put a `simulators.zip` archive there yourself (e.g. the RTE one with the private dynawo-rte, see the RTE-internal documentation, not published). It must contain a top-level `simulators/` folder: the session-manager image is built from it, and it is extracted to `simulators/` by `./setup.sh`, or when launching the application via `docker compose` if there is no `simulators` folder yet.

# 3. Usage

Once installed, the orchestrator simulator can be run simply either using

```bash
# .env variable MODE=CLICKHOUSE
orchestrator_exec --from-clickhouse
# .env variable MODE=FILESYSTEM
orchestrator_exec --from-nats
```
or
```bash
orchestrator_exec --from-toml config.toml
```
With the first option, the orchestrator wait for a simulation to be started from the graphical interface. With the second option, it directly starts the simulation specified in the configuration.toml. Note that the second option is not compatible with the DSL server and is for testing only.

An example config.toml file is available in [here](examples/config_template.toml). Please copy it to a suitable location and modify it as needed to run your simulations.

The fields of the configuration file are detailed below:

- log_level
  - Level of logs to be printed, uses standard Python level DEBUG, INFO, WARNING, ERROR, CRITICAL
- Master parameters
  - period
    - Co-simulation time step (in seconds), i.e. how often information is exchanged with the physical simulator
  - dump_period
    - Time interval between each dump of the simulation. If negative, dumps are never performed. Default value: -1
  - speedup
    - Speed up factor compared to real-time (runs in real-time if speedup = 1)
  - myEnvDynawo_path
    - Path to the myEnvDynawo executable
  - log_all_events:
    - true/false, whether to log all information flow model events to Clickhouse
  - publishing_ifl_nodes
    - List of regex patterns matching the information flow model nodes that should publish intermediary information
- Input files
  - Location of the input files of the simulation. Paths can be given either relative to the working dir or as full paths. Detailed documentation for individual input files is given in the [input files section](#4-input-files).
- HMI configuration (mock-up SCADA only, the actual SCADA is still in development)
  - location
    - ID of the communication node where the HMI is installed
  - line_button_ids
    - Deprecated with new Dynawo API
  - bool_button_ids
    - List of boolean variables that can be controlled by push buttons in the HMI. When a button is pressed, it will send a control signal to change the value of the variable with its ID to False (or True depending on the current state of the button).
  - outputs_destination
    - Destination of information for each control signal (e.g. button press) that can be sent by the HMI. More details about information routing the in the [cyber configuration section](#44-cyber-configuration).
  - plot_data
    - ID of the variables to be plotted by the HMI. A separate subplot will be created for each list of variables listed.
- Game master configuration (mock-up game master only, the actual game master is still in development)
  - line_button_ids
    - Deprecated with new Dynawo API
  - bool_button_ids
    - List of boolean variables that can be controlled by push buttons in the game master. When a button is pressed, it will send a control signal to change the value of the variable with its ID to False (or True depending on the current state of the button). (As opposed the SCADA, this information will be sent directly to its destination, without going through the information flow model, and thus without being delayed/corrupted/etc.)
  - outputs_destination
    - Destination of information for each control signal (e.g. button press) that can be sent by the game master. More details about information routing the in the [cyber configuration section](#44-cyber-configuration).
  - plot_data
    - ID of the variables to be plotted by the HMI. A separate subplot will be created for each list of variables listed.

## 3.1 Errors when launching orchestrator

### 3.1.1 what():  Connect failed: No server available for connection
Nats server hasn't been launched.
To launch it:

```bash
docker compose up -d nats
```

### 3.1.2 Exception: Address already in use
Probably an instance of Dynawo is running, can be killed with
```bash
pkill -9 dynawo
```

# 4. Input files

## 4.1. Job file

The jobs file is the Dynawo jobs file to be called to run the simulation. The jobs file must contain a single (valid) job, and have the interactiveSettings set:

- interactiveSettings couplingTimeStep="1." (must match the period in the config.toml)
- CURVES stream has the format "BYTES"
- TIMELINE stream has the format "JSON"
- CONSTRAINTS stream has the format "JSON"
- clock type is EXTERNAL (depends on trigger from ZMQ channel)

e.g.

```xml
		<interactiveSettings couplingTimeStep="1">
            <channels>
                <channel id="zmq_input" kind="INPUT" type="ZMQ" endpoint="tcp://*:5555"/>
                <channel id="zmq_output" kind="OUTPUT" type="ZMQ" endpoint="tcp://*:5556"/>
            </channels>
            <streams>
                <stream data="CURVES" channel="zmq_output" format="BYTES"/>
                <stream data="TIMELINE" channel="zmq_output" format="JSON"/>
                <stream data="CONSTRAINTS" channel="zmq_output" format="JSON"/>
                <stream data="DUMP" channel="zmq_output"/>
            </streams>
            <clock type="EXTERNAL" triggerChannel="zmq_input"/>
        </interactiveSettings>
```

***NOTE***: The Real-time mode of Dynawo currently only works with dynawo_SolverSIM, not dynawo_SolverIDA


## 4.2. Iidm, Dyd and par files

The iidm file contains the static representation of the network. This file must also be read by Dynawo (so it should be consistent with the one specified in the job file). Note that since this project works on replica SCADA systems, it is best to have networks represented in node-breaker topology. A [converter](../../tools/dynawo_toolbox/src/node_breaker_converter.py) is provided to convert a full bus-breaker network to node-breaker. The dyd file must be updated manually however (an example can be found for the [4Bus network](examples/4Bus/4Bus.dyd)).

The 4Bus network itself (`examples/4Bus/4Bus.iidm`, also copied in `examples/4Bus_PSCC/`) is generated with pypowsybl by [generate_4Bus_network.py](examples/4Bus/generate_4Bus_network.py), it is not taken from another project.

The dyd file to be specified is the one that contains the events to use to control Dynawo during the simulation. This file must also be read by Dynawo, so it must be included in the dynModels of the job file.

Indeed, for now, external controls are sent to Dynawo through predefined events (EventQuadripoleDisconnection, EventSetPointBoolean, SetPoint, etc.) whose parameters are modified during the simulation.

For example, if the specified dyd file contains the following lines:


```xml
<dyn:blackBoxModel id="L4032-4042_state" lib="EventQuadripoleDisconnection" parFile="Events.par" parId="L4032-4042_state"/>
<dyn:connect id1="L4032-4042_state" var1="event_state1_value" id2="NETWORK" var2="L4032-4044_state_value"/>
```

and the specified par file (named Events.par to match the ```parFile="Events.par"``` given in the dyd) contains the associated parameters:

```xml
<set id="L4032-4042_state">
  <par type="DOUBLE" name="event_tEvent" value="999999"/>
  <par type="BOOL" name="event_disconnectOrigin" value="true"/>
  <par type="BOOL" name="event_disconnectExtremity" value="true"/>
</set>
```

Then, it will be possible for to change the state of line L4032-4042 during the simulation. In practice, this is done by sending a control signal (e.g. from the HMI or an automaton) with id "L4032-4042_state" (the id of the event as given in the dyd and par files) with a value > 0 (to open the line, <=0 to close the line). In the backend, this is done by:

- Setting "event_disconnectOrigin" and "event_disconnectExtremity" to "true" (if the value is > 0, else to "false").
- Setting "event_tEvent" to the current time (or actually to 0) such that the event is activated at the next time step.
- Scheduling (via the Master queue) to "reset" the event at the next co-simulation timestep by setting "event_tEvent" back to a very high value. This allows for reusing the event at a later time. Indeed, Dynawo events are based on a [when](https://build.openmodelica.org/Documentation/ModelicaReference.%27when%27.html) statement. They thus only impact the simulation at the timestep where the current time becomes larger than "event_tEvent". Changing the value of "event_disconnectOrigin" or "event_disconnectExtremity" for example after the event has already been activated would have no impact. Instead, it is necessary to first "reset" the event by setting "event_tEvent" to a very high value. It should be noted that Dynawo can only activate or reset an event once in a given timestep. So, assuming a period of 1s is used, if we activate an event at t=16s, we then (automatically) schedule the event reset for t=17s, and the event can be reused starting from t=18s. ***As the use of events is considered to be a temporary solution, no safeguards have been added to avoid one from reusing an event while it is being reset.*** Also, it is best practice to have the events used for control in a dedicated dyd file and to have them all initialised with a very high "event_tEvent", because events that "naturally" activate (when the current time is higher than the initially set value of "event_tEvent") are not automatically reset.

To reiterate, the id of the events is used as id of the control variable in the remaining of the simulation. So, in the above example, to open/close the line L4032-4042 from the HMI, the HMI would need a button with id "L4032-4042_state".

The following Dynawo events are supported:
- EventQuadripoleDisconnection
  - Opens a quadripole (e.g. line) when the value of the control signal is > 0, else closes it.
- EventQuadripoleConnection
  - Closes a quadripole (e.g. line) when the value of the control signal is > 0, else opens it.
- EventConnectedStatus
  - Open connection when the value of the control signal is > 0, else closes
- EventSetPointBoolean
  - Set a boolean setpoint to true if the value of the control signal is > 0, else set to false.
- EventSetPointReal
  - Set a real setpoint to the value of the control signal.
- SetPoint
  - Change a setpoint in the simulation. As opposed to the previous events, this model is used to connect to continuous variables instead of discrete ones. Also, it needs to be correctly initialised, e.g. ```<par type="DOUBLE" name="setPoint_Value0" value="0.0"/>``` if the value should be 0 at t=0. Contrarily to other events, setpoints do not need to be reset.
- Updatables: similar to setpoint, but are initialised automatically from the value they are connected to (this means they can only be connected to one value)
  - UpdatableBoolean
  - UpdatableInteger
  - UpdatableDiscrete
  - UpdatableContinuous

The other Dynawo events are not yet supported:
- EventSetPointDoubleReal


## 4.3. Scenario file

***NOTE: the scenario file will likely be replaced by the DSL engine in some future.***

The scenario file is a json file containing the scenarios to be simulated. Note that this file only contains cyber-contingencies. For now, physical contingencies are directly modelled in Dynawo. Scenarios all have two common properties:

- t_start
  - The time (in seconds) at which the event starts.
- t_start_from_now
  - Alternative to "t_start". This gives the time of the event relative to the current time (it must thus be positive or 0). This is particularly useful for events that are scheduled mid-simulation by the game master.
- type
  - The type of scenario

The types of scenarios currently implemented and their parameters are listed in the subsections below with examples. The up-to-date syntax of all commands is also given in a [JSON schema](../../schemas/Orchestrator/Requests/game_master_control.json) file. A simple [Python GUI](../../schemas/Orchestrator/Requests/command_generator.py) is also available to help with generating/launching scenarios.

### 4.3.1. Pause

Pause the simulation (mostly used by the game master to pause a running simulation)

```json
{
    "t_start_from_now": 0,
    "command": "pause",
}
```

### 4.3.2. Stop

Stop the simulation (mostly used by the game master to stop a running simulation)

```json
{
    "command": "stop",
}
```

### 4.3.3. Resume

Resume the simulation. Note: this can only be used with t_start_from_now = 0 (or not specified). Indeed, if the simulation is paused, it does not make sense to schedule resuming at a future time, since future times will never be reached while in pause.

```json
{
    "t_start_from_now": 0,
    "command": "pause",
}
```

### 4.3.4. Fast forward

Let the simulation run at the maximum possible speed.

```json
{
    "t_start_from_now": 0,
    "command": "fast_forward",
}
```

### 4.3.5. Communication network property change

Change the properties of a list of communication links and nodes, the example below changes the properties the communication link from "substation_1" to "CC" (but not from "CC" to "substation_1") and of the communications nodes "substation_3" and "substation_4". The syntax of the delay_function, drop_function, and corruption_functions is the same of in the [cyber configuration file](#44-cyber-configuration). The network characteristics can include either a drop function (that will replace the existing drop function of the links/nodes), a delay function (replace), a corruption function list (added to the existing corruption functions if any), or any combination of the three.

```json
{
    "t_start": 30,
    "command": "change_network_characteristics",
    "links": [
        {
            "from": "substation_1",
            "to": "CC"
        }
    ],
    "nodes": [
        "substation_3",
        "substation_4"
    ],
    "drop_function": {
        "type": "random",
        "value": 0.5
    },
    "corruption_functions": [
        {
            "type": "RandomNoiseMeasurementCorruption",
            "likelihood": 0.01,
            "noise_min": -0.001,
            "noise_max": 0.001
        }
    ]
}
```

### 4.3.6 Get communication network properties

The properties of the communication networks can be obtained from multiple getters:

For nodes:
```json
{
  "command": "get_node_characteristics",
  "node": "S_4011"
}
```

which returns
```json
{
    "reply": {
        "corruption_functions": [],
        "delay_function": {},
        "drop_function": {}
    },
    "status": "OK"
}
```

For links:
```json
{
  "command": "get_link_characteristics",
  "link": {
    "from": "S_4011",
    "to": "RTU"
  }
}
```
with a similar return.

And for the full path between two nodes:
```json
{
  "command": "get_path_characteristics",
  "source": "S_4011",
  "destination": "SCADA"
}
```

which returns the configuration of all links and nodes between the two nodes (in traversal order)
```json
{
    "reply": {
        "link_configs": [
            {
                "corruption_functions": [],
                "delay_function": {
                    "delay": 0.1,
                    "type": "fixed"
                },
                "drop_function": {}
            },
            {
                "corruption_functions": [],
                "delay_function": {
                    "delay": 0.1,
                    "type": "fixed"
                },
                "drop_function": {}
            }
        ],
        "node_configs": [
            {
                "corruption_functions": [],
                "delay_function": {},
                "drop_function": {}
            },
            {
                "corruption_functions": [],
                "delay_function": {},
                "drop_function": {}
            },
            {
                "corruption_functions": [],
                "delay_function": {},
                "drop_function": {}
            }
        ],
        "node_names": [
            "S_4011",
            "ARP",
            "SCADA"
        ]
    },
    "status": "OK"
}
```


### 4.3.7. Get simulation name

Get the name of the current simulation

```json
{
    "command": "get_simulation_name",
}
```

return a JSON like
```json
{
    "reply": "sim_2026_01_02_10_29_35",
    "status": "OK"
}
```

### 4.3.8. Get historical actual measurements

Get the values of past ActualMeasurements

```json
{
  "command": "get_actual_historical_measurements",
  "topic": "S_4011",
  "min_time": 25.0
}
```

return a JSON like
```json
{
    "reply": [
        {
            "id": "NETWORK_Tr1011-4011_P1_value",
            "time": 25,
            "value": 167.37662299656958
        },
        {
            "id": "NETWORK_Tr1011-4011_P2_value",
            "time": 25,
            "value": -167.15230557499387
        }
    ],
    "status": "OK"
}
```

### 4.3.9. Command injection

The example below inject a (malicious) control signal to change the value of "PL1_state" to 1 (i.e. open the line). The signal is sent from "CC" to "substation_1", and can thus be delayed/dropped/corrupted like any other control signal.

```json
[
    {
        "t_start": 20,
        "command": "command_injection",
        "command_id": "PL1_state",
        "value": -1,
        "source": "CC",
        "destination": "substation_1"
    }
]
```
Alternatively, a "command_injection_received" command can be sent directly to its destination (without going through the information flow model), and thus cannot be delayed/dropped/corrupted. It otherwise follows the same syntax.

```json
[
    {
        "t_start": 20,
        "command": "command_injection_received",
        "command_id": "PL1_state",
        "value": -1,
        "source": "CC",
        "destination": "substation_1"
    }
]
```

Similarly, a "command_injection_game_master" command can be used to emit a ActualControl message. This creates a message that is also sent directly to its destination (without going through the information flow model), and thus cannot be delayed/dropped/corrupted. It otherwise follows the same syntax, but has no source and destination specified.

```json
[
    {
        "t_start": 20,
        "command": "command_injection_game_master",
        "command_id": "PL1_state",
        "value": -1
    }
]
```

Finally, a "manual_actuator_scada" command can be used to emulate a manual actuator action for the SCADA side. Such command do not actually impact the simulation, it only sends a TS from the SCADA back to itself.

```json
[
    {
        "t_start": 20,
        "command": "manual_actuator_scada",
        "command_id": "PL1_state",
        "value": -1,
        "topic": "substation_1"
    }
]
```

### 4.3.10. General interrogation

A "general_interrogation" command sends a general interrogation (GI, see [4.4.3](#443-special-node-types)) to an RTU or ARP, which then resends the latest TSes it saved. It goes through the information flow model (it can be delayed/dropped/corrupted, and is acknowledged like any control). "source" is optional and defaults to the SCADA (`[hmi] location`). When sent as a request, the reply contains the control uid of the general interrogation (`{"status": "OK", "control_uid": 42}`).

```json
[
    {
        "t_start": 20,
        "command": "general_interrogation",
        "destination": "RTU_1"
    }
]
```


## 4.4. Cyber configuration

The cyber layer of power systems is represented in the simulation as a directed graph. Each node and link of the graph has a delay function, a drop function, and a list of corruption functions. These functions are applied sequentially to all information that pass through the associated node or link.

The configuration of the cyber model is done through a json file with 5 main fields:
- links
- nodes_characteristics
- nodes_characteristics_by_node_type
- links_characteristics
- links_characteristics_by_link_type

Only the first field is mandatory (if no characteristics are specified for a given link or node, it is assumed that it does not impact the information flow (i.e. no delay, no drop, and no corruption)).

### 4.4.1. Links

Links are listed as

```json
"links": [
    {"from": "substation_1", "fromtype": "RTU", "to": "ARP_1", "totype": "ARP"},
]
```

i.e. links are created from the node listed in the field "from" to the one in the field "to". The fields "fromtype" and "totype" are used to specify the types of the nodes at both sides of the link. In the information flow model, links are represented as directed links, i.e. they are not bidirectional. This is because, in communication networks, links tend to have different characteristics in both directions (e.g. different download and upload speeds). However, here for convenience, each time a link is created from a node to a another one, a second link going in the opposite direction is also created. But, the two links are separate objects with different characteristics.

There is no dedicated list of nodes, as the list of nodes is generated automatically from the list of links.

```json
"***TODO: VERIFY IT IS OK TO SAY SOMETHING LIKE THIS (BELOW) IF THE REPO BECOMES PUBLIC***"
```

As opposed to traditional network simulation, the information flow model does not model routers and the associated routing algorithms. The information path must thus be specified in some other way. Here, we assumed that there is only one path the information can take between a given source and destination (tree-like representation of the network). For this, it is checked that there are no cycles in the non-directed graph created from the (directed) simulated graph.


### 4.4.2. Link and node characteristics

Element characteristics can include either a drop function, a delay function, a corruption function list, or any combination of the three. The example below specifies the characteristics for the link from "substation_1" to "ARP_1". It sets the delay function of the link to a constant delay of 0.1s. As no drop function nor corruption function(s) are specified, these are assumed null, i.e. no data drop nor corruption in the link.

```json
{
    "links_characteristics": [
        {
            "from": "substation_1",
            "to": "ARP_1",
            "delay_function": {
                "type": "fixed",
                "delay": 0.1
            }
        }
    ]
}
```

Characteristics can also be specified for all links of the same type (i.e. same "fromtype" **and** "totype") as shown below.

```json
{
    "links_characteristics_by_link_type": [
        {
            "fromtype": "RTU",
            "totype": "ARP",
            "drop_function": {
                "type": "fixed",
                "value": false
            },
            "corruption_functions": [
                {
                    "type": "RandomNoiseMeasurementCorruption",
                    "likelihood": 0.01,
                    "noise_min": -0.01,
                    "noise_max": 0.01
                }
            ]
        }
    ]
}
```

This example sets the characteristics of all links that go from a node with type "RTU" to a node with type "ARP" (and not the other way around). Characteristics given for an individual node (i.e. through the field "link_characteristics") have priority over the ones given for all links of the same type (i.e. through the filed "links_characteristics_by_link_type").

At this stage, relatively few delay/drop/corruption functions are implemented, additional delay and drop functions can be implemented [here](/Orchestrator/InformationFlowModel/CommunicationElements.cpp), and corruption functions [here](/Orchestrator/InformationFlowModel/CorruptionFunctions.h)

Node characteristics can be specified in the same way:

```json
{
    "nodes_characteristics": [
        {
            "node": "substation_1",
            // [...] characteristics
        }
    ],
    "nodes_characteristics_by_node_type": [
        {
            "type": "ARP",
            // [...] characteristics
        }
    ],
}
```

### 4.4.3. Special node types

The type of a node can be any valid string, however, the following node types have additional functionalities:
- RTU
- ARP
- SCADA

RTUs, ARPs, and the SCADA node form a chain of elements that allows for the handling of general interrogations (GI, "contrôle général" or CG in French). A GI is a request that is automatically sent from the SCADA to one of its ARPs (resp. from an ARP to one of its RTUs) whenever communication is restored between the two elements. When an RTU or ARP receives a GI, it sends back the most recent information it has to the SCADA.

Therefore, nodes which are typed as "RTU" or "ARP" will store all measurements that pass through them (actually, they only store TSes, measurements that are published on change, TMs, i.e. measurements that are published periodically are out-of-scope of the GI functionality), keeping only the most up-to-date values (based on the time_sent of the measurements), and resend them to the SCADA when they receive a GI.

The notion of an "available" communication channel between two elements is not obvious to define, especially when modelling communications with an information flow model instead of a detailed communication simulator. What has been defined for now is that a communication element (node or link) is available or not depending on its drop function (element marked unavailable when drop probability > 99%). A communication channel between two elements (defined in the c++ code as a "MonitoredPath") is defined as available when all its elements (needed to go from the first element to the second and back, cf a ping request) are available. MonitoredPaths are automatically created between every RTU and the closest ARP (or SCADA if there is no ARP between the RTU and the SCADA), and between every ARP and the SCADA. Whenever a MonitoredPath becomes available, a GI is automatically sent along this path. A GI can also be sent on demand with the "general_interrogation" command (see [4.3.10](#4310-general-interrogation)).


## 4.5. Dynawo outputs

The configuration of Dynawo outputs is split in two files: one for the outputs that are sent to the game master (game_master_outputs_file) and one for the outputs that are sent to the SCADA (scada_outputs_file). Game master outputs are sent directly to the game master, while SCADA outputs are first sent through the information flow model where they are delayed/dropped/corrupted.

Dynawo game master outputs are listed as:

```json
[
    {
        "id": "U_B1",
        "dynawo_id": "NETWORK_B1_Upu_value",
        "topic": "substation_1"
    }
]
```

The fields are:
- id: name of the variable in the simulation
- dynawo_id: name of the variable in dynawo (curve name in Dynawo = model_name + '_' + variable_name)
- topic: topic to which publish the variable to when it is updated

Game master outputs are periodically published as

```json
{"U_B1": 1.02}
```

on the topic GameMaster.topic. See the section on the orchestrator [broker](#5-connection-to-the-orchestrator-broker) for more info about publications and subscriptions.

***NOTE:*** in NATS, the dot (".") symbol is used to structure topics (e.g. GameMaster.substation_1), topic names should thus be sanitised to not include dots (and definitively not start/end with a dot). This is done automatically in the orchestrator, by replacing dots (".") by underscores ("_").

Dynawo SCADA outputs are listed

```json
[
    {
        "id": "U_B1",
        "dynawo_id": "NETWORK_B1_Upu_value",
        "topic": "substation_1",
        "source": "substation_1",
        "destination": "CC"
    }
]
```

The fields are the same as for game master outputs (*Note: this might change in the near future*), with the addition of:
- source: name of the source node (from the [cyber configuration](#44-cyber-configuration)) from which the information will be sent
- destination: name of the destination node

Also, the optional field "tase2" (string) can be set for any SCADA output. If it is set, a tase2 field with tase2 data (validity, cause, etc.) will be added on top of the default format.

The fields listed above are the only fields read by the orchestrator, but other fields might be read by other modules. Refer to the game master and SCADA documentation for more info.

The following python [script](/tools/dynawo_toolbox/src/main_dynawo_outputs_config_generator.py) can be used to generate the Dynawo output files. It also generates the associated Dynawo crv file (at this stage, Dynawo only publishes the variables listed in the crv file, dynawo outputs whose dynawo_id is not included in the crv file will thus not be published).

## 4.6. Asset simulator configuration

The asset simulator configuration file contains a list of assets to be simulated and their properties, e.g.

```json
[
    {
        "type": "Recloser",
        "line_name": "L4032-4042",
        "opening_times": [5.1],
        "closing_times": [5.4]
    },
    {
        "type": "SubstationAlarm",
        "location": "S_4011",
        "substation_name": "S_4011",
        "topic": "S_4011",
        "destination": "CC"
    }
]
```

Currently, the following assets can be modelled in the asset simulator

### 4.6.1 Recloser

An asset that emulates Dynawo timeline events caused by line faults. It is meant to replace the actual fault model when using a Dynawo tool (like DynaWaltz) that doesn't support fast timescales.

### 4.6.2 Substation alarm system

Asset that notifies the Game master and SCADA when an operator enters the substation. This is done by emitting a MeasurementSent (from "location" to "destination") and an ActualMeasurement with ID "operator_in_'substation_name'".


# 5. Connection to the orchestrator broker

Exchanges of information between the orchestrator and external modules (Game master, SCADA, automata) are done through a single broker. This broker is a NATS server, which means that data exchanges are all done via publication and subscriptions to "topics". The orchestrator publishes on the following topics:

- GameMaster."topic": [Dynawo outputs](#45-dynawo-outputs) for the game master ("topic" is to be replaced by the topic of the Dynawo output). Published in the format below
```json
{"id": 1.02}
```
- HMI."destination"."topic": [Dynawo outputs](#45-dynawo-outputs) for the SCADA ("destination" and "topic" are to be replaced by the destination and topic of the Dynawo output). Publications are pushed either in the default format:
```json
{
    "id": "id",
    "value": 1.02,
    "time_sent": 1,
    "time_received": 1.01
}
```
Or with an addendum, if a "tase2" field is given the scada_outputs.json file:
```json
{
    "id": "id",
    "value": 1.02,
    "time_sent": 1,
    "time_received": 1.01,
    "tase2": {
        "tase2_id": "tase2_id",
        "cause": 1,  // 1 periodic (for TM) or 3 spontaneous (for TS)
        "validity": 0,
        "operatorBlocked": false,
        "ts": 1754469097,
        "tfos": "111110011101111011100100"
    }
}
```
- Acknowledgement."destination"."topic": acknowledgements of the controls sent by "destination" (see [5.2](#52-control-acknowledgements-and-options)). Published in the format below (id and value are those of the acknowledged control, time_sent is the time the ack is sent, i.e. the time the control reached its destination):
```json
{
    "control_uid": 42,
    "id": "id",
    "value": 1,
    "control_time_sent": 10.0,
    "time_sent": 10.05,
    "time_received": 10.1
}
```
- stop: stop message to signal the end of the simulation
- time: current time of the simulation (published as string, updated at each Dynawo iteration). This is mostly meant for the game master, as the SCADA can guess the time from the value of the "time_received" field.
- Dynawo.Timeline: Dynawo timeline events sent one by one in JSON format
- Dynawo.Constraints: Dynawo constraints events sent one by one in JSON format

The orchestrator also listen to the following topics:

- GameMasterControl.>: to send controls from the GameMaster. Can either be in the form ```[{"key": value}, ...]```, or formatted as a [scenario json](#43-scenario-file). The suffix is used to define the source of the command, i.e. a trainer could publish on GameMasterControl.Trainer
- HMIControl.>: to send control signals from the SCADA. Formatted in the form ```[{"key": value}, ...]```, or in TC/TVC format, or formatted as a [scenario json](#43-scenario-file). The suffix is used to define the source of the command, i.e. an automaton could publish on HMIControl.automaton_name

For both topics, it replies with "OK" if the control was correctly formatted and could be implemented, else it replies with some error message

## 5.1. Connection of external automata

External automata can be connected to the broker similarly to the HMI, i.e. they should subscribe to the HMI."destination"."topic", where "destination" should be replaced by the name of the node where the automaton is installed, and "topic" by the topic of the Dynawo outputs of interest (or * to subscribe to all topic). Optionally, it should also subscribe to the topic "stop" to know when the simulation is interrupted. Finally, the automaton should publish to "HMIControl" when it is activated. A very simple example of automaton is shown [here](/Orchestrator/automata/tcp_blocker.py).

## 5.2. Control acknowledgements and options

**Acknowledgement.** Whenever a control reaches its destination (ControlReceived), the information flow model automatically sends an acknowledgement (AcknowledgementSent, then AcknowledgementReceived) from the control's destination back to its source, along the reversed path of the control. The acknowledgement crosses the information flow model like a control (delay, drop, and control corruption functions apply), so it is lost if the control or the acknowledgement is dropped. Acknowledgements are published on Acknowledgement."destination"."topic" (destination = sender of the control), forwarded to Cycosim (type "AcknowledgementReceived") when their path enters a Cycosim node, and logged in the AcknowledgementSent/AcknowledgementReceived tables.

**Control uid.** Each control gets a unique identifier, `control_uid`, carried by its acknowledgement (as id and time_sent are not unique, e.g. two controls sent in the same time step). It is returned in the reply to the HMIControl request (`{"status": "OK", "control_uid": 42}`), so that the sender can match the acknowledgement published later, and is logged in the control and acknowledgement tables.

**Control options.** A control sent on HMIControl.> (or by Cycosim) accepts two optional boolean fields:
```json
{"id": "PL1_state", "value": 0, "with_fast_TS": true, "real_time_critical": true}
```
- `with_fast_TS`: when the control reaches its destination, the paired state output (the publish_on_change [SCADA output](#45-dynawo-outputs) with the same id as the control) is returned at once with the commanded value, from the control's destination to the original sender of the control only, as an ordinary measurement (it crosses the information flow model). The other modules still receive the TS at the next Dynawo step, when the simulator publishes it.
- `real_time_critical`: the acknowledgement of the control must not wait for the event queue (which may lag behind real time under heavy load). The control itself still goes through the normal event queue. The control is timestamped from the real-time clock and the information flow model computes at once the control and its acknowledgement (delay, drop and corruption), from the thread that received the control. The acknowledgement is returned directly to the caller, in the reply to the HMIControl request (Cycosim: queued for the next synchronisation), its delay incorporated in its time_received: the caller is responsible for waiting until then. The acknowledgement is not published on the Acknowledgement topic, only logged. Reply example (`"acknowledgement": null` if the control or its acknowledgement is dropped):
```json
{
    "status": "OK",
    "control_uid": 42,
    "acknowledgement": {
        "control_uid": 42,
        "id": "PL1_state",
        "value": 0,
        "source": "RTU_1",
        "destination": "CC",
        "control_time_sent": 10.0,
        "time_sent": 10.05,
        "time_received": 10.1,
        "delay": 0.1
    }
}
```

# 6. Replay functionality

Simulation can be replayed via

```bash
./orchestrator_exec --replay config.toml sim_2025_07_29_11_50_27
```

where sim_2025_07_29_11_50_27 is the name of the simulation to replay. This launches a command line interface allowing the user to replay a simulation, jump to a particular time, etc.

The replay works by reading replaying the events logged in the ClickHouse database.


# 7. Troubleshooting

On headless servers, running the mock-up Qt HMIs might require

```bash
sudo apt install libxcb-cursor0
```
