"""State -> NMSE evaluation helpers.

``evaluate_states`` is the seam the photonic reservoir plugs into: given a state
matrix aligned sample-for-sample with a trial, it fits the ridge readout on the
training window and reports the test-window NMSE.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

from . import config
from .dataset import Narma10Trial, build_all
from .metrics import median_nmse, nmse
from .readout import delay_embedding, fit_ridge

# A scorer maps a trial to its test-window NMSE.
Scorer = Callable[[Narma10Trial], float]


@dataclass(frozen=True)
class TrialScore:
    index: int
    test_nmse: float


@dataclass(frozen=True)
class SpecScore:
    namespace: str
    scores: list[TrialScore]

    @property
    def nmse_values(self) -> list[float]:
        return [s.test_nmse for s in self.scores]

    @property
    def median(self) -> float:
        return median_nmse(self.nmse_values)

    @property
    def n_under_target(self) -> int:
        return sum(1 for v in self.nmse_values if v < config.NMSE_TARGET)

    def meets_acceptance(self) -> bool:
        return (self.median < config.NMSE_TARGET
                and self.n_under_target >= config.MIN_SEEDS_UNDER_TARGET)


def evaluate_states(trial: Narma10Trial, states: np.ndarray,
                    alpha: float = config.DEFAULT_RIDGE_ALPHA) -> float:
    """Fit ridge on the train slice, return NMSE on the test slice."""
    states = np.ascontiguousarray(states, dtype=np.float64)
    if states.ndim == 1:
        states = states[:, None]
    if states.shape[0] != trial.u.shape[0]:
        raise ValueError(
            f"states rows ({states.shape[0]}) must match trial length "
            f"({trial.u.shape[0]})"
        )
    tr, te = trial.train_slice, trial.test_slice
    readout = fit_ridge(states[tr], trial.y[tr], alpha=alpha)
    pred = readout.predict(states[te])
    return nmse(trial.y[te], pred)


def baseline_delay_scorer(n_delays: int = config.ORDER + 2,
                          alpha: float = config.DEFAULT_RIDGE_ALPHA) -> Scorer:
    """A trivial linear scorer over delayed inputs — the skeleton's sanity floor.

    NARMA-10 is nonlinear, so this baseline is expected to sit well above the
    ``NMSE_TARGET``; it exists to exercise the pipeline end to end.
    """

    def _score(trial: Narma10Trial) -> float:
        feats = delay_embedding(trial.u, n_delays)
        return evaluate_states(trial, feats, alpha=alpha)

    return _score


def score_spec(spec: config.SeedSpec, scorer: Scorer | None = None) -> SpecScore:
    scorer = scorer or baseline_delay_scorer()
    trials = build_all(spec)
    scores = [TrialScore(index=t.index, test_nmse=float(scorer(t))) for t in trials]
    return SpecScore(namespace=spec.namespace, scores=scores)
