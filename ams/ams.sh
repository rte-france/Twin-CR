#!/usr/bin/env bash
#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#
# AMS: (1) create .venv_ams + install dynagnn-ams (from GitHub) / torch for --device
#      (2) run dynagnn-ams with given args
# Optional: AMS_TORCH_CUDA_INDEX=https://download.pytorch.org/whl/cu124
# Optional: pass --models-dir /path/to/models (or set AMS_MODELS_DIR in cfg.sh)
#
# Call from your example directory so relative DSL/IIDM/DYD paths resolve correctly:
#   ../../../../ams/ams.sh Network.dsl Network.xiidm Network.dyd \
#     --network NetworkName --epsilon 5 --device mps

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$SCRIPT_DIR/.venv_ams"
DEVICE_MARKER="$VENV/.ams_device"
TORCH_CUDA_INDEX="${AMS_TORCH_CUDA_INDEX:-https://download.pytorch.org/whl/cu124}"

_is_py310() {
	"$1" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 10) else 1)' 2>/dev/null
}

# Parse --device from args (still forwarded to dynagnn-ams).
DEVICE=auto
prev=""
for arg in "$@"; do
	if [ "$prev" = "--device" ]; then
		DEVICE="$arg"
		prev=""
		continue
	fi
	case "$arg" in
		--device=*) DEVICE="${arg#--device=}" ;;
		--device) prev="--device" ;;
	esac
done
DEVICE="$(printf '%s' "$DEVICE" | tr '[:upper:]' '[:lower:]')"
case "$DEVICE" in
	auto|cpu|mps|cuda|cuda:*) ;;
	*)
		echo "[ams] Unknown --device '$DEVICE' (use auto, cpu, mps, cuda, or cuda:N)" >&2
		exit 1
		;;
esac

_install_torch_for_device() {
	local kind="$1"
	case "$kind" in
		cpu)
			echo "[ams] Installing PyTorch CPU wheels…"
			uv pip install --python "$VENV" --force-reinstall \
				torch --index-url https://download.pytorch.org/whl/cpu
			;;
		cuda|cuda:*)
			echo "[ams] Installing PyTorch CUDA wheels from ${TORCH_CUDA_INDEX}…"
			uv pip install --python "$VENV" --force-reinstall \
				torch --index-url "$TORCH_CUDA_INDEX"
			;;
		mps|auto)
			# Default macOS/Linux PyPI torch: includes MPS on Apple Silicon.
			echo "[ams] Installing default PyTorch wheels (MPS-capable on macOS)…"
			uv pip install --python "$VENV" --force-reinstall torch
			;;
	esac
}

_install_package() {
	uv pip install --python "$VENV" \
		"dynagnn-ams @ git+https://github.com/SPS-L/DYNAGNN.git#subdirectory=AMS"
}

NEED_BOOTSTRAP=0
if [ ! -x "$VENV/bin/dynagnn-ams" ] || ! _is_py310 "$VENV/bin/python"; then
	NEED_BOOTSTRAP=1
fi
NEED_TORCH=0
if [ "$NEED_BOOTSTRAP" -eq 1 ] || [ ! -f "$DEVICE_MARKER" ] || [ "$(cat "$DEVICE_MARKER")" != "$DEVICE" ]; then
	NEED_TORCH=1
fi

# --- 1) venv that can run dynagnn-ams ---
if [ "$NEED_BOOTSTRAP" -eq 1 ]; then
	rm -rf "$VENV"
	command -v uv >/dev/null 2>&1 || { echo "[ams] Missing dependency: uv (https://github.com/astral-sh/uv). Please install it and re-run." >&2; exit 1; }
	export PATH="${HOME}/.local/bin:${PATH}"
	uv venv "$VENV" --python 3.10
	_install_torch_for_device "$DEVICE"
	_install_package
	printf '%s\n' "$DEVICE" >"$DEVICE_MARKER"
elif [ "$NEED_TORCH" -eq 1 ]; then
	export PATH="${HOME}/.local/bin:${PATH}"
	_install_torch_for_device "$DEVICE"
	# Refresh package so torch/device changes stay aligned with dynagnn-ams deps.
	_install_package
	printf '%s\n' "$DEVICE" >"$DEVICE_MARKER"
fi

# --- 2) run AMS (clear conda lib paths that can segfault the venv) ---
# Keep the caller's cwd so relative DSL/IIDM/DYD paths work from example folders.
echo "[ams] Running dynagnn-ams with $($VENV/bin/python -c 'import sys; print(sys.version.split()[0])') (device=$DEVICE)…"
export PYTHONUNBUFFERED=1
env -u DYLD_LIBRARY_PATH -u DYLD_FALLBACK_LIBRARY_PATH -u LD_LIBRARY_PATH \
	-u PYTHONPATH -u PYTHONHOME \
	PYTHONUNBUFFERED=1 \
	"$VENV/bin/dynagnn-ams" "$@"
echo "[ams] Done."
