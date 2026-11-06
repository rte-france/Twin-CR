Committed copies of the Nordic example's network and game master mapping files.

To refresh them after the example changes, run its `cfg.sh` and copy the results back:

    cd docs/orchestrator/examples/Nordic && ./cfg.sh
    python ../../../../Orchestrator/DSL/tests/resources/check_resources.py --update

The script copies the files and keeps the following fake inputs for purely dynamic Dynawo models (no equipmentId),
appended after the Nordic ones. To add new ones, append them to `game_master_inputs.json` by hand.
CI runs the script without `--update` to check that the resources still match the Nordic example.

```json
[
    {
        "model_lib": "DYNModelRST",
        "equipmentId": null,
        "kind": "U",
        "id": "RST_4011_uNom",
        "factor": 1.0,
        "model": "RST_4011",
        "variable": "uNom",
        "simulator": "dynawo"
    },
    {
        "model_lib": "DYNModelRST",
        "equipmentId": null,
        "kind": "deltaU",
        "id": "RST_4011_deltaU",
        "factor": 1.0,
        "model": "RST_4011",
        "variable": "deltaU",
        "simulator": "dynawo"
    },
    {
        "model_lib": "DYNModelRST",
        "equipmentId": null,
        "kind": "U",
        "id": "RST_4012_uNom",
        "factor": 1.0,
        "model": "RST_4012",
        "variable": "uNom",
        "simulator": "dynawo"
    }
]
```

Then re-run the cases and read the diff before committing any golden that moved.
