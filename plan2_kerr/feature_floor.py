"""How few readout features can solve NARMA-10 at all?

G2 gave a Q floor that falls linearly with the mask slot count ``N``. Cutting
``N`` is therefore the cheapest way to make the memory constraint reachable —
but the feature count is ``N x ports``, so cutting ``N`` also shrinks what the
linear readout has to work with. The two floors have to be read together.

This module measures the *task-side* floor with a digital echo-state network:
a leaky-integrator ESN with ``n`` nodes, tanh nonlinearity, and the same ridge
readout, on the same dev seeds and the same 200/3000/2000 split.

Why an ESN and not the photonic model: there is no physical model yet (P2).
The ESN is the standard digital reference the Plan 2 ADR already requires as a
control, it has genuine fading memory, and its nodes are read exactly the way
photonic features would be — through one ridge fit.

**This curve is a reference, NOT a bound.** An ESN is a *generic random*
expansion; a tailored architecture can be far more feature-efficient at the
same feature count. This project's own lineage proves it: the spiral-delay
line solved NARMA-10 with 20 features in the ideal model and 30 features under
a realistic physics profile (see :data:`PRIOR_ART`), where the ESN reference
here needs roughly 300. Reading this curve as a floor would wrongly condemn
any small-feature architecture.

What the curve is good for: it calibrates how much *feature efficiency* an
architecture must have. Matching 30 features to a 300-feature ESN means the
expansion has to be about an order of magnitude better than random.

Development seeds only. The blind suite is untouched.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from benchmarks.narma10_np import config
from benchmarks.narma10_np.dataset import Narma10Trial, build_all
from benchmarks.narma10_np.metrics import median_nmse, nmse
from benchmarks.narma10_np.readout import fit_ridge

#: Ridge candidates. Selection happens strictly inside the training window.
ALPHA_GRID = (1e-9, 1e-8, 1e-7, 1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1)

#: Inner split: the last of the training window is held out to pick alpha.
INNER_VALIDATION_FRACTION = 0.25

#: Hyperparameters chosen by a grid scan on the DEV seeds (2026-09-14).
#: Scanned spectral_radius in {0.7,0.9,1.1,1.3}, leak in {0.2,0.5,1.0},
#: input_scale in {0.2,0.5,1.0} at 40 features; best median NMSE 0.183.
TUNED = {"spectral_radius": 0.9, "leak_rate": 1.0, "input_scale": 0.2}

#: What this project has already achieved on NARMA-10, for calibration.
#: Source: spiral-delay-reservoir line, recorded in the MayOS thread log.
PRIOR_ART = {
    "P2_single_pd_20_slots": {"features": 20, "median_nmse": 0.039716,
                              "note": "ideal coherent model, 8/10 blind seeds"},
    "P3_10pd_x_3slots": {"features": 30, "median_nmse": 0.038246,
                         "note": "nominal physics profile, 9/10 seeds; "
                                 "the 20-feature candidate was eliminated here"},
    "P5_blind": {"features": 30, "median_nmse": 0.038705,
                 "note": "locked candidate, single blind evaluation, 8/10"},
}


@dataclass(frozen=True)
class ESNSpec:
    n_features: int
    spectral_radius: float = 0.9
    input_scale: float = 0.2
    leak_rate: float = 1.0
    bias_scale: float = 0.2
    seed: int = 20260914

    def reservoir(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        rng = np.random.default_rng(self.seed + self.n_features)
        w = rng.standard_normal((self.n_features, self.n_features))
        eigenvalues = np.linalg.eigvals(w)
        radius = float(np.max(np.abs(eigenvalues)))
        if radius > 0:
            w *= self.spectral_radius / radius
        w_in = rng.uniform(-1.0, 1.0, size=self.n_features) * self.input_scale
        bias = rng.uniform(-1.0, 1.0, size=self.n_features) * self.bias_scale
        return w, w_in, bias


def esn_states(trial: Narma10Trial, spec: ESNSpec) -> np.ndarray:
    """Drive the ESN with the trial input and return its state matrix."""
    w, w_in, bias = spec.reservoir()
    state = np.zeros(spec.n_features, dtype=np.float64)
    out = np.empty((trial.u.shape[0], spec.n_features), dtype=np.float64)
    leak = spec.leak_rate
    for t, u in enumerate(trial.u):
        pre = np.tanh(w @ state + w_in * u + bias)
        state = (1.0 - leak) * state + leak * pre
        out[t] = state
    return out


def _select_alpha(states: np.ndarray, trial: Narma10Trial) -> float:
    """Pick the ridge alpha on an inner split of the training window only."""
    tr = trial.train_slice
    x, y = states[tr], trial.y[tr]
    n_val = max(1, int(round(x.shape[0] * INNER_VALIDATION_FRACTION)))
    n_fit = x.shape[0] - n_val
    if n_fit <= states.shape[1] + 1:
        return config.DEFAULT_RIDGE_ALPHA

    best_alpha = ALPHA_GRID[0]
    best_score = float("inf")
    for alpha in ALPHA_GRID:
        readout = fit_ridge(x[:n_fit], y[:n_fit], alpha=alpha)
        try:
            score = nmse(y[n_fit:], readout.predict(x[n_fit:]))
        except ValueError:
            continue
        if score < best_score:
            best_score, best_alpha = score, alpha
    return best_alpha


def score_trial(trial: Narma10Trial, spec: ESNSpec) -> tuple[float, float]:
    """Return (test NMSE, selected alpha) for one trial."""
    states = esn_states(trial, spec)
    alpha = _select_alpha(states, trial)
    tr, te = trial.train_slice, trial.test_slice
    readout = fit_ridge(states[tr], trial.y[tr], alpha=alpha)
    return nmse(trial.y[te], readout.predict(states[te])), alpha


@dataclass(frozen=True)
class FeaturePoint:
    n_features: int
    median_nmse: float
    per_seed: tuple[float, ...]
    n_under_target: int
    alphas: tuple[float, ...]

    @property
    def meets_dev_gate(self) -> bool:
        """Plan 2 P3 development gate: median < 0.04 and >= 4/5 seeds < 0.05."""
        return (self.median_nmse < 0.04
                and self.n_under_target >= 4)

    def to_dict(self) -> dict:
        return {
            "n_features": self.n_features,
            "median_nmse": self.median_nmse,
            "per_seed": list(self.per_seed),
            "n_under_target": self.n_under_target,
            "alphas": list(self.alphas),
            "meets_dev_gate": self.meets_dev_gate,
        }


def sweep(feature_counts, spec_factory=None) -> list[FeaturePoint]:
    """Score the ESN reference at each feature count on the dev seeds."""
    trials = build_all(config.dev_spec())
    points: list[FeaturePoint] = []
    for n in feature_counts:
        spec = (spec_factory(n) if spec_factory is not None else ESNSpec(n_features=n))
        scores, alphas = [], []
        for trial in trials:
            score, alpha = score_trial(trial, spec)
            scores.append(float(score))
            alphas.append(float(alpha))
        points.append(FeaturePoint(
            n_features=n,
            median_nmse=median_nmse(scores),
            per_seed=tuple(scores),
            n_under_target=sum(1 for s in scores if s < config.NMSE_TARGET),
            alphas=tuple(alphas),
        ))
    return points


def esn_reference_point(points: list[FeaturePoint]) -> int | None:
    """Smallest swept feature count at which the ESN reference clears the gate.

    Not a floor for other architectures -- see the module docstring.
    """
    passing = [p.n_features for p in points if p.meets_dev_gate]
    return min(passing) if passing else None


def efficiency_factor(points: list[FeaturePoint], prior_features: int) -> float | None:
    """How much better than a random expansion an architecture must be.

    ``esn_reference / prior_features``: the spiral-delay line hit the gate at
    ``prior_features`` where the generic ESN needs the reference count.
    """
    reference = esn_reference_point(points)
    if reference is None or prior_features <= 0:
        return None
    return reference / prior_features
