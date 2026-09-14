"""The locked Plan 2 readout contract.

Decided 2026-09-14 (Hasan): **8 mask slots x 4 physical ports = 32 features**,
amending the Plan 2 ADR section 4, which had fixed 20 slots x 2 ports.

Why these numbers, in one line each:

* **8 slots** — the memory floor is linear in the slot count and blind to the
  port count (:mod:`plan2_kerr.memory_triangle`), so slots are the expensive
  axis. With the measured retention this puts the requirement at
  ``Q_i >= 8.44e5`` (it was ``3.89e6`` under G2's placeholder ``1/e``).
* **4 ports** — the features cut from the slot axis come back here for free in
  the memory constraint. 4 is what a two-ring device can plausibly offer:
  through and drop of each ring.
* **32 features** — above the 30 that this project's own P3 needed under a
  realistic physics profile (:data:`plan2_kerr.feature_floor.PRIOR_ART`).

This module is the single source of truth for those numbers. Anything that
needs them — the candidate lock, the experiment records, the reports — reads
them here rather than restating them.
"""

from __future__ import annotations

from benchmarks.narma10_np.candidate_lock import ReadoutContract

from .memory_triangle import TriangleRequest
from .noise_floor import STRICT_RETENTION, WORKING_RETENTION
from .slot_decision import configuration

#: Mask slots per symbol. The memory floor scales with this.
N_SLOTS = 8

#: Independent physical output ports sampled at slot end.
N_PORTS = 4

#: Readout dimension handed to the ridge.
N_FEATURES = N_SLOTS * N_PORTS

#: Where in the slot the port power is read.
SAMPLING = "slot_end"

#: Inter-symbol digital taps are not allowed: the memory must be optical.
DIGITAL_TAPS = 0

#: Ridge regularisation is chosen inside the training window only.
RIDGE_SELECTION = "train_inner_split"

#: Physics consequences of this choice (m=10, B=50 GHz, 1550 nm, n_g=2.0,
#: critical coupling). Derived, never hand-copied, so the contract cannot
#: drift from the model.
#:
#: The retention is :data:`plan2_kerr.noise_floor.WORKING_RETENTION` = 1e-2,
#: measured against the detection noise floor. G2's original ``1/e`` is kept
#: alongside as ``*_STRICT`` so the earlier numbers stay readable.
_WORKING = configuration(N_SLOTS, N_PORTS,
                         TriangleRequest(retention=WORKING_RETENTION))
_STRICT = configuration(N_SLOTS, N_PORTS,
                        TriangleRequest(retention=STRICT_RETENTION))

RETENTION = WORKING_RETENTION

Q_FLOOR = _WORKING.q_floor
Q_INTRINSIC_REQUIRED = _WORKING.q_intrinsic_required
MAX_LOSS_DB_PER_CM = _WORKING.max_loss_db_per_cm
SYMBOL_TIME_S = _WORKING.symbol_time_s

Q_FLOOR_STRICT = _STRICT.q_floor
Q_INTRINSIC_REQUIRED_STRICT = _STRICT.q_intrinsic_required
MAX_LOSS_DB_PER_CM_STRICT = _STRICT.max_loss_db_per_cm


def contract() -> ReadoutContract:
    """The locked contract, as the candidate lock expects it."""
    return ReadoutContract(
        slots=N_SLOTS,
        ports=N_PORTS,
        n_features=N_FEATURES,
        sampling=SAMPLING,
        digital_taps=DIGITAL_TAPS,
        ridge_selection=RIDGE_SELECTION,
    )


def summary() -> dict:
    """Machine-readable summary for experiment records."""
    return {
        "slots": N_SLOTS,
        "ports": N_PORTS,
        "n_features": N_FEATURES,
        "sampling": SAMPLING,
        "digital_taps": DIGITAL_TAPS,
        "ridge_selection": RIDGE_SELECTION,
        "symbol_time_s": SYMBOL_TIME_S,
        "retention": RETENTION,
        "q_floor": Q_FLOOR,
        "q_intrinsic_required": Q_INTRINSIC_REQUIRED,
        "max_loss_db_per_cm": MAX_LOSS_DB_PER_CM,
        "q_intrinsic_required_at_1_over_e": Q_INTRINSIC_REQUIRED_STRICT,
        "decision": "docs/decisions/2026-09-14-slot-count.md",
        "retention_decision": "docs/decisions/2026-09-14-retention-noise-floor.md",
    }
