"""G2 — the Kerr memory triangle.

Kerr is instantaneous: it supplies nonlinearity, never memory. In a Kerr-only
ring the *only* memory is the cavity energy decay, so the task's required
history depth, the symbol rate and the loaded Q are not three free knobs but
one constraint surface. This module derives that surface in closed form.

Conventions (SI unless a name says otherwise)
---------------------------------------------
* ``omega0 = 2*pi*c/lambda0`` — angular optical frequency.
* ``kappa = omega0 / Q_L`` — **energy** decay rate [1/s]; the field amplitude
  decays at ``kappa/2``. Energy retained after time ``t`` is ``exp(-kappa t)``.
* ``L_rt = 2*pi*R`` — round-trip length of a ring of radius ``R``.
* ``FSR = c / (n_g * L_rt)`` [Hz]; ``FWHM = f0 / Q_L`` [Hz];
  ``F = FSR / FWHM`` — finesse.

Derivations
-----------
**1. Memory floor on Q (platform independent).**
Energy from a symbol delivered ``m`` symbols ago is attenuated by
``exp(-kappa * m * T_sym)``. Requiring at least a fraction ``epsilon`` to
survive gives ``kappa * m * T_sym <= ln(1/epsilon)``, i.e.

    Q_L >= m * omega0 * T_sym / ln(1/epsilon)

With a mask of ``N`` slots per symbol and drive/detection bandwidth
``B_drive`` the fastest usable slot is ``T_slot = 1/B_drive``, so
``T_sym = N / B_drive`` and

    Q_floor = m * omega0 * N / (ln(1/epsilon) * B_drive)

This contains no material constant: **no platform can buy its way out of it.**

**2. Loss ceiling on Q.**
``Q_i = 2*pi*n_g / (lambda0 * alpha_power)`` with ``alpha_power`` in 1/m.
At critical coupling the loaded Q is half the intrinsic Q.

**3. Kerr shift in linewidths.**
``gamma = 2*pi*n2 / (lambda0 * A_eff)`` [1/(W*m)]. On resonance at critical
coupling the intensity build-up is ``P_circ / P_in ~= F / pi``, so the
round-trip nonlinear phase is ``phi = gamma * P_circ * L_rt = 2*gamma*F*R*P_in``
and a round-trip phase ``phi`` shifts the resonance by ``phi/(2*pi)`` of an FSR,
i.e. by ``(phi/(2*pi)) * F`` linewidths:

    rho_Kerr = gamma * F**2 * R * P_in / pi

The ``F/pi`` build-up is the standard high-finesse critical-coupling result; it
is an approximation and is recorded as such.

**4. Thermal shift.**
Same build-up, but driven by *absorbed* power:
``P_abs = 2 * F * R * alpha_abs * P_in`` and ``dT = P_abs * R_th``, giving
``rho_th = (Q_L / n_g) * (dn/dT) * dT`` linewidths. ``alpha_abs`` (the
absorbing part of the loss) and ``R_th`` (thermal resistance) are device
specific; without them this returns ``None`` rather than a guess.

Timescale note: ``tau_th`` is microseconds while ``T_sym`` here is
sub-nanosecond, so the thermal shift follows the *average* power. It is a
quasi-static bias on the operating point, not a per-symbol memory — but a bias
of many linewidths still has to be locked out.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

C_LIGHT = 299_792_458.0  # m/s, exact by definition


# --- unit helpers -----------------------------------------------------------

def db_per_cm_to_per_m(alpha_db_per_cm: float) -> float:
    """Power attenuation [dB/cm] -> [1/m]."""
    return alpha_db_per_cm * 100.0 * math.log(10.0) / 10.0


def per_m_to_db_per_cm(alpha_per_m: float) -> float:
    return alpha_per_m * 10.0 / (math.log(10.0) * 100.0)


def omega_of(wavelength_m: float) -> float:
    return 2.0 * math.pi * C_LIGHT / wavelength_m


def frequency_of(wavelength_m: float) -> float:
    return C_LIGHT / wavelength_m


# --- 1. memory floor --------------------------------------------------------

def q_floor_from_memory(
    memory_depth: int,
    symbol_time_s: float,
    *,
    retention: float = 1.0 / math.e,
    wavelength_m: float = 1.55e-6,
) -> float:
    """Smallest loaded Q whose cavity still holds ``memory_depth`` symbols."""
    if memory_depth <= 0:
        raise ValueError("memory_depth must be positive")
    if symbol_time_s <= 0:
        raise ValueError("symbol_time_s must be positive")
    if not 0.0 < retention < 1.0:
        raise ValueError("retention must lie strictly between 0 and 1")
    return memory_depth * omega_of(wavelength_m) * symbol_time_s / math.log(1.0 / retention)


def symbol_time_from_slots(n_slots: int, drive_bandwidth_hz: float) -> float:
    """Shortest symbol an ``n_slots`` mask can carry at this drive bandwidth."""
    if n_slots <= 0:
        raise ValueError("n_slots must be positive")
    if drive_bandwidth_hz <= 0:
        raise ValueError("drive_bandwidth_hz must be positive")
    return n_slots / drive_bandwidth_hz


def q_floor_from_slots(
    memory_depth: int,
    n_slots: int,
    drive_bandwidth_hz: float,
    *,
    retention: float = 1.0 / math.e,
    wavelength_m: float = 1.55e-6,
) -> float:
    """The platform-independent Q floor of the Kerr-only architecture."""
    t_sym = symbol_time_from_slots(n_slots, drive_bandwidth_hz)
    return q_floor_from_memory(memory_depth, t_sym, retention=retention,
                               wavelength_m=wavelength_m)


def energy_retention(q_loaded: float, symbol_time_s: float, depth: int,
                     *, wavelength_m: float = 1.55e-6) -> float:
    """Fraction of a symbol's energy still stored ``depth`` symbols later."""
    kappa = omega_of(wavelength_m) / q_loaded
    return math.exp(-kappa * depth * symbol_time_s)


def photon_lifetime_s(q_loaded: float, *, wavelength_m: float = 1.55e-6) -> float:
    """Energy 1/e lifetime ``1/kappa``."""
    return q_loaded / omega_of(wavelength_m)


# --- 2. loss ceiling --------------------------------------------------------

def q_intrinsic_from_loss(alpha_db_per_cm: float, group_index: float,
                          *, wavelength_m: float = 1.55e-6) -> float:
    """Intrinsic Q implied by a propagation loss."""
    alpha = db_per_cm_to_per_m(alpha_db_per_cm)
    if alpha <= 0:
        raise ValueError("loss must be positive")
    return 2.0 * math.pi * group_index / (wavelength_m * alpha)


def q_loaded_critical(q_intrinsic: float) -> float:
    """Loaded Q at critical coupling: the bus takes as much as the ring loses."""
    return q_intrinsic / 2.0


# --- 3. ring geometry -------------------------------------------------------

def round_trip_length_m(radius_m: float) -> float:
    return 2.0 * math.pi * radius_m


def fsr_hz(radius_m: float, group_index: float) -> float:
    return C_LIGHT / (group_index * round_trip_length_m(radius_m))


def linewidth_hz(q_loaded: float, *, wavelength_m: float = 1.55e-6) -> float:
    return frequency_of(wavelength_m) / q_loaded


def finesse(q_loaded: float, radius_m: float, group_index: float,
            *, wavelength_m: float = 1.55e-6) -> float:
    return fsr_hz(radius_m, group_index) / linewidth_hz(q_loaded, wavelength_m=wavelength_m)


# --- 4. Kerr and thermal shifts --------------------------------------------

def gamma_nonlinear(n2_m2_per_w: float, a_eff_m2: float,
                    *, wavelength_m: float = 1.55e-6) -> float:
    """Waveguide nonlinear parameter [1/(W*m)]."""
    return 2.0 * math.pi * n2_m2_per_w / (wavelength_m * a_eff_m2)


def buildup_factor(finesse_value: float) -> float:
    """Circulating/input power at resonance, critical coupling (``F/pi``)."""
    return finesse_value / math.pi


def kerr_shift_linewidths(
    input_power_w: float,
    q_loaded: float,
    radius_m: float,
    group_index: float,
    n2_m2_per_w: float,
    a_eff_m2: float,
    *,
    wavelength_m: float = 1.55e-6,
) -> float:
    """Kerr resonance shift, in units of the loaded linewidth."""
    f_val = finesse(q_loaded, radius_m, group_index, wavelength_m=wavelength_m)
    gamma = gamma_nonlinear(n2_m2_per_w, a_eff_m2, wavelength_m=wavelength_m)
    return gamma * f_val ** 2 * radius_m * input_power_w / math.pi


def power_for_kerr_shift(
    target_linewidths: float,
    q_loaded: float,
    radius_m: float,
    group_index: float,
    n2_m2_per_w: float,
    a_eff_m2: float,
    *,
    wavelength_m: float = 1.55e-6,
) -> float:
    """Input power needed to reach ``target_linewidths`` of Kerr shift."""
    unit = kerr_shift_linewidths(1.0, q_loaded, radius_m, group_index,
                                 n2_m2_per_w, a_eff_m2, wavelength_m=wavelength_m)
    return target_linewidths / unit


def thermal_shift_linewidths(
    input_power_w: float,
    q_loaded: float,
    radius_m: float,
    group_index: float,
    dn_dt_per_k: float | None,
    alpha_abs_db_per_cm: float | None,
    thermal_resistance_k_per_w: float | None,
    *,
    wavelength_m: float = 1.55e-6,
) -> float | None:
    """Quasi-static thermo-optic shift in linewidths, or ``None`` if unresolved.

    Returns ``None`` — never a guess — when the absorbing loss fraction or the
    thermal resistance is not available.
    """
    if dn_dt_per_k is None or alpha_abs_db_per_cm is None \
            or thermal_resistance_k_per_w is None:
        return None
    f_val = finesse(q_loaded, radius_m, group_index, wavelength_m=wavelength_m)
    alpha_abs = db_per_cm_to_per_m(alpha_abs_db_per_cm)
    p_circ = buildup_factor(f_val) * input_power_w
    p_abs = p_circ * alpha_abs * round_trip_length_m(radius_m)
    delta_t = p_abs * thermal_resistance_k_per_w
    return q_loaded * dn_dt_per_k * delta_t / group_index


# --- 5. the triangle --------------------------------------------------------

@dataclass(frozen=True)
class TriangleRequest:
    """The task-side constraints. No material constants live here."""

    memory_depth: int = 10          # NARMA-10
    n_slots: int = 20               # Plan 2 mask
    drive_bandwidth_hz: float = 50e9
    retention: float = 1.0 / math.e
    wavelength_m: float = 1.55e-6
    target_kerr_linewidths: float = 0.2
    max_input_power_w: float = 10e-3  # Plan 2 average-power ceiling

    @property
    def symbol_time_s(self) -> float:
        return symbol_time_from_slots(self.n_slots, self.drive_bandwidth_hz)

    @property
    def q_floor(self) -> float:
        return q_floor_from_slots(self.memory_depth, self.n_slots,
                                  self.drive_bandwidth_hz,
                                  retention=self.retention,
                                  wavelength_m=self.wavelength_m)


@dataclass(frozen=True)
class TriangleVerdict:
    platform: str
    q_floor: float
    q_ceiling: float
    symbol_time_s: float
    symbol_rate_baud: float
    slot_time_s: float
    memory_feasible: bool
    q_operating: float | None
    finesse_at_operating: float | None
    required_power_w: float | None
    power_feasible: bool | None
    kerr_at_max_power_linewidths: float | None
    thermal_at_required_power_linewidths: float | None
    notes: tuple[str, ...]

    @property
    def feasible(self) -> bool:
        return bool(self.memory_feasible and self.power_feasible)

    def to_dict(self) -> dict:
        from dataclasses import asdict
        d = asdict(self)
        d["notes"] = list(self.notes)
        d["feasible"] = self.feasible
        return d


def evaluate(request: TriangleRequest, platform) -> TriangleVerdict:
    """Screen one platform against one task request.

    ``platform`` is a :class:`~plan2_kerr.platforms.Platform`.
    """
    notes: list[str] = []
    q_floor = request.q_floor

    q_from_loss = q_intrinsic_from_loss(
        platform.loss_db_per_cm.value, platform.group_index.value,
        wavelength_m=request.wavelength_m,
    )
    reported = getattr(platform, "q_intrinsic_reported", None)
    if reported is not None:
        # A demonstrated device beats a loss figure we did not source.
        q_intrinsic = reported.value
        notes.append(
            f"Q_i from reported device ({reported.value:.3g}); the unsourced "
            f"loss figure would have given {q_from_loss:.3g}"
        )
    else:
        q_intrinsic = q_from_loss

    q_ceiling = q_loaded_critical(q_intrinsic)
    memory_feasible = q_ceiling >= q_floor

    q_op: float | None = None
    f_op: float | None = None
    p_req: float | None = None
    power_feasible: bool | None = None
    kerr_at_max: float | None = None
    thermal: float | None = None

    if memory_feasible:
        # Operate at the memory floor: the smallest Q that satisfies memory,
        # which is also the most tolerant of loss. Kerr grows with Q, so this
        # is the *pessimistic* choice for the nonlinearity check.
        q_op = q_floor
        f_op = finesse(q_op, platform.radius_m.value, platform.group_index.value,
                       wavelength_m=request.wavelength_m)
        p_req = power_for_kerr_shift(
            request.target_kerr_linewidths, q_op, platform.radius_m.value,
            platform.group_index.value, platform.n2_m2_per_w.value,
            platform.a_eff_m2.value, wavelength_m=request.wavelength_m,
        )
        power_feasible = p_req <= request.max_input_power_w
        kerr_at_max = kerr_shift_linewidths(
            request.max_input_power_w, q_op, platform.radius_m.value,
            platform.group_index.value, platform.n2_m2_per_w.value,
            platform.a_eff_m2.value, wavelength_m=request.wavelength_m,
        )
        thermal = thermal_shift_linewidths(
            p_req, q_op, platform.radius_m.value, platform.group_index.value,
            _opt(platform.dn_dt_per_k), _opt(platform.alpha_abs_db_per_cm),
            _opt(platform.thermal_resistance_k_per_w),
            wavelength_m=request.wavelength_m,
        )
        if thermal is None:
            notes.append(
                "thermal shift unresolved: needs the absorbing loss fraction "
                "and the thermal resistance of the actual device"
            )
    else:
        notes.append(
            f"memory floor not reachable: needs Q_L >= {q_floor:.3g}, loss "
            f"allows at most {q_ceiling:.3g} at critical coupling"
        )

    unresolved = platform.unresolved_fields()
    if unresolved:
        notes.append("unresolved platform parameters: " + ", ".join(unresolved))
    notes.append(
        "memory here is cavity decay only; Kerr is instantaneous and adds none"
    )

    return TriangleVerdict(
        platform=platform.name,
        q_floor=q_floor,
        q_ceiling=q_ceiling,
        symbol_time_s=request.symbol_time_s,
        symbol_rate_baud=1.0 / request.symbol_time_s,
        slot_time_s=1.0 / request.drive_bandwidth_hz,
        memory_feasible=memory_feasible,
        q_operating=q_op,
        finesse_at_operating=f_op,
        required_power_w=p_req,
        power_feasible=power_feasible,
        kerr_at_max_power_linewidths=kerr_at_max,
        thermal_at_required_power_linewidths=thermal,
        notes=tuple(notes),
    )


def _opt(param) -> float | None:
    return None if param is None else param.value


# --- 6. where the boundary sits --------------------------------------------

def max_loss_db_per_cm(q_intrinsic: float, group_index: float,
                       *, wavelength_m: float = 1.55e-6) -> float:
    """Inverse of :func:`q_intrinsic_from_loss`."""
    alpha = 2.0 * math.pi * group_index / (wavelength_m * q_intrinsic)
    return per_m_to_db_per_cm(alpha)


def required_intrinsic_q(request: "TriangleRequest") -> float:
    """Intrinsic Q the architecture demands (critical coupling halves it)."""
    return 2.0 * request.q_floor


def max_slots_for_q(q_loaded: float, request: "TriangleRequest") -> float:
    """Largest mask slot count this Q can carry at the request's bandwidth."""
    return (q_loaded * math.log(1.0 / request.retention)
            * request.drive_bandwidth_hz
            / (request.memory_depth * omega_of(request.wavelength_m)))


def min_drive_bandwidth_for_q(q_loaded: float, request: "TriangleRequest") -> float:
    """Slowest drive bandwidth this Q tolerates at the request's slot count."""
    return (request.memory_depth * omega_of(request.wavelength_m) * request.n_slots
            / (math.log(1.0 / request.retention) * q_loaded))


def max_memory_depth_for_q(q_loaded: float, request: "TriangleRequest") -> float:
    """Deepest history this Q holds at the request's symbol time."""
    return (q_loaded * math.log(1.0 / request.retention)
            / (omega_of(request.wavelength_m) * request.symbol_time_s))
