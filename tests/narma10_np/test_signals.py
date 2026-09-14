import unittest

import numpy as np

from benchmarks.narma10_np import config
from benchmarks.narma10_np.signals import (
    derive_seed,
    driving_input,
    generate_trial,
    make_rng,
    narma10_target,
    sha256_array,
)


class DeriveSeedTest(unittest.TestCase):
    def test_stable_known_value(self):
        # Locked value; if this changes, every manifest changes.
        self.assertEqual(
            derive_seed(config.DEV_SEED_NAMESPACE, config.DEV_MASTER_SEED, 0),
            11556900618465451879,
        )

    def test_depends_on_all_inputs(self):
        base = derive_seed("ns", 1, 0)
        self.assertNotEqual(base, derive_seed("ns2", 1, 0))
        self.assertNotEqual(base, derive_seed("ns", 2, 0))
        self.assertNotEqual(base, derive_seed("ns", 1, 1))

    def test_range_is_64bit(self):
        s = derive_seed("ns", 1, 5)
        self.assertGreaterEqual(s, 0)
        self.assertLess(s, 2 ** 64)

    def test_negative_index_rejected(self):
        with self.assertRaises(ValueError):
            derive_seed("ns", 1, -1)


class DrivingInputTest(unittest.TestCase):
    def test_deterministic(self):
        a = driving_input(make_rng("ns", 7, 0), 256)
        b = driving_input(make_rng("ns", 7, 0), 256)
        np.testing.assert_array_equal(a, b)

    def test_range_and_dtype(self):
        u = driving_input(make_rng("ns", 7, 0), 4096)
        self.assertEqual(u.dtype, np.float64)
        self.assertTrue(np.all(u >= config.INPUT_LOW))
        self.assertTrue(np.all(u < config.INPUT_HIGH))

    def test_rejects_nonpositive_length(self):
        with self.assertRaises(ValueError):
            driving_input(make_rng("ns", 7, 0), 0)


class Narma10RecurrenceTest(unittest.TestCase):
    def setUp(self):
        self.u = driving_input(make_rng(config.DEV_SEED_NAMESPACE,
                                        config.DEV_MASTER_SEED, 0), 400)
        self.y = narma10_target(self.u)

    def test_warmup_is_zero(self):
        np.testing.assert_array_equal(self.y[: config.ORDER], np.zeros(config.ORDER))

    def test_first_recurrent_sample_closed_form(self):
        # y[10] depends on y[9], window y[0:10] (all zero) and u[0], u[9]:
        # y[10] = gamma*u[10-ORDER]*u[9] + delta = gamma*u[0]*u[9] + delta
        expected = config.GAMMA * self.u[0] * self.u[9] + config.DELTA
        self.assertAlmostEqual(self.y[config.ORDER], expected, places=12)

    def test_second_recurrent_sample_closed_form(self):
        y10 = self.y[10]
        # y[11]: window y[1:11] sums to y[10] only; u terms are u[11-ORDER]=u[1], u[10]
        expected = (config.ALPHA * y10
                    + config.BETA * y10 * y10
                    + config.GAMMA * self.u[1] * self.u[10]
                    + config.DELTA)
        self.assertAlmostEqual(self.y[11], expected, places=12)

    def test_finite(self):
        self.assertTrue(np.all(np.isfinite(self.y)))

    def test_deterministic(self):
        np.testing.assert_array_equal(narma10_target(self.u), self.y)

    def test_rejects_short_input(self):
        with self.assertRaises(ValueError):
            narma10_target(np.zeros(config.ORDER))

    def test_diverging_input_raises(self):
        # A constant large drive pushes the classic recurrence to overflow.
        with self.assertRaises(FloatingPointError):
            narma10_target(np.full(600, 1e3, dtype=np.float64))


class GenerateTrialTest(unittest.TestCase):
    def test_shapes_and_determinism(self):
        u1, y1 = generate_trial(config.BLIND_SEED_NAMESPACE,
                                config.BLIND_MASTER_SEED, 3, 500)
        u2, y2 = generate_trial(config.BLIND_SEED_NAMESPACE,
                                config.BLIND_MASTER_SEED, 3, 500)
        self.assertEqual(u1.shape, (500,))
        np.testing.assert_array_equal(u1, u2)
        np.testing.assert_array_equal(y1, y2)

    def test_dev_and_blind_streams_differ(self):
        u_dev, _ = generate_trial(config.DEV_SEED_NAMESPACE,
                                  config.DEV_MASTER_SEED, 0, 500)
        u_blind, _ = generate_trial(config.BLIND_SEED_NAMESPACE,
                                    config.BLIND_MASTER_SEED, 0, 500)
        self.assertFalse(np.array_equal(u_dev, u_blind))


class Sha256ArrayTest(unittest.TestCase):
    def test_stable_and_sensitive(self):
        a = np.linspace(0, 1, 50)
        self.assertEqual(sha256_array(a), sha256_array(a.copy()))
        b = a.copy()
        b[10] += 1e-12
        self.assertNotEqual(sha256_array(a), sha256_array(b))

    def test_shape_sensitive(self):
        a = np.zeros(6)
        self.assertNotEqual(sha256_array(a.reshape(2, 3)), sha256_array(a))


if __name__ == "__main__":
    unittest.main()
