"""Write the P0 experiment record for the Plan 2 Kerr workspace.

    python scripts/record_p0.py

Append-only: re-running is an error by design. The record pins the benchmark
identity, the locked readout contract and the protocol documents by content
hash, so a later edit to any of them shows up as a verification failure.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmarks.narma10_np import config
from benchmarks.narma10_np import manifest as manifest_mod
from plan2_kerr import provenance as prov
from plan2_kerr import readout_contract as rc

REPO_ROOT = Path(__file__).resolve().parents[1]

DOCS = (
    "studies/plan2-kerr/BENCHMARK-PROTOCOL.md",
    "studies/plan2-kerr/PLATFORM-EVIDENCE.md",
    "studies/plan2-kerr/README.md",
    "docs/decisions/2026-09-14-plan2-kerr-reservoir.md",
    "docs/decisions/2026-09-14-slot-count.md",
    "plan2_kerr/readout_contract.py",
)

MANIFESTS = (
    "manifests/narma10/dev_seeds.sha256.json",
    "manifests/narma10/blind_seeds.sha256.json",
)


SUPERSEDES = "plan2-kerr-P0-0001"
"""P0-0001 was written before the workspace README and the Plan 2 ADR
amendment were final, so its hashes no longer match. Records are append-only:
it is superseded here, not edited."""


def main() -> int:
    experiment_id = prov.next_id(0, REPO_ROOT / prov.DEFAULT_RECORD_DIR)
    supersedes = SUPERSEDES if experiment_id != SUPERSEDES else None

    artifacts = [prov.artifact(REPO_ROOT / p, "input", repo_root=REPO_ROOT)
                 for p in DOCS + MANIFESTS]

    benchmark = {
        "task": "NARMA-10",
        "split": [config.WASHOUT, config.TRAIN_LEN, config.TEST_LEN],
        "dev_seeds": config.N_DEV_SEEDS,
        "blind_seeds": config.N_BLIND_SEEDS,
        "dev_manifest_digest": manifest_mod.load_digest(
            manifest_mod.default_path(config.dev_spec())),
        "blind_manifest_digest": manifest_mod.load_digest(
            manifest_mod.default_path(config.blind_spec())),
        "acceptance": {"median_nmse": config.NMSE_TARGET,
                       "min_seeds_under_target": config.MIN_SEEDS_UNDER_TARGET},
        "shared": "benchmark and blind suite are shared, never copied",
    }

    record = prov.ExperimentRecord(
        experiment_id=experiment_id,
        phase=0,
        title="Plan 2 Kerr workspace, benchmark protocol and readout contract",
        command="python scripts/record_p0.py",
        readout=rc.summary(),
        benchmark=benchmark,
        artifacts=artifacts,
        parameters=[
            prov.Parameter("memory_depth", 10, "symbols", "synthetic",
                           "NARMA-10 task definition"),
            prov.Parameter("drive_bandwidth", 50e9, "Hz", "unresolved",
                           "P1 open: no sourced modulator/detector figure yet"),
            prov.Parameter("retention_epsilon", 1 / 2.718281828459045, "1",
                           "unresolved",
                           "modelling choice; needs a noise/ADC model (G2 open item)"),
            prov.Parameter("wavelength", 1.55e-6, "m", "synthetic",
                           "design choice, telecom band"),
        ],
        gates=[
            prov.GateResult("workspace", "present", "present", True,
                            "studies/plan2-kerr/ with protocol and evidence format"),
            prov.GateResult("experiment_id_scheme", "plan2-kerr-P<n>-<####>",
                            prov.SCHEMA, True, "append-only, hash-verified"),
            prov.GateResult("readout_locked", 32, rc.N_FEATURES, True,
                            f"{rc.N_SLOTS} slots x {rc.N_PORTS} ports"),
            prov.GateResult("blind_safety", "G0 closed", "G0 closed", True,
                            "reserve-before-scoring, single use"),
        ],
        validity="Applies to the Plan 2 Kerr line only. Fixes task, readout, "
                 "controls, gates and record format; fixes no physics.",
        uncertainty_method="none - this record contains no measurement",
        supersedes=supersedes,
        notes=[
            "P0 documentation alone is not technical acceptance (ADR section 2).",
            "Material inputs are unresolved; P1 owns the sourced table.",
            "epsilon = 1/e is still a modelling choice, not a measured threshold.",
            "P0-0001 is superseded: it hashed the protocol documents before "
            "the workspace README and the Plan 2 ADR amendment were final.",
        ],
    )

    path = prov.write_record(record, REPO_ROOT / prov.DEFAULT_RECORD_DIR)
    print(f"wrote {path.relative_to(REPO_ROOT)}")
    print(record.format_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
