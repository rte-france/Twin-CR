# AMS (Adaptive Model Simplification)

Wrapper around [`dynagnn-ams`](https://github.com/SPS-L/DYNAGNN/tree/main/AMS) that bootstraps a Python 3.10 venv, installs PyTorch for the requested `--device`, and runs AMS on a network case.

For full package docs (CLI, custom checkpoints, programmatic API, pipeline), see [SPS-L/DYNAGNN — AMS](https://github.com/SPS-L/DYNAGNN/tree/main/AMS).

## Prerequisites

- Python 3.10 available on the machine (`uv` will create the venv; `uv` is installed automatically if missing)
- Network access on first run (installs `dynagnn-ams` from GitHub and PyTorch wheels)

## Usage in an example

Run AMS from your example directory (so relative paths to `.dsl` / `.xiidm` / `.dyd` resolve).
Set `BASE_PATH` relative to this script (repo root), or set it yourself if the checkout folder is not four levels above the example:

```bash
BASE_PATH="$(cd "$(dirname "$0")"/../../../.. && pwd)"
# Or: BASE_PATH=/path/to/this/repo

"$BASE_PATH/ams/ams.sh" Nordic.dsl Nordic.xiidm Nordic.dyd \
	--network Nordic --epsilon 5 --device auto
```

The Nordic example keeps `cfg.sh` unchanged by default (NRT). To run AMS before configuration, use the optional script:

```bash
./cfg_ams.sh
```

### Arguments

| Argument | Description |
| --- | --- |
| `Network.dsl` | Scenario DSL file |
| `Network.xiidm` | Network IIDM file |
| `Network.dyd` | Dynawo DYD file |
| `--network NAME` | Network / model family name (e.g. `Nordic`) |
| `--epsilon N` | AMS epsilon parameter |
| `--device DEVICE` | Compute device: `auto`, `cpu`, `mps`, `cuda`, or `cuda:N` |

### Optional

- `--models-dir /path/to/models` — use your own checkpoints instead of the defaults
- `AMS_TORCH_CUDA_INDEX` — override the CUDA PyTorch index URL (default: `https://download.pytorch.org/whl/cu124`)

## What the script does

1. Creates `ams/.venv_ams` (Python 3.10) on first use, or when the device changes
2. Installs a device-matched PyTorch build and `dynagnn-ams`
3. Runs `dynagnn-ams` with your arguments, keeping the caller's working directory so relative input paths work

## Device tips

- macOS Apple Silicon: `--device mps` (or `auto`)
- CPU-only: `--device cpu`
- NVIDIA GPU: `--device cuda` (or `cuda:0`, …)
