#!/usr/bin/env python3
#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#
"""Single source of the DSL's reserved words: the grammar itself.

PowerEventDSL.g4 is the only place a keyword is declared, so anything that needs to know the reserved words
(the LaTeX reference, the Argus editor) reads a file generated from it rather than keeping its own copy that
would drift. Commented-out rules are skipped, so a literal that is not currently part of the language, such as
the disabled group-by and property filters, is not advertised as a keyword.

  python3 extract_keywords.py           regenerate every output
  python3 extract_keywords.py --check   fail if an output is out of date (used by the dsl-keywords test)
"""

import argparse
import pathlib
import re
import sys

DSL_DIR = pathlib.Path(__file__).resolve().parent.parent
REPO = DSL_DIR.parent.parent
GRAMMAR = DSL_DIR / "PowerEventDSL.g4"
TEX_OUT = REPO / "docs" / "dsl_engine" / "dsl_keywords.tex"
TS_OUT = REPO / "argus" / "src" / "features" / "dsl-editor" / "generated" / "dslKeywords.ts"
HPP_OUT = DSL_DIR / "DslKeywords.h"

BANNER = "Generated from Orchestrator/DSL/PowerEventDSL.g4 by Orchestrator/DSL/tools/extract_keywords.py."


def read_literals():
    """Every quoted literal in the live part of the grammar, split into element types and everything else."""
    text = GRAMMAR.read_text()
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)  # disabled rules
    text = re.sub(r"//[^\n]*", "", text)

    element_rule = re.search(r"^gridElementType\s*:(.*?);", text, flags=re.S | re.M)
    if not element_rule:
        sys.exit("gridElementType rule not found in the grammar")
    element_types = sorted(set(re.findall(r"'([^']+)'", element_rule.group(1))))

    words = {w for w in re.findall(r"'([^']+)'", text) if re.fullmatch(r"[A-Za-z0-9_]+", w)}
    keywords = sorted(words - set(element_types))
    return keywords, element_types


def wrap(names, indent, width=108):
    """Comma-separated names over as few lines as fit, so a regenerated file stays readable in review."""
    lines, current = [], indent
    for i, name in enumerate(names):
        piece = name + ("," if i < len(names) - 1 else "")
        if len(current) + len(piece) > width and current != indent:
            lines.append(current)
            current = indent
        current += piece
    lines.append(current)
    return lines


def render_tex(keywords, element_types):
    # alsoletter carries '2' and '3' because two element types start with a digit, which listings would otherwise
    # read as a number followed by an identifier. Class 1 is declared empty on purpose: keywordsprefix styles what
    # it matches as class 1, which is what gives $parameters a colour of their own, and listings errors out if the
    # class was never declared.
    lines = [
        f"% {BANNER}",
        "% Do not edit by hand: run the script instead.",
        "\\lstdefinelanguage{PowerEventDSL}{",
        "  sensitive=true,",
        "  alsoletter={_23},",
        "  keywordsprefix=\\$,",
        "  morekeywords=[1]{},",
        "  morekeywords=[2]{%",
    ]
    lines += [line + "%" for line in wrap(keywords, "    ")]
    lines += ["  },", "  morekeywords=[3]{%"]
    lines += [line + "%" for line in wrap(element_types, "    ")]
    lines += ["  },", "  morecomment=[l]{//},", "  morestring=[b]\",", "}", ""]
    return "\n".join(lines)


def render_ts(keywords, element_types):
    def as_array(names):
        return "\n".join("  " + line.strip() for line in wrap([f'"{n}"' for n in names], "  ", width=104))

    return (
        # Same licence header every other source file in the repo carries
        "/*\n"
        "Copyright (c) 2025-2026, RTE (https://www.rte-france.com)\n"
        "See AUTHORS.md\n"
        "SPDX-License-Identifier: MPL-2.0\n"
        "This file is part of Twin-CR, a platform for real-time cyber-physical\n"
        "co-simulation of power systems.\n"
        "*/\n"
        "\n"
        f"// {BANNER}\n"
        "// Do not edit by hand: run the script instead.\n"
        "\n"
        "/** Reserved words of the DSL, every quoted literal in the grammar that is not an element type. */\n"
        "export const DSL_KEYWORDS: readonly string[] = [\n"
        f"{as_array(keywords)}\n"
        "];\n"
        "\n"
        "/** The gridElementType alternatives. Two of them start with a digit. */\n"
        "export const DSL_ELEMENT_TYPES: readonly string[] = [\n"
        f"{as_array(element_types)}\n"
        "];\n"
    )


def render_hpp(keywords, element_types):
    def as_list(names):
        return "\n".join("    " + line.strip() for line in wrap([f'"{n}"' for n in names], "    ", width=110))

    return (
        "/*\n"
        "Copyright (c) 2025-2026, RTE (https://www.rte-france.com)\n"
        "See AUTHORS.md\n"
        "SPDX-License-Identifier: MPL-2.0\n"
        "This file is part of Twin-CR, a platform for real-time cyber-physical\n"
        "co-simulation of power systems.\n"
        "*/\n"
        "\n"
        f"// {BANNER}\n"
        "// Do not edit by hand: run the script instead.\n"
        "\n"
        "#ifndef DSL_KEYWORDS_H\n"
        "#define DSL_KEYWORDS_H\n"
        "\n"
        "#include <array>\n"
        "#include <string_view>\n"
        "\n"
        "/** Reserved words of the DSL: every quoted literal in the grammar that is not an element type. */\n"
        f"inline constexpr std::array<std::string_view, {len(keywords)}> DSL_KEYWORDS = {{{{\n"
        f"{as_list(keywords)}\n"
        "}};\n"
        "\n"
        "/** The gridElementType alternatives. Two of them start with a digit. */\n"
        f"inline constexpr std::array<std::string_view, {len(element_types)}> DSL_ELEMENT_TYPES = {{{{\n"
        f"{as_list(element_types)}\n"
        "}};\n"
        "\n"
        "#endif // DSL_KEYWORDS_H\n"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if an output is out of date")
    args = parser.parse_args()

    keywords, element_types = read_literals()
    outputs = {
        TEX_OUT: render_tex(keywords, element_types),
        TS_OUT: render_ts(keywords, element_types),
        HPP_OUT: render_hpp(keywords, element_types),
    }

    stale = []
    for path, content in outputs.items():
        if args.check:
            if not path.exists() or path.read_text() != content:
                stale.append(path)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            print(f"wrote {path.relative_to(REPO)}")

    if stale:
        for path in stale:
            print(f"out of date: {path.relative_to(REPO)}", file=sys.stderr)
        print("run Orchestrator/DSL/tools/extract_keywords.py to regenerate", file=sys.stderr)
        return 1
    if args.check:
        print(f"up to date: {len(keywords)} keywords, {len(element_types)} element types")
    return 0


if __name__ == "__main__":
    sys.exit(main())
