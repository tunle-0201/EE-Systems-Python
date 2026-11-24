"""BT acquisition/control regression: python -m unittest discover -s tests -v."""

import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "EE_Mentorship" /
                       "04_Power_Electronics_VRM_and_Thermal"))

from current_edge_motor_current_loop_capstone import CurrentLoop, PIController, RLPlant, simulate
from current_edge_pwm_sampling_windows import PwmTiming
from current_edge_shunt_afe_calibration import ADCReading, Calibration, ShuntAFE, calibrate, thermal_factor
from current_edge_two_shunt_reconstruction import TwoShuntFrame, reconstruct


class AFETests(unittest.TestCase):
    def test_bipolar_current_and_thermal_compensation(self):
        afe = ShuntAFE()
        calibration = calibrate(afe)
        for temp in (-40, 25, 100, 150):
            for current in (-20.3, -7.7, 0, 4.2, 17.1):
                self.assertAlmostEqual(calibration.decode(afe.convert(current, temp), temp),
                                       current, delta=0.025)

    def test_calibration_removes_gain_and_offset(self):
        afe = ShuntAFE(input_offset_v=0.0004, gain_error=0.02)
        calibration = calibrate(afe)
        current = 17.3
        sample = afe.convert(current)
        uncalibrated = (sample.code / 4095 * 3.3 - 1.65) / 0.05
        self.assertGreater(abs(uncalibrated - current), 0.5)
        self.assertAlmostEqual(calibration.decode(sample), current, delta=0.025)

    def test_shunt_tcr_correction_is_needed(self):
        afe = ShuntAFE()
        calibration = calibrate(afe)
        sample = afe.convert(20, 150)
        self.assertGreater(calibration.decode(sample, 25) - 20, 0.1)
        self.assertAlmostEqual(calibration.decode(sample, 150), 20, delta=0.025)

    def test_adc_clip_and_malformed_codes_rejected(self):
        afe = ShuntAFE()
        calibration = calibrate(afe)
        for sample in (afe.convert(-100), afe.convert(100), ADCReading(-1),
                       ADCReading(4096), ADCReading(2048.5)):
            with self.assertRaises(ValueError):
                calibration.decode(sample)

    def test_invalid_calibration_and_inputs(self):
        for pair in ((ADCReading(100), ADCReading(100)),
                     (ADCReading(200), ADCReading(100)),
                     (ADCReading(100, True), ADCReading(300))):
            with self.assertRaises(ValueError):
                Calibration.fit(*pair)
        with self.assertRaises(ValueError):
            ShuntAFE().convert(math.nan)
        for temp in (-41, 151, math.nan):
            with self.assertRaises(ValueError):
                thermal_factor(temp)


class TimingTests(unittest.TestCase):
    def test_aperture_fits_before_edge(self):
        timing = PwmTiming()
        window = timing.choose(0.6, 0.7)
        self.assertAlmostEqual(window.start_us, 1.5)
        self.assertAlmostEqual(window.end_us, 6.5)
        for start in (window.start_us, window.trigger_us, window.end_us):
            self.assertTrue(timing.valid_at(0.6, 0.7, start))
            self.assertLessEqual(start + timing.aperture_us + timing.deadtime_us, 7.5 + 1e-12)

    def test_blind_duty_and_exact_boundary(self):
        timing = PwmTiming()
        self.assertIsNotNone(timing.choose(0.9, 0.5))
        self.assertIsNone(timing.choose(0.90001, 0.5))
        self.assertIsNone(timing.choose(0.5, 0.95))
        self.assertIsNone(timing.choose(1, 0))
        self.assertIsNotNone(timing.choose(0, 0))

    def test_early_late_and_nonfinite_triggers(self):
        timing = PwmTiming()
        for trigger in (1.499, 6.501, math.nan, math.inf):
            self.assertFalse(timing.valid_at(0.6, 0.7, trigger))

    def test_slower_amplifier_shrinks_window(self):
        self.assertIsNotNone(PwmTiming().choose(0.8, 0.5))
        self.assertIsNone(PwmTiming(settle_us=5).choose(0.8, 0.5))

    def test_bad_timing_and_duty(self):
        for kwargs in ({"period_us": 0}, {"deadtime_us": -1}, {"aperture_us": math.nan}):
            with self.assertRaises(ValueError):
                PwmTiming(**kwargs)
        for duty in (-0.1, 1.1, math.nan):
            with self.assertRaises(ValueError):
                PwmTiming().choose(duty, 0.5)


class CurrentFixture:
    def setUp(self):
        self.afe_a, self.afe_b = ShuntAFE(), ShuntAFE(-70e-6, -0.003)
        self.cal_a, self.cal_b = calibrate(self.afe_a), calibrate(self.afe_b)
        self.timing = PwmTiming()
        self.duties = (0.6, 0.7, 0.4)

    def frame(self, cycle=0, ia=3, ib=-1, trigger=4):
        return TwoShuntFrame(cycle, trigger, self.afe_a.convert(ia, 100), self.afe_b.convert(ib, 100))


class ReconstructionTests(CurrentFixture, unittest.TestCase):
    def test_kcl_and_clarke_known_vector(self):
        result = reconstruct(self.frame(), self.cal_a, self.cal_b, 100, self.duties, self.timing)
        self.assertAlmostEqual(result.ia, 3, delta=0.025)
        self.assertAlmostEqual(result.ib, -1, delta=0.025)
        self.assertAlmostEqual(result.ic, -2, delta=0.04)
        alpha, beta = result.alpha_beta
        self.assertAlmostEqual(alpha, 3, delta=0.025)
        self.assertAlmostEqual(beta, 1 / math.sqrt(3), delta=0.04)

    def test_full_electrical_rotation(self):
        for degree in range(0, 360, 3):
            angle = math.radians(degree)
            ia, ib = 12 * math.sin(angle), 12 * math.sin(angle - 2 * math.pi / 3)
            result = reconstruct(self.frame(ia=ia, ib=ib), self.cal_a, self.cal_b,
                                 100, self.duties, self.timing)
            self.assertAlmostEqual(result.ic, -ia - ib, delta=0.04)

    def test_bad_trigger_clip_or_blind_duty_rejected(self):
        for sample, duties in ((self.frame(trigger=0), self.duties),
                               (self.frame(ia=100), self.duties),
                               (self.frame(), (0.95, 0.7, 0.4))):
            with self.assertRaises(ValueError):
                reconstruct(sample, self.cal_a, self.cal_b, 100, duties, self.timing)

    def test_kcl_does_not_detect_sensor_offset(self):
        sample = self.frame()
        shifted = TwoShuntFrame(0, sample.trigger_us, ADCReading(sample.a.code + 20), sample.b)
        result = reconstruct(shifted, self.cal_a, self.cal_b, 100, self.duties, self.timing)
        self.assertGreater(abs(result.ia - 3), 0.2)
        self.assertAlmostEqual(result.ia + result.ib + result.ic, 0)


class ControlMathTests(unittest.TestCase):
    def test_pi_saturation_without_windup(self):
        pi = PIController()
        for _ in range(1000):
            self.assertEqual(pi.step(100, 50e-6), 6)
        self.assertEqual(pi.integral, 0)
        self.assertEqual(pi.step(0, 50e-6), 0)

    def test_pi_integration_can_unwind(self):
        pi = PIController()
        pi.integral = 10
        self.assertEqual(pi.step(-1, 0.001), 6)
        self.assertLess(pi.integral, 10)
        before = pi.integral
        pi.step(1, 0.001)
        self.assertEqual(pi.integral, before)

    def test_rl_step_matches_analytic_solution(self):
        plant = RLPlant()
        plant.step(4, -2, 0.001)
        self.assertAlmostEqual(plant.alpha, 10 * (1 - math.exp(-0.4)))
        self.assertAlmostEqual(plant.beta, -5 * (1 - math.exp(-0.4)))
        previous = plant.alpha
        plant.step(0, 0, 0.001)
        self.assertAlmostEqual(plant.alpha, previous * math.exp(-0.4))

    def test_invalid_pi_and_plant_do_not_mutate_state(self):
        pi, plant = PIController(), RLPlant()
        with self.assertRaises(ValueError):
            pi.step(math.nan, 0.001)
        self.assertEqual(pi.integral, 0)
        with self.assertRaises(ValueError):
            plant.step(1, 1, 0)
        self.assertEqual((plant.alpha, plant.beta), (0, 0))


class LoopTests(CurrentFixture, unittest.TestCase):
    def test_closed_loop_step_and_reversal(self):
        loop, plant, errors = simulate()
        self.assertIsNone(loop.fault)
        self.assertTrue(loop.drive_enabled)
        self.assertLess(abs(plant.beta + 5), 0.03)
        self.assertLess(max(abs(e) for e in errors), 0.03)

    def test_valid_duties_preserve_sampling_window(self):
        loop = CurrentLoop(self.cal_a, self.cal_b)
        duties = loop.step(self.frame(), 100, self.duties, 100)
        self.assertTrue(loop.drive_enabled)
        self.assertTrue(all(0 <= duty <= 1 for duty in duties))
        self.assertIsNotNone(loop.timing.choose(*duties[:2]))

    def test_missing_and_repeated_cycle_latch(self):
        for next_cycle in (0, 2):
            loop = CurrentLoop(self.cal_a, self.cal_b)
            self.assertIsNotNone(loop.step(self.frame(0), 100, self.duties, 0))
            self.assertIsNone(loop.step(self.frame(next_cycle), 100, self.duties, 0))
            self.assertEqual(loop.fault, "SEQUENCE")
            self.assertIsNone(loop.step(self.frame(1), 100, self.duties, 0))
            self.assertFalse(loop.drive_enabled)
            self.assertEqual(loop.voltage_alpha_beta, (0, 0))

    def test_measured_and_reconstructed_overcurrent(self):
        for ia, ib in ((26, 0), (0, -26), (20, 20)):
            loop = CurrentLoop(self.cal_a, self.cal_b)
            self.assertIsNone(loop.step(self.frame(ia=ia, ib=ib), 100, self.duties, 0))
            self.assertEqual(loop.fault, "OVERCURRENT")

    def test_invalid_measurement_latches(self):
        for sample, duties in ((self.frame(trigger=0), self.duties),
                               (self.frame(ia=100), self.duties),
                               (self.frame(), (0.95, 0.7, 0.4))):
            loop = CurrentLoop(self.cal_a, self.cal_b)
            self.assertIsNone(loop.step(sample, 100, duties, 0))
            self.assertEqual(loop.fault, "MEASUREMENT")
            self.assertIsNone(loop.step(self.frame(1), 100, self.duties, 0))

    def test_nonfinite_reference_latches(self):
        loop = CurrentLoop(self.cal_a, self.cal_b)
        self.assertIsNone(loop.step(self.frame(), 100, self.duties, math.nan))
        self.assertEqual(loop.fault, "INPUT")


if __name__ == "__main__":
    unittest.main()
