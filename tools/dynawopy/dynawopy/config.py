"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

from dataclasses import dataclass, field
from pathlib import Path
from lxml import etree
from typing import Tuple, ClassVar


@dataclass
class Testcase:

    __test__ = False

    exts: ClassVar[Tuple[str]] = ("iidm", "crv", "dyd", "jobs", "par")

    name: str = "Default"
    ts_dir: str = Path("Default/")
    nsmap: dict = field(
        default_factory=lambda: {
            "iidm": "http://www.powsybl.org/schema/iidm/1_5",
            "dyn": "http://www.rte-france.com/dynawo",
        }
    )

    iidm_fpath: Path = Path("Default.iidm")
    crv_fpath: Path = Path("Default.crv")
    dyd_fpath: Path = Path("Default.dyd")
    jobs_fpath: Path = Path("Default.jobs")
    par_fpath: Path = Path("Default.par")

    iidm: etree.ElementTree = field(init=False)
    crv: etree.ElementTree = field(init=False)
    dyd: etree.ElementTree = field(init=False)
    jobs: etree.ElementTree = field(init=False)
    par: etree.ElementTree = field(init=False)

    def __post_init__(self):
        self.iidm = etree.parse(str(self.iidm_fpath))
        self.crv = etree.parse(str(self.crv_fpath))
        self.dyd = etree.parse(str(self.dyd_fpath))
        self.jobs = etree.parse(str(self.jobs_fpath))
        self.par = etree.parse(str(self.par_fpath))

    def xp_iidm(self, expr):
        return self.xpath(expr, self.iidm)

    def xp_crv(self, expr):
        return self.xpath(expr, self.crv)

    def xp_dyd(self, expr):
        return self.xpath(expr, self.dyd)

    def xp_jobs(self, expr):
        return self.xpath(expr, self.jobs)

    def xp_par(self, expr):
        return self.xpath(expr, self.par)

    def xpath(self, expr, tree):
        """Convenience method to not always having to pass namespaces dictionary"""
        return tree.xpath(expr, namespaces=self.nsmap)

    def save(self, name: list | str | None = None, directory=None, to_save: list | etree.ElementTree | None = None, spaces = 4):
        save_dir = Path(directory if directory is not None else self.ts_dir)
        save_dir.mkdir(exist_ok=True)
        tree_ext_map = dict(zip([self.iidm, self.crv, self.dyd, self.jobs, self.par], Testcase.exts))

        to_save = to_save if to_save is not None else [self.iidm, self.crv, self.dyd, self.jobs, self.par]
        to_save = to_save if isinstance(to_save, list) else [to_save]

        if name is None:
            name = [None] * len(to_save)
        elif isinstance(name, str):
            name = [name] * len(to_save)
        else:
            name = list(name)

        assert len(name) == len(to_save), "name and to_save should have the same number of elements"

        for tree, tree_name in zip(to_save, name):
            ext = tree_ext_map.get(tree, None)
            if not ext:
                continue
            to_save_name = f"{tree_name}.{ext}" if tree_name is not None else getattr(self, f"{ext}_fpath").name
            etree.indent(tree, space="".join([" "] * spaces))
            with open(save_dir / to_save_name, "w") as f:
                f.write(
                    etree.tostring(
                        tree,
                        pretty_print=True,
                        encoding="UTF-8",
                        xml_declaration=True,
                    ).decode()
                )

    @classmethod
    def from_directory(cls, dir_fpath, name=None, iidm=None, dyd=None, crv=None, jobs=None, par=None):
        ts_dir = Path(dir_fpath)
        if not name:
            name = "*"
        return cls(
            name=ts_dir.stem,
            ts_dir=ts_dir,
            iidm_fpath=list(ts_dir.glob(f"{iidm if iidm is not None else name}.iidm"))[0],
            dyd_fpath=list(ts_dir.glob(f"{dyd if dyd is not None else name}.dyd"))[0],
            crv_fpath=list(ts_dir.glob(f"{crv if crv is not None else name}.crv"))[0],
            jobs_fpath=list(ts_dir.glob(f"{jobs if jobs is not None else name}.jobs"))[0],
            par_fpath=list(ts_dir.glob(f"{par if par is not None else name}.par"))[0],
        )
