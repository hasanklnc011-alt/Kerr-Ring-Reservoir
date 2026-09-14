"""Physical mode selection. No fallback to "the highest n_eff".

The inherited selector took the largest ``n_eff`` (and, for gaps, the largest
two) with no physical test at all. That silently returns a substrate mode, a
cladding mode or a PML artefact whenever the mode of interest is not first,
which is exactly how a solver "works" while producing nonsense.

Here a mode is admissible only if it is TE enough *and* actually lives in the
core. If nothing qualifies, or if two survivors are too close in ``n_eff`` to
tell apart, this raises. Raising is the correct behaviour: the caller then has
no number to misuse.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .solver import ModeSolution


class ModeSelectionError(RuntimeError):
    """No single physically valid mode could be identified."""


@dataclass(frozen=True)
class SelectionCriteria:
    min_te_fraction: float = 0.8
    min_core_confinement: float = 0.5
    degeneracy_tol: float = 1e-3

    def describe(self) -> str:
        return (f"te>={self.min_te_fraction}, "
                f"core>={self.min_core_confinement}, "
                f"degeneracy_tol={self.degeneracy_tol}")


@dataclass(frozen=True)
class SelectedMode:
    mode_index: int
    n_eff: float
    n_group: float | None
    te_fraction: float
    core_confinement: float
    n_candidates: int

    def to_dict(self) -> dict:
        from dataclasses import asdict
        return asdict(self)


def select_te_core_mode(solution: ModeSolution,
                        criteria: SelectionCriteria | None = None) -> SelectedMode:
    """Return the fundamental TE core mode, or raise."""
    crit = criteria or SelectionCriteria()

    admissible = [
        i for i in range(len(solution.n_eff))
        if solution.te_fraction[i] >= crit.min_te_fraction
        and solution.core_confinement[i] >= crit.min_core_confinement
    ]

    if not admissible:
        raise ModeSelectionError(
            f"no mode satisfies {crit.describe()} for {solution.cross_section} "
            f"at {solution.steps_per_wvl} steps/wvl; "
            f"te={np.round(solution.te_fraction, 3).tolist()}, "
            f"core={np.round(solution.core_confinement, 3).tolist()}"
        )

    order = sorted(admissible, key=lambda i: -solution.n_eff[i])
    best = order[0]

    if len(order) > 1:
        runner_up = order[1]
        gap = abs(solution.n_eff[best] - solution.n_eff[runner_up])
        if gap < crit.degeneracy_tol:
            raise ModeSelectionError(
                f"modes {best} and {runner_up} are degenerate within "
                f"{crit.degeneracy_tol} (gap {gap:.2e}); the TE/core criteria "
                "cannot separate them, so no single branch is identified"
            )

    return SelectedMode(
        mode_index=best,
        n_eff=float(solution.n_eff[best]),
        n_group=None if solution.n_group is None else float(solution.n_group[best]),
        te_fraction=float(solution.te_fraction[best]),
        core_confinement=float(solution.core_confinement[best]),
        n_candidates=len(admissible),
    )
