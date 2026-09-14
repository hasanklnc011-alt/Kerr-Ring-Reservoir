"""Deterministic local NARMA-10 benchmark skeleton (NumPy implementation).

Phase 2 of the project plan (see ``AGENTS.md``): NARMA-10 data / baseline lock.

.. note::
   A second, standard-library-only skeleton was created concurrently by the
   other agent at ``benchmarks/narma10.py`` + ``benchmarks/metrics.py`` etc.
   This package lives under ``narma10_np`` to avoid clobbering that work; the
   collision and a recommendation are recorded in
   ``docs/coordination/2026-09-10-claude-boot-001.md`` for Astra to arbitrate.

Public surface
--------------
- :mod:`benchmarks.narma10_np.config`          immutable benchmark constants
- :mod:`benchmarks.narma10_np.signals`         deterministic input + NARMA-10 target
- :mod:`benchmarks.narma10_np.dataset`         train / test split builder
- :mod:`benchmarks.narma10_np.manifest`        SHA-256 seed + data manifests
- :mod:`benchmarks.narma10_np.metrics`         NMSE / NRMSE with finiteness guards
- :mod:`benchmarks.narma10_np.readout`         ridge-regression linear readout
- :mod:`benchmarks.narma10_np.evaluate`        state -> NMSE evaluation helpers
- :mod:`benchmarks.narma10_np.candidate_lock`  fail-closed blind-evaluation guard

Nothing in this package talks to Tidy3D or any network service.
"""

from . import config

__all__ = ["config"]
