#!/bin/bash
#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

# Set up (or update, after pulling develop) a Twin-CR development environment, following the README.
# Only warnings, .env changes and errors are printed, everything else goes to the log file.

set -o pipefail

CORE_DIR=$(cd "$(dirname "$0")" && pwd)
cd "$CORE_DIR" || exit 1

ALL_STEPS="proxy prerequisites precommit secrets garage env dynawo private build argus devenvs examples upload"
STEPS=${ALL_STEPS% upload}  # upload only with --upload
RTE=false
ARGUS=false
UPDATE_DYNAWO=false
FORCE_EXAMPLES=false
COMPOSE_DIR="$CORE_DIR"
EXAMPLES_DIRS="$CORE_DIR/docs/orchestrator/examples"
GARAGE_ENV_FILES=""
LOG_FILE=${SETUP_LOG:-$CORE_DIR/logs/setup.$(date +%Y%m%d.%H%M%S).log}

usage() {
    cat <<EOF
Usage: $0 [options]

Steps (in order): $ALL_STEPS
  proxy         check proxy need
  prerequisites check the required tools
  precommit     install pre-commit and its git hook
  secrets       generate the dev secrets required by docker compose (Garage RPC secret and tokens, Keycloak
                admin password) if missing, then write them in .env (if it exists, otherwise the env step does)
  garage        generate the Garage S3 credentials (configurator_server/init_garage.sh) if needed
  env           create/update .env from .env-example (and the service .env files, if they exist)
  dynawo        check simulators.zip (download the public one if missing) and the Dynawo version of its
                extraction in simulators/
  private       (--rte) check the private argus-backends files
  build         docker compose --profile hmi build (+ --profile argus with --argus)
  argus         Linux + --argus: build the Argus AppImage, otherwise install the native (pnpm) dependencies
  devenvs       uv sync the configurator_client (used to upload contexts)
  examples      generate the example mappings (cfg.sh)
  upload        (--upload) upload the examples to Garage (uv run upload_context), only needed without the lobby

Options:
  --rte              RTE setup: private argus-backends variant and private dynawo-rte (without it, the
                     public variant is only set when the private argus-backends files are missing)
  --argus            Linux only: also build the argus compose profile and the Argus AppImage
  --update-dynawo    Reinstall simulators/dynawo (and dynawo-rte with --rte) from simulators.zip if not the
                     required build (without --rte, an outdated simulators.zip is downloaded again)
  --force-examples   Regenerate the example mappings even if their inputs did not change
  --only STEPS       Comma separated list of steps to run (e.g. --only env,dynawo)
  --skip STEPS       Comma separated list of steps to skip (e.g. --skip build)
  --compose-dir DIR  Directory docker compose is run from (default: Twin-CR)
  --examples DIR     Also run DIR/*/cfg.sh (and upload DIR/*/config.toml with --upload), can be repeated
  --upload           Also upload the examples to Garage (context id = example directory name)
  --garage-env FILE  Also write the dev secrets and the Garage credentials in FILE (e.g. .env-tests in CI), if
                     empty there, can be repeated
  -h, --help         Show this help

Log file: logs/setup.<date>.log (or \$SETUP_LOG)
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --rte) RTE=true ;;
        --argus) ARGUS=true ;;
        --update-dynawo) UPDATE_DYNAWO=true ;;
        --force-examples) FORCE_EXAMPLES=true ;;
        --only) STEPS=$(echo "$2" | tr ',' ' '); shift ;;
        --skip) for s in $(echo "$2" | tr ',' ' '); do STEPS=$(echo " $STEPS " | sed "s/ $s / /"); done; shift ;;
        --compose-dir) COMPOSE_DIR=$(cd "$2" && pwd) || exit 1; shift ;;
        --examples) EXAMPLES_DIRS="$EXAMPLES_DIRS $(cd "$2" && pwd)" || exit 1; shift ;;
        --upload) STEPS="$STEPS upload" ;;
        --garage-env) GARAGE_ENV_FILES="$GARAGE_ENV_FILES $2"; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option $1"; usage; exit 1 ;;
    esac
    shift
done
for s in $STEPS; do
    case " $ALL_STEPS " in *" $s "*) ;; *) echo "Unknown step $s"; usage; exit 1 ;; esac
done


# Run directly inside a parent project (e.g. TwinEU-RTE) that has its own setup.sh calling this one with --compose-dir
if [ "$COMPOSE_DIR" = "$CORE_DIR" ] && [ -x "$CORE_DIR/../setup.sh" ] && [ -t 0 ]; then
    echo "$(cd "$CORE_DIR/.." && pwd)/setup.sh exists: it should be used instead of this one" \
         "(docker compose run from the parent directory, with its own options and examples)."
    read -r -p "Continue with Twin-CR/setup.sh only? [y/N] " answer
    case "$answer" in
        [yY]*) ;;
        *) echo "Aborted, run ../setup.sh instead"; exit 1 ;;
    esac
fi

mkdir -p "$(dirname "$LOG_FILE")"
: >> "$LOG_FILE"

# ---------------------------------------------------------------- output helpers
if [ -t 1 ]; then
    C_RED=$'\033[31m'; C_YELLOW=$'\033[33m'; C_BLUE=$'\033[34m'; C_BOLD=$'\033[1m'; C_RESET=$'\033[0m'
fi
N_WARN=0
N_ERR=0

log() { echo "$*" >> "$LOG_FILE"; }
step() { echo "${C_BOLD}==> $*${C_RESET}"; log "==> $*"; }
info() { echo "${C_BLUE}INFO${C_RESET}  $*"; log "INFO: $*"; }
warn() { echo "${C_YELLOW}WARN${C_RESET}  $*"; log "WARN: $*"; N_WARN=$((N_WARN + 1)); }
err() { echo "${C_RED}ERROR${C_RESET} $*"; log "ERROR: $*"; N_ERR=$((N_ERR + 1)); }

# Stop on Ctrl+C: docker compose (and others) handle SIGINT and exit with an error code, which bash would
# otherwise treat as a failed command and go on with the next step
trap 'echo; err "Interrupted, see $LOG_FILE"; rm -f "$LOG_FILE.counts"; exit 130' INT

# run "description" cmd args...: run a command with its output in the log, print the log tail on failure
run() {
    local desc=$1 start; shift
    log "\$ $*"
    start=$(wc -l < "$LOG_FILE")
    if "$@" >> "$LOG_FILE" 2>&1; then
        return 0
    fi
    local output
    output=$(tail -n +$((start + 1)) "$LOG_FILE" | grep -v '^[[:space:]]*$' | tail -n 20 | sed 's/^/      /')  # docker separates its error lines with blank lines
    err "$desc failed, last lines of $LOG_FILE:"
    echo "$output"
    return 1
}

has_step() { case " $STEPS " in *" $1 "*) return 0 ;; esac; return 1; }
has_cmd() { command -v "$1" > /dev/null 2>&1; }
compose() { (cd "$COMPOSE_DIR" && docker compose "$@"); }
docker_running() { has_cmd docker && docker info > /dev/null 2>&1; }

PYTHON=python3
env_sync() {
    # Forward env_sync.py output: DEBUG lines to the log only
    local line status
    "$PYTHON" "$CORE_DIR/tools/env_sync.py" "$@" 2>&1 | {
        while IFS= read -r line; do
            case "$line" in
                WARN:*) warn "${line#WARN: }" ;;
                INFO:*) info "${line#INFO: }" ;;
                ERROR:*) err "${line#ERROR: }" ;;
                *) log "$line" ;;
            esac
        done
        echo "$N_WARN $N_ERR" > "$LOG_FILE.counts"
    }
    status=$?
    # The pipe runs in a subshell: get the counters back
    read -r N_WARN N_ERR < "$LOG_FILE.counts"; rm -f "$LOG_FILE.counts"
    return $status
}
env_get() { "$PYTHON" "$CORE_DIR/tools/env_sync.py" get "$1" "$2"; }

OS=$(uname -s)
echo "Log file: $LOG_FILE"
log "setup.sh $(date) on $OS, steps: $STEPS, rte=$RTE argus=$ARGUS compose dir: $COMPOSE_DIR"

# Tools from mise.toml (installed by the prerequisites step) on the PATH for all the steps.
# Without mise (e.g. CI running only some steps), the tools already on the PATH are used.
mise_env() { has_cmd mise && eval "$(mise env -s bash -C "$CORE_DIR" 2>> "$LOG_FILE")"; }
# Before mise_env changes the PATH: is mise activated in the user's shell (mise activate sets MISE_SHELL) or its shims on the PATH?
MISE_ACTIVATED=false
if [ -n "$MISE_SHELL" ] || case ":$PATH:" in *"/mise/shims:"*) true ;; *) false ;; esac; then MISE_ACTIVATED=true; fi
mise_env

# Line to add to the user's shell configuration to use the mise.toml tools outside setup.sh
mise_activation_hint() {
    local mise_bin shell
    mise_bin=$(command -v mise | sed "s|^$HOME/|~/|")
    shell=$(basename "${SHELL:-bash}")
    case "$shell" in
        zsh) echo "echo 'eval \"\$($mise_bin activate zsh)\"' >> ~/.zshrc" ;;
        fish) echo "echo '$mise_bin activate fish | source' >> ~/.config/fish/config.fish" ;;
        *) echo "echo 'eval \"\$($mise_bin activate bash)\"' >> ~/.bashrc" ;;
    esac
}
log "Twin-CR $(git -C "$CORE_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null) $(git -C "$CORE_DIR" rev-parse --short HEAD 2>/dev/null)"

# ---------------------------------------------------------------- prerequisites
# Garage credentials have to be generated (needs docker)
garage_init_needed() {
    [ ! -f configurator_server/credentials.txt ] && { [ -z "$(env_get .env AWS_ACCESS_KEY_ID)" ] || [ -n "$GARAGE_ENV_FILES" ]; }
}

# Test proxy need
step_proxy() {
    step "Checking internet access"
    local test_url="https://www.google.com" proxy=""
    if [ -n "$http_proxy" ] || [ -n "$https_proxy" ] || [ -n "$HTTP_PROXY" ] || [ -n "$HTTPS_PROXY" ]; then
        proxy="${https_proxy:-${HTTPS_PROXY:-${http_proxy:-$HTTP_PROXY}}}"
        if [ -z "$no_proxy" ] && [ -z "$NO_PROXY"]; then
            warn "HTTP/HTTPS proxy is configured, but no_proxy is not set. Internal addresses may fail to resolve."
        fi
    fi
    if curl -Is --max-time 5 "$test_url" > /dev/null 2>&1; then
        log "Internet access OK${proxy:+ through the proxy $proxy}"
    elif [ -n "$proxy" ]; then
        err "No internet access through the proxy $proxy: check the http(s)_proxy variables"
    else
        err "No internet access and no proxy defined: set http_proxy/https_proxy if you are behind a proxy"
    fi
}

# The tools of mise.toml are installed by mise, only docker and basic system tools are checked.
# The run stops if one is missing.
step_prerequisites() {
    step "Checking prerequisites"
    if ! has_cmd mise; then
        export PATH="$HOME/.local/bin:$PATH"
        if ! has_cmd mise; then
            case "$OS" in
                MINGW*|MSYS*|CYGWIN*)
                    # The mise.run installer only supports Mac and Linux
                    err "mise is required (it installs the tools of mise.toml), install it following" \
                        "https://mise.jdx.dev/installing-mise.html (Windows section) and rerun"
                    return 1 ;;
            esac
            info "Installing mise in ~/.local/bin (https://mise.jdx.dev), it installs the tools of mise.toml"
            run "mise installation" bash -c "curl -fsSL https://mise.run | sh"
        fi
    fi
    if has_cmd mise && run "mise trust" mise trust "$CORE_DIR/mise.toml" && run "mise install" mise install -C "$CORE_DIR"; then
        mise_env
    fi

    local cmd
    for cmd in git curl unzip; do
        has_cmd "$cmd" || err "$cmd is required but not installed"
    done

    # Docker only for the steps using it
    if has_step build || has_step upload || { has_step argus && $ARGUS && [ "$OS" = "Linux" ]; } \
        || { has_step garage && garage_init_needed; }; then
        local version
        version=$(docker compose version --short 2> /dev/null | sed 's/^v//')
        if ! docker_running; then
            err "docker is not installed or not running (start it, or --skip the build/garage/upload steps)"
        elif ! printf '2.20.0\n%s\n' "${version%%-*}" | sort -t. -k1,1n -k2,2n -k3,3n -C; then
            err "docker compose ${version:-v1} is too old, >= 2.20 is required (include is used by the compose files)"
        fi
    fi

    if [ "$OS" = "Darwin" ]; then
        log "Mac: host networking must be enabled in Docker Desktop (Settings -> Resources -> Network) to reach services from the host"
        if [ -n "$(env_get .env DOCKER_DISPLAY 2> /dev/null)" ] && [ ! -d /Applications/Utilities/XQuartz.app ] && [ ! -d /Applications/XQuartz.app ]; then
            warn "DOCKER_DISPLAY is set but XQuartz is not installed (needed by the hmi profile)"
        fi
    fi
}

# ---------------------------------------------------------------- precommit
step_precommit() {
    step "Installing pre-commit"
    run "pre-commit install" pre-commit install
}

# ---------------------------------------------------------------- secrets
# Dev secrets required by the compose files (KEY:FORMAT, 32 random bytes): docker compose refuses to start without them
DEV_SECRETS="GARAGE_RPC_SECRET:hex GARAGE_ADMIN_TOKEN:base64 GARAGE_METRICS_TOKEN:base64 KEYCLOAK_ADMIN_PASSWORD:base64" # gitleaks:allow
DEV_SECRET_ASSIGNMENTS=()  # KEY=VALUE, filled by resolve_dev_secrets

# Each secret is taken from .env (then the --garage-env files) if set there, otherwise generated (once per run)
resolve_dev_secrets() {
    [ ${#DEV_SECRET_ASSIGNMENTS[@]} -gt 0 ] && return 0
    local entry key file value
    for entry in $DEV_SECRETS; do
        key=${entry%%:*}
        value=""
        for file in .env $GARAGE_ENV_FILES; do
            [ -f "$file" ] && value=$(env_get "$file" "$key")
            [ -n "$value" ] && break
        done
        if [ -z "$value" ]; then
            value=$("$PYTHON" -c '
import base64, secrets, sys
raw = secrets.token_bytes(32)
print(raw.hex() if sys.argv[1] == "hex" else base64.b64encode(raw).decode())
' "${entry#*:}") || { err "Could not generate $key"; DEV_SECRET_ASSIGNMENTS=(); return 1; }
        fi
        [ "$GITHUB_ACTIONS" = true ] && echo "::add-mask::$value"  # Hidden from the GitHub Actions logs
        DEV_SECRET_ASSIGNMENTS+=("$key=$value")
    done
}

step_secrets() {
    step "Checking dev secrets"
    resolve_dev_secrets || return 1
    local file
    if [ -f .env ]; then
        env_sync set .env --if-empty "${DEV_SECRET_ASSIGNMENTS[@]}"
    else
        log "No .env yet: the dev secrets are written by the env step"
    fi
    for file in $GARAGE_ENV_FILES; do
        env_sync set "$file" --if-empty "${DEV_SECRET_ASSIGNMENTS[@]}"
    done
}

# ---------------------------------------------------------------- garage
# Garage S3 credentials (configurator_server/credentials.txt, created by init_garage.sh)
CREDENTIALS=configurator_server/credentials.txt
credential() { grep "$1" "$CREDENTIALS" 2> /dev/null | awk '{print $NF}' | head -n 1; }

# Garage alone, in the main compose project (same container as with docker compose up, without needing a full .env).
# Its compose file only reads configurator_server/.env: the dev secrets it requires are passed through the environment.
garage_compose() {
    local project
    project=$(env_get "$COMPOSE_DIR/.env" COMPOSE_PROJECT_NAME 2> /dev/null)
    project=${project:-$(basename "$COMPOSE_DIR" | tr 'A-Z' 'a-z' | tr -cd 'a-z0-9_-')}
    env "${DEV_SECRET_ASSIGNMENTS[@]}" docker compose -p "$project" -f configurator_server/docker-compose-garage.yaml "$@"
}
GARAGE_STATE=""
garage_start() {
    resolve_dev_secrets || return 1
    GARAGE_STATE=$(docker ps -a --filter name=^garage-twincr$ --format '{{.State}}')
    [ "$GARAGE_STATE" = "running" ] || run "Starting garage" garage_compose up -d garage
}
garage_restore() {
    # Leave garage as it was found: running, stopped or absent
    case "$GARAGE_STATE" in
        running) ;;
        "") run "Removing garage" garage_compose rm -sf garage ;;
        *) run "Stopping garage" garage_compose stop garage ;;
    esac
}

init_garage_credentials() {
    if [ -n "$(ls -A configurator_server/garage-data/meta 2> /dev/null)" ]; then
        warn "Garage is already initialised but $CREDENTIALS is missing: create a key with" \
             "'docker exec garage-twincr /garage key create TwinCR' (and allow it on the context-library and archive buckets," \
             "see configurator_server/init_garage.sh), then set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY in .env"
        return 1
    fi
    if ! docker_running; then
        warn "Garage credentials are missing and docker is not running: rerun './setup.sh --only garage,env' with docker started"
        return 1
    fi
    info "Generating Garage S3 credentials (configurator_server/init_garage.sh)"
    garage_start || return 1
    run "init_garage.sh" bash -c "cd configurator_server && ./init_garage.sh"
    local status=$?
    garage_restore
    return $status
}

step_garage() {
    step "Checking Garage credentials"
    if garage_init_needed; then
        init_garage_credentials || return 1
    elif [ ! -f "$CREDENTIALS" ]; then
        log "AWS_ACCESS_KEY_ID already set in .env"
        return 0
    fi
    # The root and service .env files are filled by the env step
    local file
    for file in $GARAGE_ENV_FILES; do
        env_sync set "$file" --if-empty "AWS_ACCESS_KEY_ID=$(credential "Key ID:")" "AWS_SECRET_ACCESS_KEY=$(credential "Secret key:")"
    done
}

# ---------------------------------------------------------------- env
step_env() {
    step "Updating .env files"
    # --rte: private variant. Otherwise keep the user's choice, unless it is private
    # without the private files, which would make the build fail
    local variant
    variant=$(env_get .env ARGUS_BACKENDS_BUILD_VARIANT)
    variant=${variant:-$(env_get .env-example ARGUS_BACKENDS_BUILD_VARIANT)}
    if $RTE; then
        variant=private
    elif [ "$variant" = private ] && [ -n "$(missing_private_files)" ]; then
        variant=public
    fi

    local key_id secret assignment if_empty=()
    key_id=$(credential "Key ID:")
    secret=$(credential "Secret key:")
    # Dev secrets: generated if missing (the secrets step only fills an existing .env)
    resolve_dev_secrets || return 1
    for assignment in "AWS_ACCESS_KEY_ID=$key_id" "AWS_SECRET_ACCESS_KEY=$secret" "${DEV_SECRET_ASSIGNMENTS[@]}"; do
        if_empty+=(--set-if-empty "$assignment")
    done

    # Root .env: the only one used by docker compose. HERGE_URL from the environment (set by TwinEU-RTE/setup.sh)
    # is only written when .env has none
    env_sync sync .env-example .env --backup-dir logs \
        --set "ARGUS_BACKENDS_BUILD_VARIANT=$variant" "${if_empty[@]}" || return 1
    if [ -z "$(env_get .env AWS_ACCESS_KEY_ID)" ]; then
        warn ".env: AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY are empty (needed in MODE=CLICKHOUSE), see configurator_client/README.md"
    fi

    # Service .env files are only used by native (dev) runs: update them only if they exist
    local service
    for service in configurator_client session-manager keycloak; do
        if [ -f "$service/.env" ] && [ -f "$service/.env-example" ]; then
            env_sync sync "$service/.env-example" "$service/.env" --backup-dir logs "${if_empty[@]}"
        fi
    done
}

# ---------------------------------------------------------------- dynawo
. "$CORE_DIR/envs/dynawo.version"
RELEASE_URL="https://github.com/rte-france/Twin-CR/releases/tag/$DYNAWO_RELEASE_TAG"
# Where to get the RTE private files (set by TwinEU-RTE/setup.sh, their location is not public)
DYNAWO_RTE_SOURCE=${DYNAWO_RTE_URL:-the Twin-CR-RTE README}
ARGUS_PRIVATE_SOURCE=${ARGUS_PRIVATE_URL:-the Twin-CR-RTE README}

# Build of the Dynawo install in $1: "<version> rev <hash>", "unknown" if it cannot be read, empty if not installed
dynawo_build() {
    [ -x "$1/dynawo.sh" ] || return 0
    # Read from the (Linux) binary itself since it cannot be run on Mac
    "$PYTHON" -c '
import re, sys
match = re.search(rb"\x00(\d+\.\d+\.\d+)\x00 \(rev:\x00[^\x00]*\x00([0-9a-f]{7,40})\x00", open(sys.argv[1], "rb").read())
print(f"{match.group(1).decode()} rev {match.group(2).decode()}" if match else "unknown")
' "$(ls "$1"/bin/dynawo-[0-9]* 2> /dev/null | head -n 1)" 2> /dev/null || echo unknown
}

fetch_simulators() {
    local token=${GITHUB_TOKEN:-$(env_get .env GITHUB_TOKEN 2> /dev/null)}
    if ! $RTE && [ -z "$token" ] && has_cmd gh; then
        token=$(gh auth token 2> /dev/null) \
            || warn "gh auth token failed (gh not logged in, or too old for 'gh auth token'): downloading without a GitHub token"
    fi
    # --rte: no download, the public dynawo comes with dynawo-rte in the RTE simulators.zip
    run "envs/fetch_simulators.sh" env FETCH_PUBLIC_DYNAWO=$($RTE && echo false || echo true) GITHUB_TOKEN="$token" \
        bash envs/fetch_simulators.sh --force
}

# zip_has ENTRY: simulators.zip has simulators/ENTRY (the session-manager image copies its simulators/ top-level)
zip_has() { unzip -Z1 simulators.zip 2> /dev/null | grep "^simulators/$1/" > /dev/null; }  # not grep -q: with pipefail, unzip fails on SIGPIPE

# check_archive: simulators.zip, which the session-manager image is built from, is there with the expected content
check_archive() {
    if [ ! -f simulators.zip ]; then
        err "simulators.zip is missing (the session-manager image is built from it): put $source in Twin-CR/ and rerun"
    elif ! zip_has dynawo; then
        err "simulators.zip has no simulators/dynawo (the session-manager image needs a simulators/ top-level): put $source in Twin-CR/"
    elif $RTE && ! zip_has dynawo-rte; then
        err "simulators.zip has no simulators/dynawo-rte (public archive?): put $source in Twin-CR/" \
            "and rerun with --update-dynawo"
    else
        log "simulators.zip OK"
    fi
}

# check_build DIR BUILD: compare with $required, $source tells where to get it
check_build() {
    if [ -z "$2" ]; then
        err "$1 is missing: put $source in Twin-CR/ and rerun"
    elif [ "$2" != "$required" ]; then
        err "$1 is $2, $required is required: put the new $source in Twin-CR/" \
            "(replacing any outdated one) and rerun with --update-dynawo"
    else
        log "$1 $2 OK"
    fi
}

step_dynawo() {
    # --rte: both builds come from the dynawo-rte archive, which bundles its public dynawo (same revision)
    local required source build build_rte=""
    if $RTE; then
        required="$DYNAWO_VERSION rev $DYNAWO_RTE_REVISION"
        source="the RTE simulators.zip (with dynawo-rte, see $DYNAWO_RTE_SOURCE)"
    else
        required="$DYNAWO_VERSION rev $DYNAWO_REVISION"
        source="simulators.zip from $RELEASE_URL (downloaded automatically when GITHUB_TOKEN is set in .env)"
    fi
    step "Checking Dynawo (required: $required)"
    build=$(dynawo_build simulators/dynawo)
    if $RTE; then build_rte=$(dynawo_build simulators/dynawo-rte); fi
    if $UPDATE_DYNAWO && [ -n "$build" ] && [ "$build" != "$required" ]; then
        info "Removing simulators/dynawo ($build)"
        rm -rf simulators/dynawo
        build=""
        # Public: the archive it came from is outdated too, download it again
        if ! $RTE && [ -f simulators.zip ]; then
            info "Removing the outdated simulators.zip"
            rm -f simulators.zip
        fi
    fi
    if $UPDATE_DYNAWO && [ -n "$build_rte" ] && [ "$build_rte" != "$required" ]; then
        info "Removing simulators/dynawo-rte ($build_rte)"
        rm -rf simulators/dynawo-rte
        build_rte=""
    fi

    # simulators.zip ((not --rte) downloaded from the public release if missing), extracted where simulators/ lacks it
    if [ ! -f simulators.zip ] || [ -z "$build" ] || { $RTE && [ -z "$build_rte" ]; }; then
        info "Installing Dynawo from Twin-CR/simulators.zip$($RTE || echo " (downloaded from the $DYNAWO_RELEASE_TAG release if missing)")"
        fetch_simulators
        build=$(dynawo_build simulators/dynawo)
        if $RTE; then build_rte=$(dynawo_build simulators/dynawo-rte); fi
    fi

    check_archive
    check_build simulators/dynawo "$build"
    if $RTE; then check_build simulators/dynawo-rte "$build_rte"; fi
}

# ---------------------------------------------------------------- private
# Private argus-backends files (from the Dockerfile) missing in argus-backends/
missing_private_files() {
    local dockerfile=argus-backends/Dockerfile.argus-backends powsybl_version file
    powsybl_version=$(sed -n 's/^ARG POWSYBL_RTE_VERSION=//p' "$dockerfile")
    for file in "jars-powsybl-rte-$powsybl_version.tar" $(sed -n 's/^ADD \(estim-[^ ]*\) .*/\1/p' "$dockerfile"); do
        [ -f "argus-backends/$file" ] || echo "$file"
    done
}

step_private() {
    $RTE || return 0
    step "Checking private argus-backends files"
    local file
    for file in $(missing_private_files); do
        err "argus-backends/$file is missing (RTE private file, see $ARGUS_PRIVATE_SOURCE)"
    done
}

# ---------------------------------------------------------------- build
step_build() {
    local profiles="--profile hmi"
    if $ARGUS; then
        if [ "$OS" = "Linux" ]; then
            profiles="$profiles --profile argus"
        else
            warn "--argus: the argus profile only builds on Linux (the AppImage does not work under emulation), skipped"
        fi
    fi
    step "Building docker images (docker compose $profiles build), this can take a while: tail -f $LOG_FILE"
    run "docker compose build" compose $profiles build
}

# ---------------------------------------------------------------- argus
step_argus() {
    if $ARGUS && [ "$OS" = "Linux" ]; then
        step "Building the Argus AppImage (envs/build_argus_AppImage.sh), this can take a while"
        run "build_argus_AppImage.sh" envs/build_argus_AppImage.sh && info "Argus AppImage available in AppImage/"
        return
    fi
    step "Installing Argus native dependencies"
    run "pnpm install" bash -c "cd argus && pnpm install --frozen-lockfile --config.confirmModulesPurge=false" && log "Run Argus with: cd argus && pnpm tauri dev"
}

# ---------------------------------------------------------------- devenvs
step_devenvs() {
    step "Syncing configurator_client environment"
    run "uv sync (configurator_client)" bash -c "cd configurator_client && uv sync"
}

# ---------------------------------------------------------------- examples
# Signature of an example: its files (size and modification time), the scripts its config.sh runs from Twin-CR
# ($BASE_PATH/...py, e.g. Nordic/add_scada_inputs.py), the dynawo_toolbox sources and installed packages (config.sh
# only creates its venv once, so requirements.txt is not what runs) and the Dynawo builds. Logs and outputs are ignored.
example_signature() {
    "$PYTHON" -c '
import hashlib, os, sys
digest = hashlib.sha256()
for root in sys.argv[1:]:
    walk = [(os.path.dirname(root), [], [os.path.basename(root)])] if os.path.isfile(root) else os.walk(root)
    for path, dirs, files in walk:
        dirs[:] = sorted(d for d in dirs if d not in ("outputs", "execution", "venv", "__pycache__"))
        for name in sorted(files):
            if name.endswith(".log") or name == ".DS_Store":
                continue
            stat = os.stat(os.path.join(path, name))
            digest.update(f"{os.path.relpath(os.path.join(path, name), root)} {stat.st_size} {stat.st_mtime_ns}\n".encode())
print(digest.hexdigest())
' "$1" tools/dynawo_toolbox/src $(sed -n 's|.*\$BASE_PATH/\([^ "]*\.py\).*|\1|p' "$1/config.sh" 2> /dev/null)
    ls tools/dynawo_toolbox/venv/lib/python*/site-packages 2> /dev/null | grep 'dist-info$' | cksum
    dynawo_build simulators/dynawo
    dynawo_build simulators/dynawo-rte
}

step_examples() {
    step "Generating example mappings (cfg.sh)"
    local dir cfg example stamp
    mkdir -p .cache/setup
    for dir in $EXAMPLES_DIRS; do
        for cfg in "$dir"/*/cfg.sh; do
            [ -x "$cfg" ] || continue
            example=$(dirname "$cfg")
            stamp=".cache/setup/cfg.$(echo "$example" | tr '/ ' '__')"
            if ! $FORCE_EXAMPLES && [ -f "$stamp" ] && [ "$(example_signature "$example")" = "$(cat "$stamp")" ]; then
                info "$(basename "$example"): mappings up to date (cached, --force-examples to regenerate)"
                continue
            fi
            info "$(basename "$example"): regenerating mappings"
            rm -f "$stamp"
            # On failure, run reports the error: the other examples are still generated, then setup stops
            run "$cfg" bash -c "cd '$example' && ./cfg.sh" && example_signature "$example" > "$stamp"
        done
    done
}

# ---------------------------------------------------------------- upload
step_upload() {
    step "Uploading the examples to Garage (uv run upload_context)"
    local key_id secret cfg dir
    key_id=$(env_get .env AWS_ACCESS_KEY_ID)
    secret=$(env_get .env AWS_SECRET_ACCESS_KEY)
    if [ -z "$key_id" ] || ! docker_running; then
        err "Upload skipped: it needs the Garage credentials in .env and a running docker"
        return 1
    fi
    garage_start || return 1
    for dir in $EXAMPLES_DIRS; do
        for cfg in "$dir"/*/config.toml; do
            [ -f "$cfg" ] || continue
            run "upload_context $(basename "$(dirname "$cfg")")" \
                env AWS_ACCESS_KEY_ID="$key_id" AWS_SECRET_ACCESS_KEY="$secret" \
                bash -c "cd configurator_client && uv run upload_context '$cfg' '$(basename "$(dirname "$cfg")")'" \
                && info "Uploaded context $(basename "$(dirname "$cfg")")"
        done
    done
    garage_restore
}

# ---------------------------------------------------------------- main
# Stop at the first step with errors: the next ones depend on it (e.g. build on dynawo and private)
for s in $ALL_STEPS; do
    if has_step "$s"; then
        "step_$s"
        if [ $N_ERR -gt 0 ]; then
            echo
            echo "${C_RED}${C_BOLD}Setup stopped at the $s step${C_RESET} ($N_ERR error(s), $N_WARN warning(s)): fix the errors above" \
                 "and rerun (--skip $s to bypass), log: $LOG_FILE"
            exit 1
        fi
    fi
done

echo
echo "${C_BOLD}Setup done${C_RESET} ($N_WARN warning(s)), log: $LOG_FILE"
if ! $MISE_ACTIVATED && has_cmd mise; then
    echo "To also use the mise.toml tools (python, uv, pnpm, etc.) outside setup.sh, activate mise in your shell"
    echo "(https://mise.jdx.dev/getting-started.html#activate-mise), e.g.:"
    echo "  $(mise_activation_hint)"
fi
if has_step build; then
    echo "Next steps:"
    echo "  - start the platform: (cd $COMPOSE_DIR && docker compose up -d)   # docker compose down -v to stop"
    has_step upload || echo "  - without the lobby, upload the examples to Garage: ./setup.sh --only upload"
fi
