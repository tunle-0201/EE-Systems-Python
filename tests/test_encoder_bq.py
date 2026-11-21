"""Regression tests BQ: python -m unittest discover -s tests -v.

Standard library only. CRC oracle dung chia da thuc, doc lap voi LFSR encoder.
"""

import math
from pathlib import Path
import random
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "EE_Mentorship" /
                       "08_Robotics_Autonomous_Driving_and_Control"))

from encoder_edge_bissc_crc6 import (
    DATA_BITS, FRAME_BITS, MODULUS, crc6, decode_scd, encode_scd,
)
from encoder_edge_quadrature_abz import AB_CYCLE, QuadratureDecoder, feed_edges
from encoder_edge_robot_joint_feedback_capstone import JointFeedbackMonitor, make_monitor
from encoder_edge_sincos_calibration import SinCosCalibration, sensor_sample, signed_delta


class QuadratureTests(unittest.TestCase):
    def test_all_state_transitions(self):
        for old in range(4):
            for new in range(4):
                with self.subTest(old=old, new=new):
                    decoder = QuadratureDecoder(initial_ab=old)
                    distance = (AB_CYCLE.index(new) - AB_CYCLE.index(old)) % 4
                    expected = {0: 0, 1: 1, 2: 0, 3: -1}[distance]
                    self.assertEqual(decoder.sample(new >> 1, new & 1), expected)
                    self.assertEqual(decoder.count, expected)
                    self.assertEqual(decoder.invalid_transitions, int(distance == 2))

    def test_multiple_turns_and_reverse(self):
        decoder = QuadratureDecoder(lines=100)
        feed_edges(decoder, 1200)
        self.assertEqual(decoder.angle_deg, 1080)
        feed_edges(decoder, -1600)
        self.assertEqual(decoder.angle_deg, -360)

    def test_invalid_edge_requires_rehome(self):
        decoder = QuadratureDecoder()
        decoder.home_at_index()
        decoder.sample(1, 1)
        self.assertEqual(decoder.count, 0)
        self.assertFalse(decoder.homed)
        # Resync to 11, then legitimate 11 -> 10 is +1.
        self.assertEqual(decoder.sample(1, 0), 1)
        decoder.home_at_index()
        self.assertTrue(decoder.homed)
        self.assertEqual(decoder.count, 0)

    def test_bad_inputs(self):
        for lines in (0, -1, 2.5):
            with self.assertRaises(ValueError):
                QuadratureDecoder(lines=lines)
        with self.assertRaises(ValueError):
            QuadratureDecoder().sample(2, 0)


class SinCosTests(unittest.TestCase):
    def setUp(self):
        self.cal = SinCosCalibration.calibrate(sensor_sample(k) for k in range(360))

    def test_unseen_angles_and_quadrants(self):
        for truth in (0.37, 89.8, 90.2, 180.6, 270.4, 359.9):
            self.assertAlmostEqual(
                signed_delta(self.cal.angle(*sensor_sample(truth)), truth), 0, places=10)

    def test_noise_after_calibration(self):
        rng = random.Random(221)
        errors = []
        for truth in range(360):
            s, c = sensor_sample(truth)
            angle = self.cal.angle(s + rng.gauss(0, 0.0005), c + rng.gauss(0, 0.0005))
            errors.append(signed_delta(angle, truth))
        rms = math.sqrt(sum(e * e for e in errors) / len(errors))
        self.assertLess(rms, 0.04)

    def test_wrap_both_directions(self):
        self.assertEqual(signed_delta(1, 359), 2)
        self.assertEqual(signed_delta(359, 1), -2)
        self.assertEqual(signed_delta(20, 740), 0)  # Full turns are unobservable.

    def test_invalid_amplitude_and_nonfinite(self):
        for point in ((0.18, -0.09), (100, 100), (math.nan, 0), (0, math.inf)):
            with self.assertRaises(ValueError):
                self.cal.angle(*point)

    def test_invalid_calibration(self):
        for points in ([], [(0, 0)] * 8, [(math.nan, 1)] * 8):
            with self.assertRaises(ValueError):
                SinCosCalibration.calibrate(points)
        with self.assertRaises(ValueError):
            SinCosCalibration(0, 0, -1, 1)


class BiSSTests(unittest.TestCase):
    def test_crc_against_polynomial_long_division(self):
        rng = random.Random(222)
        for data in [0, 1, 3, (1 << DATA_BITS) - 1] + [
            rng.randrange(1 << DATA_BITS) for _ in range(256)
        ]:
            remainder = data << 6
            while remainder.bit_length() >= 7:
                remainder ^= 0x43 << (remainder.bit_length() - 7)
            self.assertEqual(crc6(data, DATA_BITS), remainder)
        # Hand-divided data 0b11: (3 << 6) mod 0x43 = 5; inverted = 58.
        frame = encode_scd(0)
        self.assertEqual(frame[:18], (0,) * 18)
        self.assertEqual(frame[18:20], (1, 1))
        self.assertEqual(frame[20:], (1, 1, 1, 0, 1, 0))

    def test_extreme_positions_and_all_statuses(self):
        for position in (0, 1, MODULUS // 4, MODULUS - 1):
            for nerror in (0, 1):
                for nwarning in (0, 1):
                    result = decode_scd(encode_scd(position, nerror, nwarning))
                    self.assertEqual(result.position, position)
                    self.assertEqual(result.healthy, bool(nerror and nwarning))

    def test_every_single_bit_corruption(self):
        for position in (0, 12345, MODULUS - 1):
            frame = encode_scd(position)
            for index in range(FRAME_BITS):
                corrupt = list(frame)
                corrupt[index] ^= 1
                with self.assertRaises(ValueError):
                    decode_scd(corrupt)

    def test_malformed_frames(self):
        for frame in ((), (0,) * 25, (0,) * 27, (2,) * 26):
            with self.assertRaises(ValueError):
                decode_scd(frame)
        for position in (-1, MODULUS, 1.5):
            with self.assertRaises(ValueError):
                encode_scd(position)


class MonitorTests(unittest.TestCase):
    def test_startup_requires_homing_and_valid_data(self):
        with self.assertRaises(ValueError):
            JointFeedbackMonitor(QuadratureDecoder())
        monitor = make_monitor()
        self.assertFalse(monitor.torque_enabled)
        self.assertFalse(monitor.update(0, None))
        self.assertTrue(monitor.update(0.001, encode_scd(0)))

    def test_crc_rejected_then_recovery(self):
        monitor = make_monitor()
        self.assertTrue(monitor.update(0, encode_scd(0)))
        broken = list(encode_scd(0))
        broken[0] ^= 1
        self.assertFalse(monitor.update(0.001, broken))
        self.assertEqual(monitor.last_good, 0)
        self.assertEqual(monitor.rejected_frames, 1)
        self.assertTrue(monitor.update(0.002, encode_scd(0)))

    def test_sensor_status_rejected(self):
        for status in ((0, 1), (1, 0)):
            monitor = make_monitor()
            self.assertFalse(monitor.update(0, encode_scd(0, *status)))
            self.assertIsNone(monitor.last_good)

    def test_timeout_boundary_and_late_healthy_frame(self):
        for late_frame in (None, encode_scd(0)):
            monitor = make_monitor()
            self.assertTrue(monitor.update(0, encode_scd(0)))
            self.assertFalse(monitor.update(0.004999, None))
            self.assertIsNone(monitor.fault)
            self.assertFalse(monitor.update(0.005, late_frame))
            self.assertEqual(monitor.fault, "TIMEOUT")
            self.assertFalse(monitor.update(0.006, encode_scd(0)))

    def test_startup_timeout(self):
        monitor = make_monitor()
        self.assertFalse(monitor.update(0.005, encode_scd(0)))
        self.assertEqual(monitor.fault, "TIMEOUT")

    def test_stuck_absolute_detected_and_latched(self):
        monitor = make_monitor()
        monitor.update(0, encode_scd(0))
        for tick in range(1, 4):
            feed_edges(monitor.decoder, 10)
            self.assertFalse(monitor.update(tick * 0.001, encode_scd(0)))
        self.assertEqual(monitor.fault, "DISAGREEMENT")
        actual = round(monitor.decoder.angle_deg / 360 * MODULUS) % MODULUS
        self.assertFalse(monitor.update(0.004, encode_scd(actual)))

    def test_single_disagreement_recovers(self):
        monitor = make_monitor()
        self.assertFalse(monitor.update(0, encode_scd(MODULUS // 4)))
        self.assertEqual(monitor.mismatches, 1)
        self.assertTrue(monitor.update(0.001, encode_scd(0)))
        self.assertEqual(monitor.mismatches, 0)

    def test_quadrature_loss_latches_immediately(self):
        monitor = make_monitor()
        monitor.update(0, encode_scd(0))
        monitor.decoder.sample(1, 1)
        self.assertFalse(monitor.update(0.001, encode_scd(0)))
        self.assertEqual(monitor.fault, "QUADRATURE")

    def test_clock_errors(self):
        for timestamp in (0, -0.001, math.nan, math.inf):
            monitor = make_monitor()
            monitor.update(0, encode_scd(0))
            self.assertFalse(monitor.update(timestamp, encode_scd(0)))
            self.assertEqual(monitor.fault, "CLOCK")

    def test_wrap_and_reverse_integration(self):
        monitor = make_monitor()
        cal = SinCosCalibration.calibrate(sensor_sample(k) for k in range(360))
        for tick in range(1000):
            truth = 450 * (1 - math.cos(2 * math.pi * tick / 1000)) / 2
            target = round(truth / 360 * monitor.decoder.counts_per_rev)
            feed_edges(monitor.decoder, target - monitor.decoder.count)
            angle = cal.angle(*sensor_sample(truth))
            frame = encode_scd(round(angle / 360 * MODULUS) % MODULUS)
            self.assertTrue(monitor.update(tick * 0.001, frame))
            self.assertLess(abs(signed_delta(monitor.angle_deg, truth)), 360 / MODULUS)


if __name__ == "__main__":
    unittest.main()
