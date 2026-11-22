"""BR regression tests: python -m unittest discover -s tests -v."""

import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "EE_Mentorship" /
                       "07_Mixed_Signal_Audio_and_Precision_Actuators"))

from strain_edge_ratiometric_adc_filter import AdcReading, MainsRejector, MovingAverage, RatiometricADC
from strain_edge_robot_gripper_force_capstone import GripperForceMonitor
from strain_edge_temperature_calibration import CalibrationPoint, TemperatureCalibration, lab_calibration
from strain_edge_wheatstone_bridge import BridgeSpec, FullBridge


class BridgeTests(unittest.TestCase):
    def test_ideal_bridge_voltage_and_polarity(self):
        bridge = FullBridge(BridgeSpec(zero_ratio=0, zero_tc_per_c=0, span_tc_per_c=0))
        for force in (-100, -50, 0, 50, 100):
            reading = bridge.sample(force)
            self.assertAlmostEqual(reading.differential_v, force * 0.0001, places=13)
            self.assertAlmostEqual(reading.common_mode_v, 2.5)
            self.assertTrue(all(r > 0 for r in reading.resistances_ohm))

    def test_excitation_scaling_cancels_in_ratio(self):
        bridge = FullBridge()
        low, high = bridge.sample(37, 35, 4.5), bridge.sample(37, 35, 5.5)
        self.assertAlmostEqual(high.differential_v / low.differential_v, 5.5 / 4.5)
        self.assertAlmostEqual(low.ratio, high.ratio)

    def test_common_tcr_cancels_in_ratio(self):
        bridge = FullBridge(BridgeSpec(zero_tc_per_c=0, span_tc_per_c=0))
        cold, hot = bridge.sample(60, 20), bridge.sample(60, 50)
        self.assertNotEqual(cold.resistances_ohm, hot.resistances_ohm)
        self.assertAlmostEqual(cold.ratio, hot.ratio)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            BridgeSpec(full_scale_n=0)
        for args in ((math.nan, 20, 5), (0, math.inf, 5), (0, 20, 0), (1e9, 20, 5)):
            with self.assertRaises(ValueError):
                FullBridge().sample(*args)


class ADCTests(unittest.TestCase):
    def test_signed_conversion_and_quantization_error(self):
        adc = RatiometricADC()
        half_lsb_ratio = 0.5 / (adc.scale * adc.gain)
        for ratio in (-0.00213, -0.0009, 0, 0.0008, 0.00213):
            result = adc.quantize(ratio * 5, 5)
            self.assertFalse(result.clipped)
            self.assertLessEqual(abs(result.ratio - ratio), half_lsb_ratio + 1e-16)

    def test_ratiometric_vs_fixed_reference(self):
        adc = RatiometricADC()
        first = adc.quantize(0.002 * 5, 5)
        drifted = adc.quantize(0.002 * 4.5, 4.5)
        fixed_reference = adc.quantize(0.002 * 4.5, 5)
        self.assertEqual(first.ratio, drifted.ratio)
        self.assertAlmostEqual(fixed_reference.ratio / first.ratio, 0.9, places=6)

    def test_clipping_both_rails(self):
        adc = RatiometricADC()
        for voltage in (-1, 1):
            self.assertTrue(adc.quantize(voltage, 5).clipped)
        self.assertFalse(adc.quantize(-5 / 128, 5).clipped)

    def test_invalid_adc_configuration_and_voltage(self):
        for bits in (0, 33, 2.5):
            with self.assertRaises(ValueError):
                RatiometricADC(bits=bits)
        for args in ((0, 0), (math.nan, 5), (0, math.inf)):
            with self.assertRaises(ValueError):
                RatiometricADC().quantize(*args)


class FilterTests(unittest.TestCase):
    def test_warmup_decimation_and_group_delay(self):
        fir = MainsRejector()
        outputs = []
        for k in range(120):
            result = fir.push(float(k))
            if result is not None:
                outputs.append(k)
                self.assertAlmostEqual(result, k - 21)
        self.assertEqual(outputs, list(range(47, 120, 12)))
        self.assertAlmostEqual(fir.GROUP_DELAY_SEC, 21 / 1200)

    def test_50_and_60_hz_rejection(self):
        for frequency in (50, 60):
            fir = MainsRejector()
            errors = []
            for k in range(1200):
                result = fir.push(40 + math.sin(2 * math.pi * frequency * k / 1200))
                if result is not None:
                    errors.append(result - 40)
            self.assertLess(max(abs(e) for e in errors), 1e-11)

    def test_off_frequency_is_not_perfectly_rejected(self):
        fir = MainsRejector()
        errors = []
        for k in range(2400):
            result = fir.push(math.sin(2 * math.pi * 49 * k / 1200))
            if result is not None:
                errors.append(result)
        self.assertGreater(max(abs(e) for e in errors), 1e-4)

    def test_nonfinite_does_not_poison_filter(self):
        average = MovingAverage(2)
        self.assertIsNone(average.push(3))
        for value in (math.nan, math.inf):
            with self.assertRaises(ValueError):
                average.push(value)
        self.assertEqual(average.push(5), 4)


class CalibrationTests(unittest.TestCase):
    def setUp(self):
        self.bridge, self.adc = FullBridge(), RatiometricADC()
        self.calibration = lab_calibration(self.bridge, self.adc)

    def test_unseen_loads_temperatures_and_excitation(self):
        for temp in (20, 27, 35, 43, 50):
            for force in (-37, 0, 17, 37, 63, 100):
                reading = self.bridge.sample(force, temp, 4.7)
                sample = self.adc.quantize(reading.differential_v, 4.7)
                self.assertAlmostEqual(self.calibration.force(sample.ratio, temp), force, delta=0.0001)

    def test_outside_temperature_range_rejected(self):
        for temp in (19.99, 50.01, math.nan, math.inf):
            with self.assertRaises(ValueError):
                self.calibration.force(0, temp)

    def test_invalid_points(self):
        good = CalibrationPoint(20, 0, 0.002, 100)
        for bad in (CalibrationPoint(20, 0, 0.002, 100),
                    CalibrationPoint(50, 0, 0, 100),
                    CalibrationPoint(50, 0, 0.002, 0),
                    CalibrationPoint(50, math.nan, 0.002, 100)):
            with self.assertRaises(ValueError):
                TemperatureCalibration.fit(good, bad)


class GripperTests(unittest.TestCase):
    def setUp(self):
        self.bridge, self.adc = FullBridge(), RatiometricADC()
        self.calibration = lab_calibration(self.bridge, self.adc)
        self.monitor = GripperForceMonitor(self.calibration)

    def sample(self, force=40, temp=20):
        reading = self.bridge.sample(force, temp)
        return self.adc.quantize(reading.differential_v, reading.excitation_v)

    def warmup(self):
        for k in range(48):
            enabled = self.monitor.update(k / 1200, self.sample(), 20)
            self.assertEqual(enabled, k == 47)

    def test_warmup_and_measurement_timestamp(self):
        self.warmup()
        self.assertAlmostEqual(self.monitor.filtered_n, 40, delta=0.0001)
        self.assertAlmostEqual(self.monitor.measurement_time, 47 / 1200 - 0.0175)

    def test_single_sample_overload_before_filter_and_latched(self):
        for force in (-90, 90):
            self.monitor = GripperForceMonitor(self.calibration)
            self.warmup()
            previous_filtered = self.monitor.filtered_n
            self.assertFalse(self.monitor.update(48 / 1200, self.sample(force), 20))
            self.assertEqual(self.monitor.fault, "OVERLOAD")
            self.assertEqual(self.monitor.filtered_n, previous_filtered)
            self.assertFalse(self.monitor.update(49 / 1200, self.sample(), 20))

    def test_adc_clipping_latches(self):
        self.assertFalse(self.monitor.update(0, AdcReading(0, True), 20))
        self.assertEqual(self.monitor.fault, "ADC_CLIP")

    def test_temperature_fault_latches(self):
        self.assertFalse(self.monitor.update(0, self.sample(), 51))
        self.assertEqual(self.monitor.fault, "TEMPERATURE")

    def test_external_sensor_diagnostic_and_bad_ratio(self):
        for sample, sensor_ok in ((self.sample(), False), (AdcReading(math.nan, False), True)):
            monitor = GripperForceMonitor(self.calibration)
            self.assertFalse(monitor.update(0, sample, 20, sensor_ok))
            self.assertEqual(monitor.fault, "SENSOR")

    def test_missing_sample_resets_fir_then_warms_again(self):
        self.warmup()
        self.assertFalse(self.monitor.update(48 / 1200, None, 20))
        self.assertIsNone(self.monitor.filtered_n)
        for k in range(49, 97):
            enabled = self.monitor.update(k / 1200, self.sample(), 20)
            self.assertEqual(enabled, k == 96)
            self.assertIsNone(self.monitor.fault)

    def test_timeout_at_deadline_rejects_late_data(self):
        for late_sample in (None, self.sample()):
            monitor = GripperForceMonitor(self.calibration)
            monitor.update(0, self.sample(), 20)
            self.assertFalse(monitor.update(0.0049, None, 20))
            self.assertIsNone(monitor.fault)
            self.assertFalse(monitor.update(0.005, late_sample, 20))
            self.assertEqual(monitor.fault, "TIMEOUT")
            self.assertFalse(monitor.update(0.006, self.sample(), 20))

    def test_startup_timeout(self):
        self.assertFalse(self.monitor.update(0.005, self.sample(), 20))
        self.assertEqual(self.monitor.fault, "TIMEOUT")

    def test_clock_and_sample_rate_errors(self):
        for now, fault in ((0, "CLOCK"), (-1, "CLOCK"), (math.nan, "CLOCK"),
                           (math.inf, "CLOCK"), (0.001, "TIMING")):
            monitor = GripperForceMonitor(self.calibration)
            monitor.update(0, self.sample(), 20)
            self.assertFalse(monitor.update(now, self.sample(), 20))
            self.assertEqual(monitor.fault, fault)

    def test_full_thermal_and_mains_pipeline(self):
        for k in range(1200):
            t = k / 1200
            temp = 20 + 30 * k / 1199
            force = 40 + math.sin(2 * math.pi * 50 * t) + 0.7 * math.sin(2 * math.pi * 60 * t)
            excitation = 5 + 0.4 * math.sin(2 * math.pi * t)
            reading = self.bridge.sample(force, temp, excitation)
            sample = self.adc.quantize(reading.differential_v, excitation)
            self.monitor.update(t, sample, temp)
            self.assertIsNone(self.monitor.fault)
            if self.monitor.drive_enabled:
                self.assertLess(abs(self.monitor.filtered_n - 40), 0.0001)


if __name__ == "__main__":
    unittest.main()
