"""Train / test split construction for a single NARMA-10 trial."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import config
from .signals import generate_trial


@dataclass(frozen=True)
class Narma10Trial:
    """One deterministic NARMA-10 sequence with its split boundaries."""

    namespace: str
    master_seed: int
    index: int
    u: np.ndarray
    y: np.ndarray
    washout: int
    train_len: int
    test_len: int

    @property
    def train_slice(self) -> slice:
        return slice(self.washout, self.washout + self.train_len)

    @property
    def test_slice(self) -> slice:
        start = self.washout + self.train_len
        return slice(start, start + self.test_len)

    def check(self) -> None:
        expected = self.washout + self.train_len + self.test_len
        if self.u.shape != (expected,) or self.y.shape != (expected,):
            raise ValueError(
                f"trial length mismatch: expected {expected}, "
                f"got u={self.u.shape} y={self.y.shape}"
            )
        if not (np.all(np.isfinite(self.u)) and np.all(np.isfinite(self.y))):
            raise FloatingPointError("non-finite values in trial data")


def build_trial(spec: config.SeedSpec, index: int) -> Narma10Trial:
    if not 0 <= index < spec.count:
        raise IndexError(f"index {index} out of range for count {spec.count}")
    length = spec.sequence_length
    u, y = generate_trial(spec.namespace, spec.master_seed, index, length)
    trial = Narma10Trial(
        namespace=spec.namespace,
        master_seed=spec.master_seed,
        index=index,
        u=u,
        y=y,
        washout=spec.washout,
        train_len=spec.train_len,
        test_len=spec.test_len,
    )
    trial.check()
    return trial


def build_all(spec: config.SeedSpec) -> list[Narma10Trial]:
    return [build_trial(spec, i) for i in range(spec.count)]
