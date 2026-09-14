"""Candidate platform parameters for the G2 screening.

Every number carries a unit, a status and a source. Statuses follow
``const.md``:

``source-supported``
    Taken from a primary source that was actually fetched and read.
``unresolved``
    A working figure used only to make the screening concrete. It is **not**
    accepted physics, it may not open the P5 search, and every verdict that
    touches one lists it (see :meth:`Platform.unresolved_fields`).

Nothing here is ``EM-supported``: no EM run has been made in this repository.

Filling these in properly is P1 (``docs/decisions/2026-09-14-plan2-kerr-reservoir.md``
section 3), which also requires each row to share one process/geometry context
rather than mixing the best number from several devices.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

STATUS_SOURCE = "source-supported"
STATUS_UNRESOLVED = "unresolved"
STATUS_SYNTHETIC = "synthetic"


@dataclass(frozen=True)
class Param:
    value: float
    unit: str
    status: str
    source: str
    note: str = ""

    def __post_init__(self) -> None:
        if self.status not in (STATUS_SOURCE, STATUS_UNRESOLVED, STATUS_SYNTHETIC):
            raise ValueError(f"unknown parameter status {self.status!r}")


@dataclass(frozen=True)
class Platform:
    name: str
    group_index: Param
    loss_db_per_cm: Param
    n2_m2_per_w: Param
    a_eff_m2: Param
    radius_m: Param
    q_intrinsic_reported: Param | None = None
    dn_dt_per_k: Param | None = None
    alpha_abs_db_per_cm: Param | None = None
    thermal_resistance_k_per_w: Param | None = None

    def unresolved_fields(self) -> list[str]:
        out = []
        for f in fields(self):
            if f.name == "name":
                continue
            param = getattr(self, f.name)
            if param is None:
                out.append(f"{f.name} (absent)")
            elif param.status != STATUS_SOURCE:
                out.append(f"{f.name} ({param.status})")
        return out

    def parameter_rows(self) -> list[dict]:
        rows = []
        for f in fields(self):
            if f.name == "name":
                continue
            param = getattr(self, f.name)
            if param is None:
                rows.append({"name": f.name, "value": None, "unit": "",
                             "status": "absent", "source": "", "note": ""})
            else:
                rows.append({"name": f.name, "value": param.value,
                             "unit": param.unit, "status": param.status,
                             "source": param.source, "note": param.note})
        return rows


_UNSOURCED = ("working figure for screening only; not read from a primary "
              "source in this session")


SI3N4 = Platform(
    name="Si3N4/SiO2",
    group_index=Param(2.0, "1", STATUS_UNRESOLVED, "P1 open", _UNSOURCED),
    loss_db_per_cm=Param(0.1, "dB/cm", STATUS_UNRESOLVED, "P1 open", _UNSOURCED),
    n2_m2_per_w=Param(2.4e-19, "m^2/W", STATUS_UNRESOLVED, "P1 open", _UNSOURCED),
    a_eff_m2=Param(1.0e-12, "m^2", STATUS_UNRESOLVED, "P1 open", _UNSOURCED),
    radius_m=Param(100e-6, "m", STATUS_SYNTHETIC, "design choice",
                   "scan variable, not a measured device"),
)

ALGAAS_OI = Platform(
    name="AlGaAs-on-insulator",
    group_index=Param(3.8, "1", STATUS_UNRESOLVED, "P1 open", _UNSOURCED),
    loss_db_per_cm=Param(0.2, "dB/cm", STATUS_UNRESOLVED, "P1 open", _UNSOURCED),
    n2_m2_per_w=Param(2.6e-17, "m^2/W", STATUS_UNRESOLVED, "P1 open", _UNSOURCED),
    a_eff_m2=Param(0.3e-12, "m^2", STATUS_UNRESOLVED, "P1 open", _UNSOURCED),
    radius_m=Param(100e-6, "m", STATUS_SYNTHETIC, "design choice",
                   "scan variable, not a measured device"),
    q_intrinsic_reported=Param(
        3.52e6, "1", STATUS_SOURCE,
        "Xie et al., Opt. Express 28(22), 32894 (2020), arXiv:2004.14537",
        "abstract: intrinsic Q up to 3.52e6, finesse up to 1.4e4; read 2026-09-14",
    ),
)

PLATFORMS = (SI3N4, ALGAAS_OI)
