import math
import unittest

from plan2_kerr import platforms as plat
from plan2_kerr.memory_triangle import (
    TriangleRequest,
    db_per_cm_to_per_m,
    energy_retention,
    evaluate,
    finesse,
    fsr_hz,
    gamma_nonlinear,
    kerr_shift_linewidths,
    linewidth_hz,
    max_loss_db_per_cm,
    max_memory_depth_for_q,
    max_slots_for_q,
    min_drive_bandwidth_for_q,
    omega_of,
    per_m_to_db_per_cm,
    photon_lifetime_s,
    power_for_kerr_shift,
    q_floor_from_memory,
    q_floor_from_slots,
    q_intrinsic_from_loss,
    q_loaded_critical,
    required_intrinsic_q,
    round_trip_length_m,
    symbol_time_from_slots,
    thermal_shift_linewidths,
)


class UnitsTest(unittest.TestCase):
    def test_loss_conversion_roundtrip(self):
        for db in (0.01, 0.1, 1.0, 10.0):
            self.assertAlmostEqual(per_m_to_db_per_cm(db_per_cm_to_per_m(db)), db)

    def test_one_db_per_cm_is_23_per_m(self):
        # 1 dB/cm = 100 dB/m = 100 * ln(10)/10 per metre
        self.assertAlmostEqual(db_per_cm_to_per_m(1.0), 23.0258509, places=5)

    def test_omega_at_1550nm(self):
        self.assertAlmostEqual(omega_of(1.55e-6) / 1e15, 1.2154, places=3)


class MemoryFloorTest(unittest.TestCase):
    def setUp(self):
        self.req = TriangleRequest()

    def test_floor_is_exactly_the_retention_boundary(self):
        """A cavity at the floor retains exactly the requested fraction."""
        q = self.req.q_floor
        retained = energy_retention(q, self.req.symbol_time_s,
                                    self.req.memory_depth)
        self.assertAlmostEqual(retained, self.req.retention, places=9)

    def test_floor_scales_linearly_with_depth(self):
        a = q_floor_from_memory(10, 400e-12)
        b = q_floor_from_memory(20, 400e-12)
        self.assertAlmostEqual(b / a, 2.0)

    def test_floor_scales_linearly_with_symbol_time(self):
        a = q_floor_from_memory(10, 400e-12)
        b = q_floor_from_memory(10, 800e-12)
        self.assertAlmostEqual(b / a, 2.0)

    def test_floor_scales_inversely_with_bandwidth(self):
        a = q_floor_from_slots(10, 20, 50e9)
        b = q_floor_from_slots(10, 20, 100e9)
        self.assertAlmostEqual(a / b, 2.0)

    def test_floor_scales_linearly_with_slots(self):
        a = q_floor_from_slots(10, 20, 50e9)
        b = q_floor_from_slots(10, 10, 50e9)
        self.assertAlmostEqual(a / b, 2.0)

    def test_looser_retention_lowers_the_floor(self):
        strict = q_floor_from_slots(10, 20, 50e9, retention=1 / math.e)
        loose = q_floor_from_slots(10, 20, 50e9, retention=0.01)
        self.assertLess(loose, strict)
        self.assertAlmostEqual(strict / loose, math.log(100.0))

    def test_floor_is_platform_independent(self):
        """No material constant may enter the floor."""
        self.assertEqual(
            q_floor_from_slots(10, 20, 50e9),
            q_floor_from_slots(10, 20, 50e9, wavelength_m=1.55e-6),
        )

    def test_nominal_plan2_floor_value(self):
        """Regression pin on the headline G2 number."""
        self.assertAlmostEqual(self.req.q_floor / 1e6, 4.861, places=2)
        self.assertAlmostEqual(self.req.symbol_time_s * 1e12, 400.0, places=6)

    def test_photon_lifetime_matches_floor(self):
        tau = photon_lifetime_s(self.req.q_floor)
        # retention e^-1 at depth m  =>  tau = m * T_sym
        self.assertAlmostEqual(tau, self.req.memory_depth * self.req.symbol_time_s,
                               places=15)

    def test_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            q_floor_from_memory(0, 1e-10)
        with self.assertRaises(ValueError):
            q_floor_from_memory(10, -1.0)
        with self.assertRaises(ValueError):
            q_floor_from_memory(10, 1e-10, retention=1.0)
        with self.assertRaises(ValueError):
            symbol_time_from_slots(0, 50e9)
        with self.assertRaises(ValueError):
            symbol_time_from_slots(20, 0.0)


class LossCeilingTest(unittest.TestCase):
    def test_loss_and_q_are_inverse(self):
        q = q_intrinsic_from_loss(0.1, 2.0)
        self.assertAlmostEqual(max_loss_db_per_cm(q, 2.0), 0.1, places=12)

    def test_lower_loss_gives_higher_q(self):
        self.assertGreater(q_intrinsic_from_loss(0.01, 2.0),
                           q_intrinsic_from_loss(0.1, 2.0))

    def test_critical_coupling_halves_q(self):
        self.assertAlmostEqual(q_loaded_critical(1e7), 5e6)

    def test_zero_loss_rejected(self):
        with self.assertRaises(ValueError):
            q_intrinsic_from_loss(0.0, 2.0)

    def test_required_loss_for_nominal_plan2(self):
        """The nominal Plan 2 readout demands ultra-low-loss SiN."""
        req = TriangleRequest()
        qi = required_intrinsic_q(req)
        self.assertAlmostEqual(qi, 2 * req.q_floor)
        self.assertLess(max_loss_db_per_cm(qi, 2.0), 0.04)


class GeometryTest(unittest.TestCase):
    def test_finesse_two_ways_agree(self):
        q, r, ng = 1e6, 100e-6, 2.0
        direct = fsr_hz(r, ng) / linewidth_hz(q)
        self.assertAlmostEqual(finesse(q, r, ng), direct, places=6)

    def test_finesse_closed_form(self):
        q, r, ng, lam = 1e6, 100e-6, 2.0, 1.55e-6
        expected = q * lam / (ng * round_trip_length_m(r))
        self.assertAlmostEqual(finesse(q, r, ng) / expected, 1.0, places=6)

    def test_finesse_falls_with_radius_at_fixed_q(self):
        self.assertAlmostEqual(
            finesse(1e6, 100e-6, 2.0) / finesse(1e6, 200e-6, 2.0), 2.0, places=6)


class KerrTest(unittest.TestCase):
    args = dict(q_loaded=1e6, radius_m=100e-6, group_index=2.0,
                n2_m2_per_w=2.4e-19, a_eff_m2=1e-12)

    def test_gamma_units(self):
        g = gamma_nonlinear(2.4e-19, 1e-12)
        self.assertAlmostEqual(g, 2 * math.pi * 2.4e-19 / (1.55e-6 * 1e-12))

    def test_shift_is_linear_in_power(self):
        a = kerr_shift_linewidths(1e-3, **self.args)
        b = kerr_shift_linewidths(2e-3, **self.args)
        self.assertAlmostEqual(b / a, 2.0)

    def test_shift_scales_as_q_squared(self):
        a = kerr_shift_linewidths(1e-3, **{**self.args, "q_loaded": 1e6})
        b = kerr_shift_linewidths(1e-3, **{**self.args, "q_loaded": 2e6})
        self.assertAlmostEqual(b / a, 4.0, places=6)

    def test_bigger_ring_is_worse_at_fixed_q(self):
        """F^2 R scales as 1/R: a larger ring weakens the Kerr shift."""
        small = kerr_shift_linewidths(1e-3, **{**self.args, "radius_m": 100e-6})
        big = kerr_shift_linewidths(1e-3, **{**self.args, "radius_m": 200e-6})
        self.assertAlmostEqual(small / big, 2.0, places=6)

    def test_power_for_shift_inverts_the_shift(self):
        p = power_for_kerr_shift(0.2, **self.args)
        self.assertAlmostEqual(kerr_shift_linewidths(p, **self.args), 0.2, places=9)


class ThermalTest(unittest.TestCase):
    def test_unresolved_inputs_give_none_not_a_guess(self):
        self.assertIsNone(thermal_shift_linewidths(
            1e-3, 1e6, 100e-6, 2.0, None, 0.01, 1e4))
        self.assertIsNone(thermal_shift_linewidths(
            1e-3, 1e6, 100e-6, 2.0, 2.45e-5, None, 1e4))
        self.assertIsNone(thermal_shift_linewidths(
            1e-3, 1e6, 100e-6, 2.0, 2.45e-5, 0.01, None))

    def test_scales_with_power_when_fully_specified(self):
        a = thermal_shift_linewidths(1e-3, 1e6, 100e-6, 2.0, 2.45e-5, 0.01, 1e4)
        b = thermal_shift_linewidths(2e-3, 1e6, 100e-6, 2.0, 2.45e-5, 0.01, 1e4)
        self.assertAlmostEqual(b / a, 2.0)


class BoundaryTest(unittest.TestCase):
    def setUp(self):
        self.req = TriangleRequest()

    def test_max_slots_inverts_the_floor(self):
        q = self.req.q_floor
        self.assertAlmostEqual(max_slots_for_q(q, self.req), self.req.n_slots,
                               places=6)

    def test_min_bandwidth_inverts_the_floor(self):
        q = self.req.q_floor
        self.assertAlmostEqual(min_drive_bandwidth_for_q(q, self.req) / 1e9,
                               self.req.drive_bandwidth_hz / 1e9, places=3)

    def test_max_depth_inverts_the_floor(self):
        q = self.req.q_floor
        self.assertAlmostEqual(max_memory_depth_for_q(q, self.req),
                               self.req.memory_depth, places=6)

    def test_demonstrated_algaas_q_cannot_carry_20_slots(self):
        """Xie 2020 reports Q_i = 3.52e6; critical coupling halves it."""
        q_loaded = q_loaded_critical(3.52e6)
        self.assertLess(max_slots_for_q(q_loaded, self.req), 10.0)


class PlatformTest(unittest.TestCase):
    def test_status_must_be_known(self):
        with self.assertRaises(ValueError):
            plat.Param(1.0, "m", "definitely-fine", "nowhere")

    def test_unresolved_fields_are_reported(self):
        for platform in plat.PLATFORMS:
            self.assertTrue(platform.unresolved_fields(),
                            "P1 is open; nothing may look fully sourced yet")

    def test_only_the_fetched_value_is_source_supported(self):
        sourced = [
            (p.name, row["name"])
            for p in plat.PLATFORMS
            for row in p.parameter_rows()
            if row["status"] == plat.STATUS_SOURCE
        ]
        self.assertEqual(sourced, [("AlGaAs-on-insulator", "q_intrinsic_reported")])

    def test_parameter_rows_cover_every_field(self):
        rows = plat.SI3N4.parameter_rows()
        self.assertIn("n2_m2_per_w", {r["name"] for r in rows})
        self.assertTrue(all("status" in r for r in rows))


class EvaluateTest(unittest.TestCase):
    def setUp(self):
        self.req = TriangleRequest()

    def test_nominal_plan2_region_is_empty_for_both_candidates(self):
        for platform in plat.PLATFORMS:
            verdict = evaluate(self.req, platform)
            self.assertFalse(verdict.memory_feasible, platform.name)
            self.assertFalse(verdict.feasible, platform.name)
            self.assertIsNone(verdict.required_power_w)

    def test_verdict_always_names_its_unresolved_inputs(self):
        verdict = evaluate(self.req, plat.SI3N4)
        joined = " ".join(verdict.notes)
        self.assertIn("unresolved", joined)
        self.assertIn("Kerr is instantaneous", joined)

    def test_reported_q_is_preferred_over_unsourced_loss(self):
        verdict = evaluate(self.req, plat.ALGAAS_OI)
        self.assertAlmostEqual(verdict.q_ceiling, 3.52e6 / 2)
        self.assertIn("reported device", " ".join(verdict.notes))

    def test_relaxing_the_mask_opens_the_region(self):
        """4 slots instead of 20 fits under the sourced AlGaAsOI device Q."""
        relaxed = TriangleRequest(n_slots=4)
        verdict = evaluate(relaxed, plat.ALGAAS_OI)
        self.assertTrue(verdict.memory_feasible)
        self.assertIsNotNone(verdict.required_power_w)
        self.assertIsNotNone(verdict.q_operating)

    def test_serializable(self):
        d = evaluate(self.req, plat.SI3N4).to_dict()
        self.assertIn("feasible", d)
        self.assertIsInstance(d["notes"], list)


if __name__ == "__main__":
    unittest.main()
