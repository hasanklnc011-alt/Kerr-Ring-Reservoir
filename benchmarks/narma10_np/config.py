"""Immutable NARMA-10 benchmark constants.

These values are part of the benchmark contract. Changing any of them changes
the locked seed / data hashes, so a decision record under ``docs/decisions/`` is
required first (see ``const.md``).
"""

from __future__ import annotations

from dataclasses import dataclass

# --- NARMA-10 recurrence -------------------------------------------------------
ORDER: int = 10
"""Memory order of the NARMA system (the "10")."""

ALPHA: float = 0.3
BETA: float = 0.05
GAMMA: float = 1.5
DELTA: float = 0.1
"""Classic NARMA-10 coefficients (Atiya & Parlos / Jaeger convention):

    y[t+1] = ALPHA*y[t] + BETA*y[t]*sum(y[t-ORDER+1 : t+1])
             + GAMMA*u[t-ORDER+1]*u[t] + DELTA
"""

# --- Driving signal ----------------------------------------------------------
INPUT_LOW: float = 0.0
INPUT_HIGH: float = 0.5
"""Driving input u[t] ~ Uniform[INPUT_LOW, INPUT_HIGH], i.i.d."""

# --- Sequence layout -------------------------------------------------------
WASHOUT: int = 200
TRAIN_LEN: int = 3000
TEST_LEN: int = 2000


def total_length(washout: int = WASHOUT, train_len: int = TRAIN_LEN,
                 test_len: int = TEST_LEN) -> int:
    """Total samples generated per trial (a +1 warm sample is added on top)."""
    return washout + train_len + test_len


# --- Seed namespaces --------------------------------------------------------
# Per-trial RNG seeds are derived deterministically from (namespace, master, index)
# via SHA-256 (see signals.derive_seed). Master seeds are fixed constants; the
# blind master is intentionally distinct from the dev master so blind trials can
# never coincide with development trials.
DEV_SEED_NAMESPACE: str = "narma10/dev"
DEV_MASTER_SEED: int = 20260910
N_DEV_SEEDS: int = 5

BLIND_SEED_NAMESPACE: str = "narma10/blind"
BLIND_MASTER_SEED: int = 909_314_159_265_358
N_BLIND_SEEDS: int = 10

# --- Acceptance target ------------------------------------------------------
NMSE_TARGET: float = 0.05
"""Median blind test NMSE must be strictly below this (project acceptance gate)."""
MIN_SEEDS_UNDER_TARGET: int = 8
"""At least this many of the N_BLIND_SEEDS trials must be below NMSE_TARGET."""

# --- Readout --------------------------------------------------------------
DEFAULT_RIDGE_ALPHA: float = 1e-6


@dataclass(frozen=True)
class SeedSpec:
    """A named block of deterministic trials."""

    namespace: str
    master_seed: int
    count: int
    washout: int = WASHOUT
    train_len: int = TRAIN_LEN
    test_len: int = TEST_LEN

    @property
    def sequence_length(self) -> int:
        return total_length(self.washout, self.train_len, self.test_len)


def dev_spec() -> SeedSpec:
    return SeedSpec(DEV_SEED_NAMESPACE, DEV_MASTER_SEED, N_DEV_SEEDS)


def blind_spec() -> SeedSpec:
    return SeedSpec(BLIND_SEED_NAMESPACE, BLIND_MASTER_SEED, N_BLIND_SEEDS)
