#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

"""
Keep .env files in sync with their .env-example (standard library only, used by the pre-commit).

    sync EXAMPLE ENV [--set K=V] [--set-if-empty K=V] [--backup-dir DIR]
        Rewrite ENV following the layout of EXAMPLE while keeping the user's values:
            - WARN when a value differs from the example (not for keys left empty in the example, e.g. credentials)
            - WARN + delete when a variable is no longer in the example (COMPOSE_* docker compose settings are kept)
            - INFO + add when a variable is new in the example
        Variables commented out in the example (# KEY=value) are optional: kept if the user set them.
    check
        Fail if a service .env-example declares a variable that is missing from (or differs in) the root
        .env-example, or if a compose file interpolates a variable the root .env-example does not define.
        Tag a service variable with an inline "# [native]" comment when it only applies to native runs.
    set ENV KEY=VALUE... [--if-empty]
        Set variables in ENV in place (uncommenting "# KEY=" lines, appending otherwise), without
        synchronising it with an example (e.g. for .env-tests).
    get ENV KEY
        Print the value of KEY in ENV (empty if absent).

Output lines are prefixed with WARN/INFO/DEBUG/ERROR, setup.sh only shows WARN/INFO/ERROR on the console.
"""

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

ACTIVE_RE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$")
COMMENTED_RE = re.compile(r"^\s*#\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
SECRET_RE = re.compile(r"(^|_)(KEY|SECRET|TOKEN|PASSWORD)(_|$)", re.IGNORECASE)
NATIVE_TAG = "[native]"
KEEP_PREFIXES = ("COMPOSE_",)  # Docker compose settings (COMPOSE_FILE, COMPOSE_PROJECT_NAME...): kept even if not in the example
# ${VAR}, ${VAR:-default}, ${VAR-default}, ${VAR:?err} and $VAR ($$ is an escaped $)
COMPOSE_VAR_RE = re.compile(r"(?<!\$)\$(?:\{([A-Za-z_][A-Za-z0-9_]*)([:?\-+][^}]*)?\}|([A-Za-z_][A-Za-z0-9_]*))")
HOST_VARS = {"HOME", "DISPLAY"}  # Taken from the host environment, not from the .env (X11 of the argus/hmi profiles)


def log(level, msg):
    print(f"{level}: {msg}", flush=True)


def split_value(raw):
    """Split the text after '=' into (value, raw_value, comment_suffix)."""
    stripped = raw.lstrip()
    lead = raw[: len(raw) - len(stripped)]
    if stripped[:1] in ("'", '"'):
        end = stripped.find(stripped[0], 1)
        if end != -1:
            return stripped[1:end], lead + stripped[: end + 1], stripped[end + 1:]
    if stripped.startswith("#"):  # Empty value followed by a comment
        return "", "", (lead or "  ") + stripped.rstrip()
    match = re.search(r"\s+#", stripped)
    raw_value = stripped[: match.start()] if match else stripped.rstrip()
    suffix = stripped[match.start():] if match else ""
    return raw_value.strip(), lead + raw_value, suffix.rstrip()


def split_commented(line):
    """split_value() of a "# KEY=value" line (only called on lines already matched by COMMENTED_RE)."""
    match = COMMENTED_RE.match(line)
    assert match, line
    return split_value(match.group(2))


class EnvFile:
    def __init__(self, path):
        self.path = Path(path)
        self.lines = self.path.read_text().splitlines() if self.path.exists() else []
        self.active = {}  # key -> (value, raw_value, comment_suffix, line index)
        self.commented = {}  # key -> list of raw lines
        self.duplicates = set()
        for i, line in enumerate(self.lines):
            match = ACTIVE_RE.match(line)
            if match and not line.lstrip().startswith("#"):
                key = match.group(1)
                if key in self.active:
                    self.duplicates.add(key)
                self.active[key] = (*split_value(match.group(2)), i)
                continue
            match = COMMENTED_RE.match(line)
            if match:
                self.commented.setdefault(match.group(1), []).append(line)

    def keys(self):
        return set(self.active) | set(self.commented)


def show(key, value):
    if SECRET_RE.search(key) and value:
        return "<hidden>"
    return value if value else "<empty>"


def parse_assignments(items, option):
    result = {}
    for item in items or []:
        if "=" not in item:
            sys.exit(f"ERROR: {option} expects KEY=VALUE, got {item!r}")
        key, value = item.split("=", 1)
        result[key] = value
    return result


def sync(args):
    example = EnvFile(args.example)
    if not example.path.exists():
        log("ERROR", f"{example.path} not found")
        return 1
    user = EnvFile(args.env)
    forced = parse_assignments(args.set, "--set")
    if_empty = parse_assignments(args.set_if_empty, "--set-if-empty")
    name = user.path.name if user.path.parent == Path(".") else str(user.path)

    if not user.path.exists():
        log("INFO", f"{name}: created from {example.path.name}")
    for key in sorted(user.duplicates):
        log("WARN", f"{name}: {key} is defined several times, keeping the last value")

    def resolve(key, example_value):
        """Value to write for key, None to keep the example line as is."""
        current = user.active.get(key)
        value = current[1] if current else None
        if key in forced and (current is None or current[0] != forced[key]):
            log("INFO", f"{name}: {key}={show(key, forced[key])} (set by setup)")
            return forced[key]
        if key in if_empty and (current is None or current[0] == "") and if_empty[key]:
            log("INFO", f"{name}: {key}={show(key, if_empty[key])} (set by setup)")
            return if_empty[key]
        if current is None:
            return None
        if key in forced or key in if_empty:
            return value
        if example_value is None:
            log("DEBUG", f"{name}: {key}={show(key, current[0])} set (optional, commented out in the example)")
        elif example_value == "":
            log("DEBUG", f"{name}: {key} set (empty in example)")
        elif current[0] != example_value:
            log("WARN", f"{name}: {key}={show(key, current[0])} differs from example ({show(key, example_value)})")
        return value

    out = []
    written = set()
    for line in example.lines:
        active = ACTIVE_RE.match(line)
        commented = COMMENTED_RE.match(line)
        if active and not line.lstrip().startswith("#"):
            key = active.group(1)
            example_value, _, suffix = split_value(active.group(2))
        elif commented and commented.group(1) not in example.active and commented.group(1) not in written:
            key = commented.group(1)  # Optional variable, only the first commented example is resolved
            example_value, suffix = None, split_value(commented.group(2))[2]
        else:
            out.append(line)
            continue
        written.add(key)

        # Keep the user's alternative values (commented out lines) above the variable
        current_value = user.active[key][0] if key in user.active else example_value
        for alt in user.commented.get(key, []):
            alt_value = split_commented(alt)[0]
            if alt.strip() != line.strip() and alt_value != current_value and alt not in out:
                out.append(alt)

        value = resolve(key, example_value)
        if value is None:
            if example_value is not None and key in user.commented:
                log("WARN", f"{name}: {key} is commented out in your file but set in the example, kept commented")
                out.extend(c for c in user.commented[key][-1:] if c not in out)
                continue
            if example_value is not None and user.path.exists():
                log("INFO", f"{name}: {key}={show(key, example_value)} added (new in example)")
            out.append(line)
        else:
            out.append(f"{key}={value}{suffix}")

    kept = []
    for key in sorted(set(user.active) - example.keys()):
        if key.startswith(KEEP_PREFIXES):
            log("WARN", f"{name}: {key}={show(key, user.active[key][0])} is not in the example, kept (docker compose setting)")
            kept.append(user.lines[user.active[key][3]])
        else:
            log("WARN", f"{name}: {key}={show(key, user.active[key][0])} removed (no longer in example)")
    if kept:
        out += ["", "# Docker compose settings (not in .env-example)"] + kept
    for key in sorted(set(user.commented) - example.keys()):
        log("DEBUG", f"{name}: commented out {key} dropped (no longer in example)")
    for i, line in enumerate(user.lines):
        stripped = line.strip()
        if stripped.startswith("#") and not COMMENTED_RE.match(line) and stripped not in (l.strip() for l in out):
            log("DEBUG", f"{name}: comment line {i + 1} dropped: {stripped}")

    content = "\n".join(out) + "\n"
    if user.path.exists() and user.path.read_text() == content:
        log("DEBUG", f"{name}: up to date")
        return 0
    if user.path.exists() and args.backup_dir:
        backup_dir = Path(args.backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d.%H%M%S")
        backup = backup_dir / f"{str(user.path).replace('/', '__')}.{stamp}.bak"
        shutil.copy2(user.path.resolve(), backup)
        log("DEBUG", f"{name}: previous version saved to {backup}")
    # Write through symlinks (Twin-CR-RTE/.env -> Twin-CR/.env)
    user.path.resolve().write_text(content)
    log("DEBUG", f"{name}: written")
    return 0


def check(args):
    root = Path(__file__).resolve().parent.parent  # Twin-CR
    root_example = EnvFile(root / ".env-example")
    errors = 0

    def error(msg):
        nonlocal errors
        errors += 1
        log("ERROR", msg)

    for key in sorted(root_example.duplicates):
        error(f".env-example: {key} is defined several times")

    for service_example in sorted(root.glob("*/.env-example")):
        service = EnvFile(service_example)
        rel = service_example.relative_to(root)
        for key, (value, _, suffix, _) in service.active.items():
            if NATIVE_TAG in suffix:
                continue
            if key not in root_example.keys():
                error(f"{rel}: {key} is missing from .env-example "
                      f"(add it there, or tag it '# {NATIVE_TAG}' if it is only used by native runs)")
            elif key in root_example.active and root_example.active[key][0] != value:
                error(f"{rel}: {key}={value!r} differs from .env-example ({root_example.active[key][0]!r}) "
                      f"(align them, or tag it '# {NATIVE_TAG}' if the native value is intentionally different)")

    for compose_file in sorted(root.glob("docker-compose*.yaml")) + sorted(root.glob("*/docker-compose*.yaml")):
        text = "\n".join(l for l in compose_file.read_text().splitlines() if not l.lstrip().startswith("#"))
        for match in COMPOSE_VAR_RE.finditer(text):
            key, modifier = match.group(1) or match.group(3), match.group(2)
            has_default = modifier is not None and modifier.lstrip(":")[:1] in ("-", "+")
            if has_default or key in HOST_VARS or key in root_example.keys():
                continue
            error(f"{compose_file.relative_to(root)}: ${key} is not defined in .env-example")
            root_example.commented.setdefault(key, [])  # Report each variable once

    if errors:
        log("ERROR", f"{errors} .env-example inconsistencies")
        return 1
    log("INFO", ".env-example files are consistent")
    return 0


def set_values(args):
    env = EnvFile(args.env)
    lines = list(env.lines)
    for key, value in parse_assignments(args.assignments, "set").items():
        if args.if_empty and env.active.get(key, ("",))[0]:
            continue
        if key in env.active:
            _, _, suffix, i = env.active[key]
            lines[i] = f"{key}={value}{suffix}"
        elif key in env.commented:
            i = lines.index(env.commented[key][0])
            lines[i] = f"{key}={value}{split_commented(lines[i])[2]}"
        else:
            lines.append(f"{key}={value}")
        log("INFO", f"{env.path}: {key}={show(key, value)} (set by setup)")
    content = "\n".join(lines) + "\n"
    if content != ("\n".join(env.lines) + "\n"):
        env.path.resolve().write_text(content)
    return 0


def get(args):
    env = EnvFile(args.env)
    entry = env.active.get(args.key)
    print(entry[0] if entry else "")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("sync")
    p.add_argument("example")
    p.add_argument("env")
    p.add_argument("--set", action="append", metavar="KEY=VALUE", help="Force a value")
    p.add_argument("--set-if-empty", action="append", metavar="KEY=VALUE", help="Set a value if missing or empty")
    p.add_argument("--backup-dir", help="Save the previous version of ENV in this directory before rewriting it")
    p.set_defaults(func=sync)

    p = sub.add_parser("check")
    p.set_defaults(func=check)

    p = sub.add_parser("set")
    p.add_argument("env")
    p.add_argument("assignments", nargs="+", metavar="KEY=VALUE")
    p.add_argument("--if-empty", action="store_true", help="Only set variables that are missing or empty")
    p.set_defaults(func=set_values)

    p = sub.add_parser("get")
    p.add_argument("env")
    p.add_argument("key")
    p.set_defaults(func=get)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
