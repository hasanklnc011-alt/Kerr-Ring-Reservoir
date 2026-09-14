"""Shared fixtures for the v2 candidate-lock and blind-path tests."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

from benchmarks.narma10_np import config
from benchmarks.narma10_np import manifest as m
from benchmarks.narma10_np.candidate_lock import ReadoutContract, create_lock

DEV = config.SeedSpec("narma10/lock-dev", 11, 2, washout=10, train_len=30, test_len=15)
BLIND = config.SeedSpec("narma10/lock-blind", 22, 3, washout=10, train_len=30, test_len=15)

#: A minimal but honest candidate: it reads the trial, builds its own features
#: and scores through the public ``evaluate_states`` seam. It is emphatically
#: not ``baseline_delay_scorer``.
CANDIDATE_SOURCE = '''\
"""Synthetic locked candidate used by the blind-path tests."""

import numpy as np

from benchmarks.narma10_np.evaluate import evaluate_states

MARKER = "candidate-v1"


def build_scorer():
    def _score(trial):
        u = trial.u
        feats = np.stack([u, u ** 2, np.roll(u, 1), np.roll(u, 5)], axis=1)
        return evaluate_states(trial, feats)

    return _score
'''

HELPER_SOURCE = '''\
"""A transitively imported helper, frozen by the lock alongside the candidate."""

SCALE = 1.0
'''


def default_readout() -> ReadoutContract:
    return ReadoutContract(
        slots=20, ports=2, n_features=40, sampling="slot_end",
        digital_taps=0, ridge_selection="train_inner_split",
    )


class CandidateFixture:
    """A locked candidate package living in a throwaway directory."""

    def __init__(self, root: Path, *, use_real_manifests: bool = False):
        self.root = Path(root)
        self.pkg_name = f"locked_candidate_{uuid.uuid4().hex[:8]}"
        self.source_root = self.root / self.pkg_name
        self.source_root.mkdir(parents=True, exist_ok=True)
        (self.source_root / "__init__.py").write_text("", encoding="utf-8")
        self.candidate_py = self.source_root / "scorer.py"
        self.candidate_py.write_text(CANDIDATE_SOURCE, encoding="utf-8")
        self.helper_py = self.source_root / "helper.py"
        self.helper_py.write_text(HELPER_SOURCE, encoding="utf-8")

        self.lock_path = self.root / "candidates" / "C001.lock.json"
        self.ledger = self.root / "ledger.json"

        if use_real_manifests:
            self.dev_manifest = m.default_path(config.dev_spec())
            self.blind_manifest = m.default_path(config.blind_spec())
        else:
            self.dev_manifest = self.root / "dev.json"
            self.blind_manifest = self.root / "blind.json"
            m.write_manifest(DEV, self.dev_manifest)
            m.write_manifest(BLIND, self.blind_manifest)

        if str(self.root) not in sys.path:
            sys.path.insert(0, str(self.root))

    @property
    def entry_point(self) -> str:
        return f"{self.pkg_name}.scorer:build_scorer"

    def make_lock(self, *, locked: bool = True, entry_point: str | None = None,
                  readout: ReadoutContract | None = None):
        return create_lock(
            candidate_id="C001",
            description="unit-test candidate",
            entry_point=entry_point or self.entry_point,
            source_root=self.source_root,
            readout=readout or default_readout(),
            dev_manifest_path=self.dev_manifest,
            blind_manifest_path=self.blind_manifest,
            lock_path=self.lock_path,
            locked=locked,
        )

    def cleanup(self) -> None:
        if str(self.root) in sys.path:
            sys.path.remove(str(self.root))
        for name in list(sys.modules):
            if name.startswith(self.pkg_name):
                del sys.modules[name]
