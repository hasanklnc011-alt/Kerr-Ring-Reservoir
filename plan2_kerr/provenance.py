"""P0 — experiment records for the Plan 2 Kerr line.

Every result in this line gets a record: what was run, with which tools, over
which inputs, producing which files, and which gates it did or did not pass.
The Plan 2 ADR section 9 asks for source/config/environment content hashes, the
production command, the validity range, and per-gate evidence; this module is
where that shape is enforced rather than described.

Three rules the code enforces, not just documents:

* **Append-only.** An experiment id may be written once. Re-running a study
  means a new id, so a record can never be quietly improved after the fact.
  A record that is wrong or stale is *superseded*, not edited: the replacement
  names it in ``supersedes``, and verification then skips the old one instead
  of flagging it forever.
* **Hashes are recomputed, not trusted.** :func:`verify_record` re-reads every
  referenced file and compares. A record whose outputs moved is invalid.
* **Unresolved stays visible.** A parameter without a primary source carries
  ``status: "unresolved"`` and :meth:`ExperimentRecord.unresolved_inputs`
  lists it; nothing silently promotes to accepted physics.

Ids are ``plan2-kerr-P<phase>-<4 digits>``, e.g. ``plan2-kerr-P1-0001``.
"""

from __future__ import annotations

import hashlib
import json
import platform
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "plan2-kerr-experiment/1"

ID_PATTERN = re.compile(r"^plan2-kerr-P(?P<phase>[0-6])-(?P<serial>\d{4})$")

VALID_STATUSES = ("synthetic", "source-supported", "EM-supported", "unresolved")

DEFAULT_RECORD_DIR = Path("studies/plan2-kerr/experiments")


class ProvenanceError(RuntimeError):
    """A record is malformed, duplicated, or no longer matches its files."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --- ids --------------------------------------------------------------------

def validate_id(experiment_id: str) -> str:
    if not ID_PATTERN.match(experiment_id):
        raise ProvenanceError(
            f"{experiment_id!r} is not a plan2-kerr-P<0-6>-<4 digits> id"
        )
    return experiment_id


def make_id(phase: int, serial: int) -> str:
    if not 0 <= phase <= 6:
        raise ProvenanceError(f"phase {phase} is outside P0..P6")
    if not 0 <= serial <= 9999:
        raise ProvenanceError(f"serial {serial} does not fit four digits")
    return validate_id(f"plan2-kerr-P{phase}-{serial:04d}")


def next_id(phase: int, record_dir: Path = DEFAULT_RECORD_DIR) -> str:
    """Lowest unused serial for this phase."""
    used = set()
    directory = Path(record_dir)
    if directory.exists():
        for path in directory.glob(f"plan2-kerr-P{phase}-*.json"):
            match = ID_PATTERN.match(path.stem)
            if match:
                used.add(int(match.group("serial")))
    serial = 1
    while serial in used:
        serial += 1
    return make_id(phase, serial)


# --- environment ------------------------------------------------------------

def tool_versions(extra_modules=("numpy", "tidy3d", "scipy", "xarray")) -> dict:
    """Real installed versions, never a hand-written list."""
    versions = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "executable": sys.executable,
    }
    for name in extra_modules:
        try:
            module = __import__(name)
            versions[name] = getattr(module, "__version__", "unknown")
        except Exception:
            versions[name] = "not installed"
    return versions


def git_state(repo_root: Path | None = None) -> dict:
    """Commit and dirtiness, so a record cannot claim a clean tree it lacked."""
    root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[1]
    def run(args):
        return subprocess.run(args, cwd=root, capture_output=True, text=True,
                              timeout=30)
    try:
        head = run(["git", "rev-parse", "HEAD"])
        status = run(["git", "status", "--porcelain"])
        if head.returncode != 0:
            return {"commit": "unavailable", "dirty": None}
        return {
            "commit": head.stdout.strip(),
            "dirty": bool(status.stdout.strip()),
        }
    except Exception as exc:
        return {"commit": "unavailable", "dirty": None, "error": repr(exc)}


# --- record pieces ----------------------------------------------------------

@dataclass(frozen=True)
class Parameter:
    """One physical or numerical input, with its provenance."""

    name: str
    value: float | str | None
    unit: str
    status: str
    source: str
    note: str = ""

    def __post_init__(self) -> None:
        if self.status not in VALID_STATUSES:
            raise ProvenanceError(
                f"status {self.status!r} not in {list(VALID_STATUSES)}")

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Artifact:
    """A file the experiment consumed or produced."""

    path: str
    sha256: str
    role: str  # "input" or "output"
    note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def artifact(path: Path, role: str, note: str = "",
             repo_root: Path | None = None) -> Artifact:
    p = Path(path)
    if not p.exists():
        raise ProvenanceError(f"artifact not found: {p}")
    root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[1]
    try:
        rel = p.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        rel = p.resolve().as_posix()
    return Artifact(path=rel, sha256=sha256_file(p), role=role, note=note)


@dataclass(frozen=True)
class GateResult:
    name: str
    threshold: float | str
    value: float | str | None
    passed: bool
    detail: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# --- the record -------------------------------------------------------------

@dataclass
class ExperimentRecord:
    experiment_id: str
    phase: int
    title: str
    command: str
    created_utc: str = field(default_factory=_utc_now)
    schema: str = SCHEMA
    tools: dict = field(default_factory=tool_versions)
    git: dict = field(default_factory=git_state)
    readout: dict = field(default_factory=dict)
    benchmark: dict = field(default_factory=dict)
    parameters: list[Parameter] = field(default_factory=list)
    artifacts: list[Artifact] = field(default_factory=list)
    gates: list[GateResult] = field(default_factory=list)
    validity: str = ""
    uncertainty_method: str = ""
    supersedes: str | None = None
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        validate_id(self.experiment_id)
        if self.supersedes is not None:
            validate_id(self.supersedes)
            if self.supersedes == self.experiment_id:
                raise ProvenanceError("a record cannot supersede itself")
        match = ID_PATTERN.match(self.experiment_id)
        if int(match.group("phase")) != self.phase:
            raise ProvenanceError(
                f"id {self.experiment_id} does not match phase P{self.phase}")

    def unresolved_inputs(self) -> list[str]:
        return [p.name for p in self.parameters if p.status == "unresolved"]

    @property
    def passed(self) -> bool:
        """A record with no gates has not passed anything."""
        return bool(self.gates) and all(g.passed for g in self.gates)

    def to_dict(self) -> dict:
        return {
            "schema": self.schema,
            "experiment_id": self.experiment_id,
            "phase": self.phase,
            "title": self.title,
            "created_utc": self.created_utc,
            "command": self.command,
            "tools": self.tools,
            "git": self.git,
            "readout": self.readout,
            "benchmark": self.benchmark,
            "parameters": [p.to_dict() for p in self.parameters],
            "artifacts": [a.to_dict() for a in self.artifacts],
            "gates": [g.to_dict() for g in self.gates],
            "validity": self.validity,
            "uncertainty_method": self.uncertainty_method,
            "supersedes": self.supersedes,
            "unresolved_inputs": self.unresolved_inputs(),
            "passed": self.passed,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ExperimentRecord":
        if data.get("schema") != SCHEMA:
            raise ProvenanceError(f"unexpected record schema {data.get('schema')!r}")
        record = cls(
            experiment_id=data["experiment_id"],
            phase=int(data["phase"]),
            title=data["title"],
            command=data["command"],
            created_utc=data["created_utc"],
            tools=data.get("tools", {}),
            git=data.get("git", {}),
            readout=data.get("readout", {}),
            benchmark=data.get("benchmark", {}),
            parameters=[Parameter(**p) for p in data.get("parameters", [])],
            artifacts=[Artifact(**a) for a in data.get("artifacts", [])],
            gates=[GateResult(**g) for g in data.get("gates", [])],
            validity=data.get("validity", ""),
            uncertainty_method=data.get("uncertainty_method", ""),
            supersedes=data.get("supersedes"),
            notes=list(data.get("notes", [])),
        )
        return record

    def format_text(self) -> str:
        lines = [
            f"{self.experiment_id}  (P{self.phase})  {self.title}",
            f"  created   {self.created_utc}",
            f"  command   {self.command}",
            f"  git       {self.git.get('commit', '?')[:12]}"
            f"{' DIRTY' if self.git.get('dirty') else ''}",
        ]
        if self.supersedes:
            lines.append(f"  supersedes {self.supersedes}")
        if self.readout:
            lines.append(f"  readout   {self.readout.get('slots')} slots x "
                         f"{self.readout.get('ports')} ports = "
                         f"{self.readout.get('n_features')} features")
        if self.parameters:
            lines.append("  parameters:")
            for p in self.parameters:
                lines.append(f"    [{p.status:<16}] {p.name} = {p.value} {p.unit}"
                             f"   {p.source}")
        if self.gates:
            lines.append("  gates:")
            for g in self.gates:
                lines.append(f"    [{'PASS' if g.passed else 'FAIL'}] {g.name}: "
                             f"{g.value} vs {g.threshold}  {g.detail}")
        unresolved = self.unresolved_inputs()
        if unresolved:
            lines.append(f"  UNRESOLVED: {', '.join(unresolved)}")
        return "\n".join(lines)


def record_path(experiment_id: str, record_dir: Path = DEFAULT_RECORD_DIR) -> Path:
    return Path(record_dir) / f"{validate_id(experiment_id)}.json"


def write_record(record: ExperimentRecord,
                 record_dir: Path = DEFAULT_RECORD_DIR) -> Path:
    """Write once. An existing id is an error, never an overwrite."""
    path = record_path(record.experiment_id, record_dir)
    if path.exists():
        raise ProvenanceError(
            f"{record.experiment_id} already exists at {path}; experiment "
            "records are append-only, use a new id"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record.to_dict(), indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    return path


def load_record(path: Path) -> ExperimentRecord:
    return ExperimentRecord.from_dict(
        json.loads(Path(path).read_text(encoding="utf-8")))


def verify_record(record: ExperimentRecord,
                  repo_root: Path | None = None) -> list[str]:
    """Re-read every referenced file; return the mismatches."""
    root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[1]
    problems: list[str] = []
    for art in record.artifacts:
        path = root / art.path
        if not path.exists():
            problems.append(f"missing artifact: {art.path}")
            continue
        actual = sha256_file(path)
        if actual != art.sha256:
            problems.append(f"artifact changed: {art.path}")
    return problems


def superseded_ids(records) -> set[str]:
    return {r.supersedes for r in records if r.supersedes}


def verify_directory(record_dir: Path = DEFAULT_RECORD_DIR,
                     repo_root: Path | None = None) -> dict:
    """Verify every live record. Superseded records are skipped, not failed."""
    directory = Path(record_dir)
    records = [load_record(p)
               for p in sorted(directory.glob("plan2-kerr-P*-*.json"))]
    stale = superseded_ids(records)
    results = {}
    for record in records:
        if record.experiment_id in stale:
            results[record.experiment_id] = None  # superseded
        else:
            results[record.experiment_id] = verify_record(record, repo_root)
    return results


def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(prog="plan2_kerr.provenance")
    sub = p.add_subparsers(dest="command", required=True)

    v = sub.add_parser("verify", help="re-hash every recorded artifact")
    v.add_argument("--dir", default=str(DEFAULT_RECORD_DIR))

    n = sub.add_parser("next-id", help="lowest unused id for a phase")
    n.add_argument("--phase", type=int, required=True)
    n.add_argument("--dir", default=str(DEFAULT_RECORD_DIR))

    s = sub.add_parser("show", help="print a record")
    s.add_argument("experiment_id")
    s.add_argument("--dir", default=str(DEFAULT_RECORD_DIR))

    e = sub.add_parser("env", help="print the tool versions that would be recorded")

    args = p.parse_args(argv)

    if args.command == "env":
        print(json.dumps({"tools": tool_versions(), "git": git_state()},
                         indent=2, sort_keys=True))
        return 0
    if args.command == "next-id":
        print(next_id(args.phase, Path(args.dir)))
        return 0
    if args.command == "show":
        print(load_record(record_path(args.experiment_id, Path(args.dir))).format_text())
        return 0

    results = verify_directory(Path(args.dir))
    if not results:
        print(f"no experiment records under {args.dir}")
        return 0
    failed = 0
    live = 0
    for experiment_id, problems in results.items():
        if problems is None:
            print(f"[SUPR] {experiment_id}  (superseded)")
            continue
        live += 1
        if problems:
            failed += 1
            print(f"[FAIL] {experiment_id}")
            for problem in problems:
                print(f"         {problem}")
        else:
            print(f"[ OK ] {experiment_id}")
    print(f"\n{live - failed}/{live} live records verify "
          f"({len(results) - live} superseded)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
