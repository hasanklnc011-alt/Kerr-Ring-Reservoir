"""Deriving ``epsilon`` from the noise floor, by measurement rather than taste.

G2 left one thing arbitrary. ``Q_floor`` depends on ``epsilon``, the fraction
of a symbol's energy that must survive ``m`` symbols, and ``1/e`` was a
placeholder: loosening it to 0.01 drops the Q requirement 4.6x, which is the
difference between "out of reach" and "comfortable". A number with that much
leverage cannot stay a preference.

The operational question is whether the depth-``m`` residual is still
recoverable once detection noise is on it. That is measured here, not argued:

1. Build the feature set an **ideal** readout would have: delay taps whose
   amplitude decays as a single-pole cavity's would, normalised so that the
   *energy* retention at depth ``m`` is exactly ``epsilon``, expanded to all
   pairwise products.
2. Add per-sample detection noise at the SNR of a modelled photodiode + TIA +
   ADC chain (:class:`DetectionChain`).
3. Fit the same ridge readout on the same dev seeds and the same split, and
   sweep ``epsilon`` until the development gate breaks.

Because step 1 uses an oracle with far more features than the locked 32, the
resulting ``epsilon_min`` is a **necessary condition, not a sufficient one**:
it is the point below which the information is gone even for a perfect
readout. A real 32-feature device will need more, by an amount P3 has to
measure. So the working value carries margin over it.

What the measurement found (2026-09-14, dev seeds):

===========  ==================================
SNR          smallest retention clearing the gate
===========  ==================================
>= 50        1e-4
10 - 20      1e-3
5            nothing clears (SNR itself is the limit)
===========  ==================================

Hence :data:`WORKING_RETENTION` = 1e-2, at least one decade above the measured
floor across the whole plausible SNR range, and ~36x looser than ``1/e``.

One incidental finding worth keeping: a quadratic oracle needs roughly 25-30
input taps to solve NARMA-10 at all (12 taps plateau at NMSE 0.16). The "10"
in NARMA-10 is the recursion order, not the input memory the task demands.
The exponential tail of the decayed taps already carries that, so no separate
correction to ``m`` is needed here.

The closed-form route below (:func:`epsilon_min`) is kept as a cross-check
only. It relies on ``corr(y, s)`` with ``s`` the explicit
``gamma * u[t-ORDER+1] * u[t]`` term, which measures 0.019 and badly
understates the memory the task needs, because NARMA-10's variance is carried
by the recursive part. **Do not use it to set a threshold.**
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from benchmarks.narma10_np import config
from benchmarks.narma10_np.dataset import build_all

#: Elementary charge [C].
Q_ELECTRON = 1.602176634e-19

#: Adopted retention at depth ``m``, replacing the placeholder ``1/e``.
#: One decade of margin over the measured floor; P3 must re-verify it with the
#: real 32-feature model rather than the oracle used to derive it.
WORKING_RETENTION = 1e-2

#: Retention that G2 originally assumed. Kept so the old numbers stay readable.
STRICT_RETENTION = 0.36787944117144233


# --- 1. how much of the target needs the memory -----------------------------

def memory_term(u: np.ndarray, order: int = config.ORDER) -> np.ndarray:
    """The explicit ``gamma * u[t-order+1] * u[t]`` term of NARMA-10."""
    term = np.zeros_like(u)
    term[order - 1:] = config.GAMMA * u[: u.shape[0] - order + 1] * u[order - 1:]
    return term


def memory_correlation(spec: config.SeedSpec | None = None,
                       order: int = config.ORDER) -> float:
    """``corr(y, s)`` over the evaluation window, averaged across dev seeds."""
    trials = build_all(spec or config.dev_spec())
    correlations = []
    for trial in trials:
        window = trial.test_slice
        s = memory_term(trial.u, order)[window]
        y = trial.y[window]
        s = s - s.mean()
        y = y - y.mean()
        denom = float(np.sqrt(np.sum(s ** 2) * np.sum(y ** 2)))
        if denom <= 0:
            continue
        correlations.append(float(np.sum(s * y) / denom))
    if not correlations:
        raise ValueError("no usable trial")
    return float(np.mean(correlations))


# --- 2. what the readout sees ----------------------------------------------

@dataclass(frozen=True)
class DetectionChain:
    """One photodiode plus TIA plus ADC, per port.

    Every field is an explicit input. Nothing here is sourced yet; P1 owns the
    sourced table and :meth:`unresolved` says so out loud.
    """

    optical_power_w: float = 2.5e-3
    """Average power reaching one port. Default: the 10 mW research ceiling
    split over four ports."""

    modulation_depth: float = 0.5
    """Fraction of the port power that the signal actually swings over."""

    responsivity_a_per_w: float = 1.0
    bandwidth_hz: float = 50e9
    tia_noise_a_per_sqrt_hz: float = 20e-12
    adc_bits: int = 8
    adc_full_scale_factor: float = 2.0
    """ADC full scale as a multiple of the mean photocurrent."""

    def mean_photocurrent_a(self) -> float:
        return self.responsivity_a_per_w * self.optical_power_w

    def signal_swing_a(self) -> float:
        return self.modulation_depth * self.mean_photocurrent_a()

    def shot_noise_a(self) -> float:
        return math.sqrt(2.0 * Q_ELECTRON * self.mean_photocurrent_a()
                         * self.bandwidth_hz)

    def thermal_noise_a(self) -> float:
        return self.tia_noise_a_per_sqrt_hz * math.sqrt(self.bandwidth_hz)

    def quantisation_noise_a(self) -> float:
        full_scale = self.adc_full_scale_factor * self.mean_photocurrent_a()
        return full_scale / (2 ** self.adc_bits) / math.sqrt(12.0)

    def total_noise_a(self) -> float:
        return math.sqrt(self.shot_noise_a() ** 2
                         + self.thermal_noise_a() ** 2
                         + self.quantisation_noise_a() ** 2)

    def snr(self) -> float:
        noise = self.total_noise_a()
        if noise <= 0:
            raise ValueError("noise must be positive")
        return self.signal_swing_a() / noise

    def noise_breakdown(self) -> dict:
        total = self.total_noise_a()
        return {
            "shot_a": self.shot_noise_a(),
            "thermal_a": self.thermal_noise_a(),
            "quantisation_a": self.quantisation_noise_a(),
            "total_a": total,
            "dominant": max(
                (("shot", self.shot_noise_a()),
                 ("thermal", self.thermal_noise_a()),
                 ("quantisation", self.quantisation_noise_a())),
                key=lambda pair: pair[1],
            )[0],
            "snr": self.snr(),
            "snr_db": 20.0 * math.log10(self.snr()),
        }

    def unresolved(self) -> list[str]:
        """Which inputs are design choices rather than sourced measurements."""
        return ["optical_power_w", "modulation_depth", "responsivity_a_per_w",
                "tia_noise_a_per_sqrt_hz", "adc_bits", "adc_full_scale_factor"]


# --- 3. the requirement -----------------------------------------------------

@dataclass(frozen=True)
class EpsilonRequirement:
    correlation: float
    snr: float
    noise_nmse_budget: float
    epsilon_min: float
    noise_breakdown: dict

    def to_dict(self) -> dict:
        return {
            "correlation": self.correlation,
            "snr": self.snr,
            "noise_nmse_budget": self.noise_nmse_budget,
            "epsilon_min": self.epsilon_min,
            "noise_breakdown": self.noise_breakdown,
        }


def epsilon_min(correlation: float, snr: float,
                noise_nmse_budget: float) -> float:
    """Closed-form cross-check only. See the module docstring: this understates
    the requirement and must not be used to set a threshold."""
    if not 0.0 < noise_nmse_budget < 1.0:
        raise ValueError("noise_nmse_budget must lie in (0, 1)")
    if snr <= 0:
        raise ValueError("snr must be positive")
    return correlation / (snr * math.sqrt(noise_nmse_budget))


def requirement(chain: DetectionChain | None = None,
                *,
                noise_nmse_budget: float = 0.2 * config.NMSE_TARGET,
                correlation: float | None = None) -> EpsilonRequirement:
    """Full chain: measured correlation + noise model -> ``epsilon_min``.

    ``noise_nmse_budget`` defaults to a fifth of the acceptance target, i.e.
    detection noise may consume 20% of the NMSE budget and no more.
    """
    chain = chain or DetectionChain()
    corr = memory_correlation() if correlation is None else correlation
    snr = chain.snr()
    return EpsilonRequirement(
        correlation=corr,
        snr=snr,
        noise_nmse_budget=noise_nmse_budget,
        epsilon_min=epsilon_min(corr, snr, noise_nmse_budget),
        noise_breakdown=chain.noise_breakdown(),
    )


# --- 4. the operational route: measure it instead of deriving it ------------

def decayed_tap_features(u: np.ndarray, n_taps: int, retention: float,
                         depth: int) -> np.ndarray:
    """Delay taps attenuated so that energy retention at ``depth`` is ``retention``.

    Amplitude decays as ``r**k`` with ``r = retention**(1/(2*depth))``, because
    ``retention`` is defined on **energy** and the feature carries amplitude.
    """
    if not 0.0 < retention <= 1.0:
        raise ValueError("retention must lie in (0, 1]")
    r = retention ** (1.0 / (2.0 * depth))
    out = np.zeros((u.shape[0], n_taps), dtype=np.float64)
    for k in range(n_taps):
        if k == 0:
            out[:, k] = u
        else:
            out[k:, k] = u[:-k] * (r ** k)
    return out


def quadratic_expand(x: np.ndarray) -> np.ndarray:
    """``x`` plus every pairwise product, including squares."""
    n = x.shape[1]
    products = [x]
    for i in range(n):
        products.append(x[:, i:i + 1] * x[:, i:])
    return np.hstack(products)


def score_with_noise(trial, retention: float, snr: float, depth: int,
                     n_taps: int, rng: np.random.Generator) -> float:
    """NMSE of a quadratic oracle over decayed taps, with detection noise."""
    from benchmarks.narma10_np.metrics import nmse
    from benchmarks.narma10_np.readout import fit_ridge

    taps = decayed_tap_features(trial.u, n_taps, retention, depth)
    features = quadratic_expand(taps)

    # Detection noise is applied per feature, relative to that feature's swing.
    scale = features.std(axis=0)
    scale[scale <= 0] = 1.0
    features = features + rng.standard_normal(features.shape) * (scale / snr)

    tr, te = trial.train_slice, trial.test_slice
    readout = fit_ridge(features[tr], trial.y[tr], alpha=1e-8)
    return float(nmse(trial.y[te], readout.predict(features[te])))


def sweep_retention(retentions, *, snr: float, depth: int = config.ORDER,
                    n_taps: int | None = None, seed: int = 20260914) -> list[dict]:
    """Median dev NMSE as a function of the retention at ``depth``."""
    from benchmarks.narma10_np.metrics import median_nmse

    taps = n_taps if n_taps is not None else config.ORDER + 2
    trials = build_all(config.dev_spec())
    rows = []
    for retention in retentions:
        rng = np.random.default_rng(seed)
        scores = [score_with_noise(t, retention, snr, depth, taps, rng)
                  for t in trials]
        rows.append({
            "retention": float(retention),
            "median_nmse": float(median_nmse(scores)),
            "per_seed": [float(s) for s in scores],
            "n_under_target": sum(1 for s in scores if s < config.NMSE_TARGET),
        })
    return rows


def retention_from_sweep(rows: list[dict], budget_nmse: float) -> float | None:
    """Smallest swept retention whose median NMSE still clears the budget."""
    passing = [r["retention"] for r in rows if r["median_nmse"] < budget_nmse]
    return min(passing) if passing else None
