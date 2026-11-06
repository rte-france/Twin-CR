#!/usr/bin/env bash
#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

#
# Periodically syncs the given branch with an upstream branch (default: merges origin/main into rwth/dev).
# Designed for long-lived branches that should regularly integrate the latest main changes.

set -euo pipefail

usage() {
  cat <<'EOF'
Usage: auto_rebase.sh [--branch <branch>] [--upstream <upstream>] [--interval <seconds>] [--repo <path>]

Defaults:
  --branch   rwth/dev        # target branch to keep up to date
  --upstream origin/main     # upstream branch to rebase onto
  --interval 600             # seconds between attempts (10 minutes)
  --repo     current dir     # repository to operate on
EOF
}

branch="rwth/dev"
upstream="origin/main"
interval=600
repo="$(pwd)"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --branch)
      branch="$2"
      shift 2
      ;;
    --upstream)
      upstream="$2"
      shift 2
      ;;
    --interval)
      interval="$2"
      shift 2
      ;;
    --repo)
      repo="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ ! -d "$repo/.git" ]]; then
  echo "Repository path '$repo' does not contain a .git directory" >&2
  exit 1
fi

cd "$repo"

while true; do
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] sync cycle started"

  git fetch --all --prune

  if ! git rev-parse --verify "$branch" >/dev/null 2>&1; then
    echo "Branch '$branch' not found; sleeping $interval seconds" >&2
    sleep "$interval"
    continue
  fi

  if ! git rev-parse --verify "$upstream" >/dev/null 2>&1; then
    echo "Upstream '$upstream' not found; sleeping $interval seconds" >&2
    sleep "$interval"
    continue
  fi

  if ! git diff --quiet --stat; then
    echo "Working tree dirty; please stash/commit changes before running auto rebase" >&2
    exit 1
  fi

  current_branch="$(git symbolic-ref --short HEAD)"
  if [[ "$current_branch" != "$branch" ]]; then
    git checkout "$branch"
  fi

  if git merge-base --is-ancestor "$upstream" "$branch"; then
    echo "Branch already up to date with $upstream"
  else
    if git merge --no-ff "$upstream"; then
      echo "Merge from $upstream succeeded"
    else
      echo "Merge failed; resolving conflicts required. Exiting." >&2
      exit 1
    fi
  fi

  git checkout "$current_branch" >/dev/null 2>&1 || true

  echo "Sync cycle finished. Sleeping $interval seconds..."
  sleep "$interval"
done