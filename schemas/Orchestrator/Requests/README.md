The JSON schemas in this folder describe the orchestrator API. The main entry points are
- Initialisation
  - Topic `Start`: two-step process: first send config with message defined in [start_prepare.json](start_prepare.json), then if successful, start the simulation with message defined in [start_start.json](start_start.json)
- Simulation control
  - Topic `GameMasterControl.<source>` defined in [game_master_control.json](game_master_control.json)
  - Topic `HMIControl.<source>` defined in [hmi_control.json](hmi_control.json)

For all commands, an associated `*-reply.json` schema is also provided to describe the reply that the orchestrator can return. A [python GUI](command_generator.py) is provided to help generating valid commands.
