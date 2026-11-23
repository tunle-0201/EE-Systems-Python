"""BS regression: python -m unittest discover -s tests -v; standard library only."""

import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "EE_Mentorship" /
                       "07_Mixed_Signal_Audio_and_Precision_Actuators"))

from rtd_edge_pt100_callendar_van_dusen import resistance, temperature
from rtd_edge_robot_winding_thermal_capstone import TemperatureFrame, WindingThermalMonitor
from rtd_edge_self_heating_pulsed_excitation import ThermalRTD, excitation_on
from rtd_edge_three_wire_ratiometric import RTDReading, ThreeWireAFE, Wiring


def frame(acquired, temp=80):
    return TemperatureFrame(acquired, RTDReading(resistance(temp)))


class CVDTests(unittest.TestCase):
    def test_reference_resistances(self):
        # Explicit nominal values, including negative-T cubic correction.
        for temp, ohm in ((-200, 18.52008), (-100, 60.25584), (0, 100),
                          (100, 138.5055), (500, 280.9775), (850, 390.481125)):
            self.assertAlmostEqual(resistance(temp), ohm, places=8)

    def test_inverse_grid_and_endpoints(self):
        for temp in [-200, 850] + [k / 2 for k in range(-399, 1700, 11)]:
            self.assertAlmostEqual(temperature(resistance(temp)), temp, delta=1e-10)

    def test_monotonic_across_zero(self):
        values = [resistance(temp) for temp in (-1, -0.01, 0, 0.01, 1)]
        self.assertEqual(values, sorted(set(values)))

    def test_out_of_range_and_nonfinite(self):
        for temp in (-201, 851, math.nan, math.inf):
            with self.assertRaises(ValueError):
                resistance(temp)
        for ohm in (-1, 0, 10, 400, math.nan, math.inf):
            with self.assertRaises(ValueError):
                temperature(ohm)


class AFETests(unittest.TestCase):
    def test_balanced_leads_and_return_cancel(self):
        afe = ThreeWireAFE()
        for temp in (-100, 0, 80, 250):
            for wires in (Wiring(0, 0, 0), Wiring(1.2, 1.2, 1.2), Wiring(3, 3, 15)):
                result = afe.convert(resistance(temp), wiring=wires)
                self.assertFalse(result.clipped)
                self.assertLess(abs(result.resistance_ohm - resistance(temp)), 1000 / afe.scale)

    def test_lead_mismatch_residual(self):
        afe = ThreeWireAFE()
        result = afe.convert(resistance(80), wiring=Wiring(1.4, 1.2, 20))
        self.assertAlmostEqual(result.resistance_ohm - resistance(80), 0.2, delta=0.0001)
        self.assertGreater(temperature(result.resistance_ohm) - 80, 0.5)

    def test_current_drift_cancels_electrically(self):
        afe = ThreeWireAFE()
        results = [afe.convert(resistance(80), current_a=current) for current in
                   (0.0004, 0.0005, 0.0006)]
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[1], results[2])

    def test_reference_value_must_be_known(self):
        # Synthetic physical reference is 1001 ohm, receiver assumes 1000 ohm.
        physical = ThreeWireAFE(reference_ohm=1001)
        measured = physical.convert(resistance(80)).resistance_ohm
        wrong_scale = measured * 1000 / 1001
        self.assertGreater(abs(temperature(wrong_scale) - 80), 0.3)

    def test_clip_and_invalid_inputs(self):
        self.assertTrue(ThreeWireAFE().convert(1200).clipped)
        with self.assertRaises(ValueError):
            Wiring(lead_a=-1)
        for kwargs in ({"reference_ohm": 0}, {"bits": 1}, {"bits": 24.5}):
            with self.assertRaises(ValueError):
                ThreeWireAFE(**kwargs)
        for ohm, current in ((100, 0), (0, 0.0005), (math.nan, 0.0005)):
            with self.assertRaises(ValueError):
                ThreeWireAFE().convert(ohm, current)


class HeatingTests(unittest.TestCase):
    def test_zero_current_follows_analytic_rc(self):
        sensor = ThermalRTD(20, tau_sec=0.5)
        measured = sensor.step(80, 0, 0.1)
        self.assertAlmostEqual(measured, 80 + (20 - 80) * math.exp(-0.1 / 0.5))

    def test_dc_power_balance(self):
        sensor = ThermalRTD(80)
        for _ in range(10000):
            sensor.step(80, 0.003, 0.001)
        expected_rise = 1000 * 0.003**2 * resistance(sensor.sensor_temp_c) / 0.4
        self.assertAlmostEqual(sensor.sensor_temp_c - 80, expected_rise, delta=1e-6)

    def test_pulse_schedule_boundaries(self):
        self.assertEqual(sum(excitation_on(k) for k in range(1000)), 100)
        for tick, on in ((0, True), (9, True), (10, False), (99, False), (100, True)):
            self.assertEqual(excitation_on(tick), on)

    def test_pulsed_end_on_bias_lower_than_dc(self):
        dc, pulsed = ThermalRTD(80), ThermalRTD(80)
        for tick in range(10010):
            dc.step(80, 0.003, 0.001)
            pulsed.step(80, 0.003 if excitation_on(tick) else 0, 0.001)
        self.assertGreater(pulsed.sensor_temp_c, 80)
        self.assertLess(pulsed.sensor_temp_c - 80, (dc.sensor_temp_c - 80) * 0.15)

    def test_bad_parameters_do_not_mutate_state(self):
        sensor = ThermalRTD(80)
        for args in ((80, -1, 0.001), (80, math.nan, 0.001), (80, 0, 0),
                     (851, 0, 0.001), (80, 1000, 0.001)):
            with self.assertRaises(ValueError):
                sensor.step(*args)
            self.assertEqual(sensor.sensor_temp_c, 80)
        for args in ((-1, 100, 10), (0, 100, 101), (0.5, 100, 10)):
            with self.assertRaises(ValueError):
                excitation_on(*args)


class MonitorTests(unittest.TestCase):
    def test_startup_disabled_then_valid(self):
        monitor = WindingThermalMonitor()
        self.assertFalse(monitor.drive_enabled)
        self.assertEqual(monitor.current_limit_ratio, 0)
        self.assertTrue(monitor.update(0, frame(0)))
        self.assertEqual(monitor.current_limit_ratio, 1)

    def test_hysteresis_at_exact_thresholds(self):
        monitor = WindingThermalMonitor()
        # 0.5 degC steps stay comfortably within the 10 degC/s slew limit.
        temps = [89, 89.5, 90, 89.5, 89, 88.5, 88, 87.5, 87, 86.5, 86, 85.5, 85]
        for k, temp in enumerate(temps):
            self.assertTrue(monitor.update(k * 0.1, frame(k * 0.1, temp)))
            self.assertEqual(monitor.current_limit_ratio, 0.5 if 2 <= k <= 11 else 1)

    def test_overtemperature_inclusive_and_latched(self):
        for temp in (120, 125):
            monitor = WindingThermalMonitor()
            self.assertFalse(monitor.update(0, frame(0, temp)))
            self.assertEqual(monitor.fault, "OVER_TEMPERATURE")
            self.assertFalse(monitor.update(0.1, frame(0.1, 80)))
            self.assertEqual(monitor.current_limit_ratio, 0)

    def test_slew_uses_acquisition_time(self):
        monitor = WindingThermalMonitor()
        self.assertTrue(monitor.update(0, frame(0, 80)))
        # Arrival interval 200 ms; actual acquisition interval 50 ms -> 20 degC/s.
        self.assertFalse(monitor.update(0.2, frame(0.05, 81)))
        self.assertEqual(monitor.fault, "SLEW")

    def test_repeated_or_backward_acquisition_rejected(self):
        for acquired in (0.05, 0.04):
            monitor = WindingThermalMonitor()
            self.assertTrue(monitor.update(0.05, frame(0.05)))
            self.assertFalse(monitor.update(0.1, frame(acquired)))
            self.assertEqual(monitor.fault, "STALE")

    def test_max_age_boundary(self):
        monitor = WindingThermalMonitor()
        self.assertTrue(monitor.update(0.2, frame(0.05)))  # Exactly 150 ms old.
        monitor = WindingThermalMonitor()
        self.assertFalse(monitor.update(0.2, frame(0.049999)))
        self.assertEqual(monitor.fault, "STALE")

    def test_slew_threshold_boundary(self):
        for new_temp, valid in ((81, True), (81.001, False)):
            monitor = WindingThermalMonitor()
            self.assertTrue(monitor.update(0, frame(0, 80)))
            self.assertEqual(monitor.update(0.1, frame(0.1, new_temp)), valid)

    def test_old_but_new_frame_rejected(self):
        monitor = WindingThermalMonitor()
        self.assertFalse(monitor.update(0.2, frame(0.01)))
        self.assertEqual(monitor.fault, "STALE")

    def test_missing_sample_recovery_before_deadline(self):
        monitor = WindingThermalMonitor()
        monitor.update(0, frame(0))
        self.assertFalse(monitor.update(0.1, None))
        self.assertEqual(monitor.current_limit_ratio, 0)
        self.assertTrue(monitor.update(0.2, frame(0.2)))

    def test_deadline_before_late_healthy_frame(self):
        for late_frame in (None, frame(0.25)):
            monitor = WindingThermalMonitor()
            monitor.update(0, frame(0))
            self.assertFalse(monitor.update(0.249, None))
            self.assertIsNone(monitor.fault)
            self.assertFalse(monitor.update(0.250, late_frame))
            self.assertEqual(monitor.fault, "TIMEOUT")
            self.assertFalse(monitor.update(0.3, frame(0.3)))

    def test_watchdog_uses_acquisition_not_arrival(self):
        monitor = WindingThermalMonitor()
        self.assertTrue(monitor.update(0.14, frame(0)))
        self.assertFalse(monitor.update(0.25, frame(0.25)))
        self.assertEqual(monitor.fault, "TIMEOUT")

    def test_bad_clock_and_future_frame(self):
        for now, acquired in ((-1, 0), (math.nan, 0), (math.inf, 0), (0, 0.01), (0, math.nan)):
            monitor = WindingThermalMonitor()
            self.assertFalse(monitor.update(now, frame(acquired)))
            self.assertEqual(monitor.fault, "CLOCK")
        monitor = WindingThermalMonitor()
        monitor.update(0, frame(0))
        self.assertFalse(monitor.update(0, frame(0)))
        self.assertEqual(monitor.fault, "CLOCK")

    def test_adc_clip_range_and_external_sensor_faults(self):
        for reading, ok, fault in ((RTDReading(100, True), True, "ADC_CLIP"),
                                    (RTDReading(0), True, "SENSOR_RANGE"),
                                    (RTDReading(math.nan), True, "SENSOR_RANGE"),
                                    (RTDReading(100), False, "SENSOR")):
            monitor = WindingThermalMonitor()
            self.assertFalse(monitor.update(0, TemperatureFrame(0, reading), ok))
            self.assertEqual(monitor.fault, fault)

    def test_afe_pipeline_and_thermal_lag(self):
        sensor, afe, monitor = ThermalRTD(80), ThreeWireAFE(), WindingThermalMonitor()
        for tick in range(2000):
            now = (tick + 1) / 1000
            sensed = sensor.step(80 + 0.5 * now, 0.0005 if excitation_on(tick) else 0, 0.001)
            if tick % 100 == 9:
                reading = afe.convert(resistance(sensed))
                self.assertTrue(monitor.update(now, TemperatureFrame(now, reading)))
                self.assertLess(abs(monitor.temperature_c - sensed), 0.0002)
        self.assertLess(sensor.sensor_temp_c, 81)  # Lag still exists despite pulsed excitation.


if __name__ == "__main__":
    unittest.main()
