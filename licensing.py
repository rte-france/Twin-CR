"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Add or update the RTE license header of the source files.

Usage:
    python3 licensing.py [FILE ...]

With arguments (pre-commit passes the staged files), only those files are processed.
Without arguments, every file tracked by git in the current repository is processed.

For each file whose type is listed in COMMENT_STYLES or matched by special_style():
- a file without any license header gets the header built by header_lines();
- a file that already carries an RTE header of this project (current or earlier
  template) gets it rewritten in place, keeping its copyright years;
- a file that carries a third-party notice (a copyright not held by RTE, another SPDX
  identifier, another project's header or license text) is left untouched, as is any
  file under a directory listed in EXCLUDED_DIRS.
A second run right after a first one changes nothing.
"""
import datetime
import re
import subprocess
import sys
import warnings
from pathlib import Path

############
#  HEADER  #
############

HOLDER = "RTE (https://www.rte-france.com)"
SPDX_ID = "MPL-2.0"
PROJECT_LINES = (
    "This file is part of Twin-CR, a platform for real-time cyber-physical",
    "co-simulation of power systems.",
)


def header_lines(years):
    return [
        f"Copyright (c) {years}, {HOLDER}",
        "See AUTHORS.md",
        f"SPDX-License-Identifier: {SPDX_ID}",
        *PROJECT_LINES,
    ]


CURRENT_YEAR = datetime.date.today().year


def years_for(file_path: Path):
    """Copyright years of a header added to a file that has none:
    from the year the file entered git history to the current year."""
    try:
        result = subprocess.run(
            ["git", "log", "--follow", "--format=%ad", "--date=format:%Y", "--", str(file_path)],
            capture_output=True,
            text=True,
            check=True,
        )
        first = int(result.stdout.split()[-1])
    except (OSError, subprocess.CalledProcessError, ValueError, IndexError):
        first = CURRENT_YEAR
    return str(CURRENT_YEAR) if first >= CURRENT_YEAR else f"{first}-{CURRENT_YEAR}"

# Lines that may appear in an RTE header of this project, current or earlier template.
# A header is recognised as a contiguous run of these lines starting with RTE_COPYRIGHT.
RTE_COPYRIGHT = re.compile(
    r"Copyright \(c\) (?P<years>\d{4}(?:\s*[-,]\s*\d{4})*),? RTE \(https?://www\.rte-france\.com/?\)"
)
SPDX_LINE = re.compile(r"SPDX-License-Identifier: MPL-2\.0")
OWN_PROJECT_LINES = [
    re.compile(r"This file is part of the (?i:twineu-core|twin-cr) project\."),
    re.compile(re.escape(PROJECT_LINES[0])),
]
KNOWN_HEADER_LINES = [
    RTE_COPYRIGHT,
    SPDX_LINE,
    *OWN_PROJECT_LINES,
    re.compile(re.escape(PROJECT_LINES[1])),
    re.compile(r"See AUTHORS\.md"),
    re.compile(r"This Source Code Form is subject to the terms of the Mozilla Public"),
    re.compile(r"License, v\. 2\.0\. If a copy of the MPL was not distributed with this"),
    re.compile(r"file, [Yy]ou can obtain one at https?://mozilla\.org/MPL/2\.0/\."),
]

# The RTE copyright line of a header must start within the first lines of a file.
HEAD_SIZE = 15

# Comment decoration allowed in front of a header line ("# ", " * ", "// "...).
LINE_PREFIX = re.compile(r"\s*(?:#|\*|//|--|;|%)?\s*")

# Third-party markers, looked for at the start of any comment or docstring line.
_DECORATION = r"^\s*(?:#+|//+|/\*+!?|\*+|<!--|--|;+|%+|\"\"\"|''')?\s*"
ANY_COPYRIGHT = re.compile(_DECORATION + r"Copyright\b(?:\s*(?:\(c\)|\u00a9))?\s*\d{4}", re.IGNORECASE)
ANY_SPDX = re.compile(_DECORATION + r"SPDX-License-Identifier:\s*(?P<id>.*?)\s*(?:\*/|-->)?\s*$")
ANY_PROJECT = re.compile(_DECORATION + r"(?P<line>This file is part of .*?)\s*$")
THIRD_PARTY_TEXT = re.compile(
    _DECORATION
    + r"(?:@license\b|Licensed under the|Permission is hereby granted|"
    r"Redistribution and use in source and binary forms|This program is free software|"
    r"GNU (?:Lesser |Library |Affero )?General Public License)",
    re.IGNORECASE,
)

#################
#  FILE TYPES   #
#################


def _block(open_, close):
    return lambda lines: open_ + "\n" + "\n".join(lines) + "\n" + close + "\n\n"


def _line_comment(lines, prefix="#"):
    return prefix + "\n" + "".join(f"{prefix} {line}\n" for line in lines) + prefix + "\n\n"


_C_STYLE = _block("/*", "*/")
_PY_STYLE = _block('"""', '"""')
_XML_STYLE = _block("<!--", "-->")
_JINJA_STYLE = _block("{#", "#}")
_DSL_STYLE = lambda lines: _line_comment(lines, "//")

# Comment style per extension. Types left out on purpose:
# - .sql: argus/migrations is embedded by sqlx::migrate!, which checksums each applied
#   migration, so editing one breaks existing databases;
# - .dsl under a tests directory: DSL test expectations quote script line numbers
#   (the other .dsl files are handled by special_style());
# - .ftl: Keycloak theme template derived from Keycloak (Apache-2.0), see NOTICE;
# - lockfiles (LOCKFILES): generated by the package manager, which rewrites them
#   without comments;
# - .json and data files (.iidm, .xiidm, .par, .dyd, .jobs, .crv): no comment syntax,
#   or example data partly taken from other projects;
# - .md, .rst, .tex and other documentation, which follows the documentation license.
COMMENT_STYLES = {
    ".rs": _C_STYLE,
    ".ts": _C_STYLE,
    ".tsx": _C_STYLE,
    ".js": _C_STYLE,
    ".jsx": _C_STYLE,
    ".mjs": _C_STYLE,
    ".cjs": _C_STYLE,
    ".java": _C_STYLE,
    ".c": _C_STYLE,
    ".cpp": _C_STYLE,
    ".h": _C_STYLE,
    ".hpp": _C_STYLE,
    ".g4": _C_STYLE,
    ".css": _C_STYLE,
    ".py": _PY_STYLE,
    ".sh": _line_comment,
    ".bash": _line_comment,
    ".yml": _line_comment,
    ".yaml": _line_comment,
    ".toml": _line_comment,
    ".properties": _line_comment,
    ".ini": _line_comment,
    ".conf": _line_comment,
    ".cmake": _line_comment,
    ".dockerfile": _line_comment,
    ".version": _line_comment,
    ".xml": _XML_STYLE,
    ".html": _XML_STYLE,
}

# Directories holding vendored third-party code: never touched.
EXCLUDED_DIRS = {
    "node_modules",
    "vendor",
    "vendored",
    "third_party",
    "third-party",
    "thirdparty",
    "3rdparty",
    "external",
    "extern",
    "_deps",
    "site-packages",
    ".venv",
    "venv",
    ".git",
}


def is_dockerfile(file_path: Path):
    # Dockerfile, Dockerfile.<name>, Dockerfile-<name>, <name>.dockerfile
    return bool(re.fullmatch(r"Dockerfile(?:[.-].+)?", file_path.name)) or (
        file_path.suffix == ".dockerfile"
    )


# Lockfiles are never touched: the package manager rewrites them without comments.
LOCKFILES = {"pnpm-lock.yaml", "package-lock.json", "yarn.lock"}

# Files without an extension of COMMENT_STYLES that accept "#" comments.
REQUIREMENTS = re.compile(r"requirements[-\w]*\.txt")
ENV_FILES = {".env-example", ".env-tests"}


def special_style(file_path: Path):
    if file_path.name == "CMakeLists.txt" or is_dockerfile(file_path):
        return _line_comment
    if REQUIREMENTS.fullmatch(file_path.name) or file_path.name in ENV_FILES:
        return _line_comment
    if file_path.suffix == ".dsl" and "tests" not in file_path.parts:
        # PowerEventDSL skips "//" comments (rule COMMENT of PowerEventDSL.g4).
        # An empty script (e.g. IEEE14.dsl) is left empty rather than reduced to a header.
        try:
            if file_path.stat().st_size == 0:
                return None
        except OSError:
            return None
        return _DSL_STYLE
    return None


def get_comment_style(file_path: Path):
    if file_path.name in LOCKFILES or file_path.suffix == ".lock":
        return None
    return special_style(file_path) or COMMENT_STYLES.get(file_path.suffix)


##############
#  ANALYSIS  #
##############


def find_third_party_notice(content: str):
    """Return the reason why the file looks third-party, or None."""
    for line in content.splitlines():
        if ANY_COPYRIGHT.match(line) and not RTE_COPYRIGHT.search(line):
            return "copyright not held by RTE"
        spdx = ANY_SPDX.match(line)
        if spdx and spdx["id"] != SPDX_ID:
            return "other SPDX identifier"
        project = ANY_PROJECT.match(line)
        if project and not any(p.fullmatch(project["line"]) for p in OWN_PROJECT_LINES):
            return "header of another project"
        if THIRD_PARTY_TEXT.match(line):
            return "third-party license text"
    return None


def find_rte_header(lines):
    """Locate an RTE header of this project.

    Return (start, end, prefix, years) for lines[start:end], or None.
    """
    for start, line in enumerate(lines[:HEAD_SIZE]):
        text = line.rstrip("\r\n")
        idx = text.find("Copyright")
        if idx == -1:
            continue
        prefix = text[:idx]
        match = RTE_COPYRIGHT.fullmatch(text[idx:].rstrip())
        if not match or not LINE_PREFIX.fullmatch(prefix):
            continue
        end = start + 1
        while end < len(lines):
            candidate = lines[end].rstrip("\r\n")
            if not candidate.startswith(prefix):
                break
            body = candidate[len(prefix):].rstrip()
            if not any(p.fullmatch(body) for p in KNOWN_HEADER_LINES):
                break
            end += 1
        bodies = [l.rstrip("\r\n")[len(prefix):].rstrip() for l in lines[start:end]]
        has_spdx = any(SPDX_LINE.fullmatch(b) for b in bodies)
        has_project = any(p.fullmatch(b) for b in bodies for p in OWN_PROJECT_LINES)
        if has_spdx and has_project:
            return start, end, prefix, match["years"]
        return None
    return None


def has_license_marker(content: str):
    return any(
        (ANY_SPDX.match(line) or ANY_COPYRIGHT.match(line)) for line in content.splitlines()
    )


###############
#  REWRITING  #
###############


def newline_of(content: str):
    return "\r\n" if "\r\n" in content else "\n"


def replace_header(lines, start, end, prefix, years):
    eol = "\r\n" if lines[start].endswith("\r\n") else "\n"
    new_block = [f"{prefix}{line}".rstrip() + eol for line in header_lines(years)]
    return "".join(lines[:start] + new_block + lines[end:])


CODING_LINE = re.compile(r"^[ \t\f]*#.*?coding[:=]")
# Dockerfile parser directives are only read before any comment, blank line or instruction.
DOCKER_DIRECTIVE = re.compile(r"#\s*(?:syntax|escape|check)\s*=", re.IGNORECASE)
# A CSS @charset rule is only honoured as the very first bytes of the file.
CSS_CHARSET = re.compile(r'@charset "[^"]*";')


def split_preamble(content: str, file_path: Path):
    """Split off what must stay above the header: BOM, shebang, encoding line,
    Dockerfile parser directives, CSS @charset rule, XML declaration, HTML doctype."""
    bom = ""
    if content.startswith("\ufeff"):
        bom, content = "\ufeff", content[1:]
    lines = content.splitlines(keepends=True)
    n = 0
    if lines and lines[0].startswith("#!"):
        n = 1
    if file_path.suffix == ".py":
        while n < min(2, len(lines)) and CODING_LINE.match(lines[n]):
            n += 1
    elif is_dockerfile(file_path):
        while n < len(lines) and DOCKER_DIRECTIVE.match(lines[n]):
            n += 1
    elif file_path.suffix == ".css" and lines and CSS_CHARSET.match(lines[0]):
        n = 1
    k = n
    while k < len(lines) and not lines[k].strip():
        k += 1
    if k < len(lines):
        first = lines[k].lstrip().lower()
        if first.startswith("<?xml") or first.startswith("<!doctype"):
            n = k + 1
    preamble = "".join(lines[:n])
    if preamble and not preamble.endswith("\n"):
        preamble += newline_of(content)
    return bom + preamble, "".join(lines[n:])


def merge_python_docstring(body: str, lines):
    """Python accepts a single docstring before `from __future__` imports:
    put the header at the top of an existing module docstring."""
    stripped = body.lstrip()
    quote = next((q for q in ('"""', "'''") if stripped.startswith(q)), None)
    if quote is None:
        return None
    end = stripped.find(quote, len(quote))
    if end == -1:
        return None
    inner = stripped[len(quote):end].strip()
    rest = stripped[end + len(quote):].lstrip("\n")
    text = "\n".join(lines)
    merged = f"{text}\n\n{inner}" if inner else text
    return f"{quote}\n{merged}\n{quote}\n\n{rest}"


def compiles(source: str, file_path: Path):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            compile(source, str(file_path), "exec")
        except (SyntaxError, ValueError):
            return False
    return True


def add_header(content: str, file_path: Path, style):
    preamble, body = split_preamble(content, file_path)
    if file_path.suffix == ".html" and body.lstrip().startswith(("{%", "{#")):
        style = _JINJA_STYLE  # Jinja template: an HTML comment would be rendered
    lines = header_lines(years_for(file_path))
    if file_path.suffix == ".py":
        merged = merge_python_docstring(body, lines)
        candidate = preamble + (merged if merged is not None else style(lines) + body)
        if compiles(candidate, file_path) or not compiles(content, file_path):
            new_content = candidate
        else:
            # e.g. a comment above the docstring, then a __future__ import
            new_content = preamble + _line_comment(lines) + body
    else:
        new_content = preamble + style(lines) + body
    eol = newline_of(content)
    if eol != "\n":
        new_content = re.sub(r"(?<!\r)\n", eol, new_content)
    return new_content


def process_file(file_path: Path, stats):
    style = get_comment_style(file_path)
    if not style:
        return
    if EXCLUDED_DIRS.intersection(file_path.parts[:-1]):
        return
    if file_path.is_symlink() or not file_path.is_file():
        return

    try:
        content = file_path.read_bytes().decode("utf-8")
    except Exception:
        print(f"Could not read: {file_path}")
        stats["errors"] += 1
        return

    reason = find_third_party_notice(content)
    if reason:
        print(f"Skip ({reason}): {file_path}")
        stats["third_party"] += 1
        return

    lines = content.splitlines(keepends=True)
    found = find_rte_header(lines)
    if found:
        new_content = replace_header(lines, *found)
        action = "Updated"
    elif has_license_marker(content):
        print(f"Skip (unrecognised license header): {file_path}")
        stats["unrecognised"] += 1
        return
    else:
        new_content = add_header(content, file_path, style)
        action = "Added"
        if new_content is None:
            return

    if new_content == content:
        stats["unchanged"] += 1
        return
    try:
        file_path.write_bytes(new_content.encode("utf-8"))
    except Exception:
        print(f"Failed to write: {file_path}")
        stats["errors"] += 1
        return
    print(f"{action}: {file_path}")
    stats[action.lower()] += 1


# Files tracked by git in the current repository. Submodules are not walked:
# they are separate projects with their own licensing.
def get_git_files():
    result = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True)
    return [Path(f) for f in result.stdout.splitlines()]


############
#   MAIN   #
############
if __name__ == "__main__":
    args = sys.argv[1:]
    stats = dict.fromkeys(
        ("added", "updated", "unchanged", "third_party", "unrecognised", "errors"), 0
    )

    # pre-commit (pass_filenames: true) gives the files to scan;
    # without arguments, every tracked file is processed.
    for path in [Path(f) for f in args] if args else get_git_files():
        process_file(path, stats)

    print(
        "Done. added={added} updated={updated} unchanged={unchanged} "
        "third_party={third_party} unrecognised={unrecognised} errors={errors}".format(**stats)
    )
