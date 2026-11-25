"""BU regression: python -m unittest discover -s tests -v; no third-party deps."""

import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "EE_Mentorship" /
                       "04_Power_Electronics_VRM_and_Thermal"))

from servo_edge_cascaded_pi_controller import CurrentPI, SpeedPI
from servo_edge_encoder_speed_estimator import SpeedEstimator, encoder_code
from servo_edge_pmsm_dq_plant import MotorConfig, PMSM
from servo_edge_regenerative_dc_link import DCLink
from servo_edge_robot_axis_drive_capstone import DriveGuard, simulate
from servo_edge_voltage_circle_limiter import limit_voltage


class MotorTests(unittest.TestCase):
    def test_torque_and_saliency(self):
        motor = PMSM()
        self.assertAlmostEqual(motor.torque(0,2),0.24)
        salient = PMSM(MotorConfig(ld=0.002,lq=0.001))
        self.assertAlmostEqual(salient.torque(3,2),1.5*4*(0.02*2+0.001*3*2))

    def test_spinning_rotor_back_emf_brakes(self):
        motor = PMSM()
        motor.omega = 100
        motor.step(0,0,0,50e-6)
        self.assertLess(motor.iq,0)
        self.assertLess(motor.omega,100)
        self.assertGreater(motor.theta,0)

    def test_dq_energy_power_balance(self):
        motor = PMSM(MotorConfig(ld=0.0012,lq=0.0009))
        motor.id,motor.iq,motor.omega = 1.0,2.0,50.0
        before = motor.stored_energy_j
        expected_power = 1.5*(3*1+8*2)-1.5*0.4*(1**2+2**2)-0.0001*50**2-0.01*50
        dt = 1e-8
        motor.step(3,8,0.01,dt)
        self.assertAlmostEqual((motor.stored_energy_j-before)/dt,expected_power,delta=0.001)

    def test_rk4_timestep_convergence(self):
        coarse,fine = PMSM(),PMSM()
        for _ in range(200):
            coarse.step(1,3,0.01,50e-6)
        for _ in range(400):
            fine.step(1,3,0.01,25e-6)
        for name in ("id","iq","omega","theta"):
            self.assertAlmostEqual(getattr(coarse,name),getattr(fine,name),delta=1e-6)

    def test_bad_inputs_leave_state_unchanged(self):
        motor = PMSM()
        for args in ((math.nan,0,0,50e-6),(0,0,0,0),(0,0,0,51e-6)):
            with self.assertRaises(ValueError):
                motor.step(*args)
            self.assertEqual((motor.id,motor.iq,motor.omega,motor.theta),(0,0,0,0))
        with self.assertRaises(ValueError):
            MotorConfig(pole_pairs=1.5)


class VoltageTests(unittest.TestCase):
    def test_zero_and_unsaturated_vector(self):
        for vd,vq in ((0,0),(3,4),(-3,4),(3,-4)):
            result = limit_voltage(vd,vq,48)
            self.assertEqual((result.vd,result.vq,result.scale),(vd,vq,1))
            self.assertFalse(result.saturated)

    def test_circle_preserves_direction(self):
        for vd,vq in ((30,40),(-30,40),(30,-40),(-30,-40)):
            result = limit_voltage(vd,vq,48)
            self.assertAlmostEqual(math.hypot(result.vd,result.vq),48*0.9/math.sqrt(3))
            self.assertAlmostEqual(result.vd/result.vq,vd/vq)
            self.assertTrue(result.saturated)

    def test_bus_drop_scales_available_voltage(self):
        full,half = limit_voltage(30,40,48),limit_voltage(30,40,24)
        self.assertAlmostEqual(half.scale,full.scale/2)

    def test_invalid_bus_margin_or_nonfinite(self):
        for args in ((0,0,0,0.9),(1,2,48,0),(1,2,48,1.1),(math.inf,0,48,0.9)):
            with self.assertRaises(ValueError):
                limit_voltage(*args)


class EncoderTests(unittest.TestCase):
    def test_forward_and_backward_wrap(self):
        for old,new,sign in ((65530,4,1),(4,65530,-1)):
            estimator = SpeedEstimator(cutoff_hz=1e6)
            estimator.update(old,0.001)
            result = estimator.update(new,0.001)
            self.assertAlmostEqual(result,sign*10*math.tau/65536/0.001)

    def test_steady_speed_both_directions(self):
        for truth in (-100,100):
            estimator = SpeedEstimator()
            for cycle in range(2000):
                estimator.update(encoder_code(truth*cycle*50e-6),50e-6)
            self.assertAlmostEqual(estimator.speed,truth,delta=0.1)

    def test_aliasing_gap_and_jump_rejected(self):
        estimator = SpeedEstimator()
        estimator.update(0,50e-6)
        for code,dt in ((0,0.01),(32768,50e-6)):
            with self.assertRaises(ValueError):
                estimator.update(code,dt)
            self.assertEqual(estimator.previous,0)
            self.assertEqual(estimator.speed,0)

    def test_bad_codes_dt_and_first_sample(self):
        estimator = SpeedEstimator()
        self.assertEqual(estimator.update(40000,50e-6),0)
        for code,dt in ((-1,50e-6),(65536,50e-6),(1.5,50e-6),(0,0),(0,math.nan)):
            with self.assertRaises(ValueError):
                estimator.update(code,dt)
            self.assertEqual(estimator.previous,40000)


class ControllerTests(unittest.TestCase):
    def test_speed_current_limit_and_no_windup(self):
        pi = SpeedPI()
        for _ in range(1000):
            self.assertEqual(pi.step(1000,0,0.001),6)
        self.assertEqual(pi.integral,0)
        self.assertEqual(pi.step(0,0,0.001),0)

    def test_feedforward_uses_electrical_speed(self):
        result = CurrentPI().step(0,2,2,50,48,50e-6)
        self.assertAlmostEqual(result.vd,-4*50*0.001*2)
        self.assertAlmostEqual(result.vq,4*50*0.02)

    def test_vector_antiwindup_bounded_under_forced_error(self):
        pi = CurrentPI()
        for _ in range(5000):
            result = pi.step(0,0,50,0,12,50e-6)
        self.assertTrue(result.saturated)
        self.assertLess(abs(pi.integral_q),100)
        self.assertLessEqual(math.hypot(result.vd,result.vq),12*0.9/math.sqrt(3)+1e-12)

    def test_invalid_control_inputs_do_not_mutate(self):
        current,speed = CurrentPI(),SpeedPI()
        with self.assertRaises(ValueError):
            current.step(0,0,0,0,0,50e-6)
        with self.assertRaises(ValueError):
            speed.step(math.nan,0,0.001)
        self.assertEqual((current.integral_d,current.integral_q,speed.integral),(0,0,0))


class DCLinkTests(unittest.TestCase):
    def test_ideal_source_supplies_but_cannot_sink(self):
        bus = DCLink()
        bus.step(100,0.001)
        self.assertAlmostEqual(bus.voltage,48)
        self.assertAlmostEqual(bus.source_energy_j,0.1)
        bus.step(-100,0.001)
        self.assertGreater(bus.voltage,48)
        self.assertAlmostEqual(bus.source_energy_j,0.1)

    def test_energy_bookkeeping(self):
        bus = DCLink()
        initial = bus.energy_j
        for cycle in range(3000):
            bus.step(30 if cycle < 1000 else -50,50e-6)
        expected = initial+bus.source_energy_j-bus.inverter_energy_j-bus.brake_energy_j
        self.assertAlmostEqual(bus.energy_j,expected,places=10)
        self.assertGreater(bus.brake_energy_j,0)

    def test_chopper_hysteresis(self):
        bus = DCLink()
        for voltage,on in ((50.5,True),(50,True),(49,False),(50,False)):
            bus.voltage = voltage
            bus.step(0,1e-8)
            self.assertEqual(bus.chopper_on,on)

    def test_brake_failure_energy_raises_voltage(self):
        good,failed = DCLink(),DCLink()
        for _ in range(4000):
            good.step(-50,50e-6)
            failed.step(-50,50e-6,False)
        self.assertLess(good.voltage,51)
        self.assertGreater(failed.voltage,100)
        self.assertEqual(failed.brake_energy_j,0)

    def test_invalid_input_does_not_mutate(self):
        bus = DCLink()
        for power,dt in ((math.nan,50e-6),(0,0),(0,0.002)):
            with self.assertRaises(ValueError):
                bus.step(power,dt)
            self.assertEqual(bus.voltage,48)
        with self.assertRaises(ValueError):
            DCLink(source_v=55)


class GuardTests(unittest.TestCase):
    def test_nominal_and_consecutive_cycles(self):
        guard = DriveGuard()
        self.assertTrue(guard.check(0,48,0,1,100))
        self.assertTrue(guard.check(1,48,0,-1,-100))

    def test_faults_latch_and_disable(self):
        for args,reason in (((0,48,0,0,0,False),"ENCODER"),
                            ((0,61,0,0,0),"BUS"),((0,23,0,0,0),"BUS"),
                            ((0,48,6,6,0),"OVERCURRENT"),
                            ((0,48,0,0,201),"OVERSPEED"),
                            ((0,math.nan,0,0,0),"NONFINITE")):
            guard = DriveGuard()
            self.assertFalse(guard.check(*args))
            self.assertEqual(guard.fault,reason)
            self.assertFalse(guard.check(0,48,0,0,0))
            self.assertFalse(guard.drive_enabled)

    def test_cycle_gap_and_replay(self):
        for cycle in (0,2):
            guard = DriveGuard()
            guard.check(0,48,0,0,0)
            self.assertFalse(guard.check(cycle,48,0,0,0))
            self.assertEqual(guard.fault,"SEQUENCE")


class IntegrationTests(unittest.TestCase):
    def test_rotating_axis_speed_load_and_regeneration(self):
        result = simulate()
        self.assertIsNone(result.fault)
        self.assertEqual(result.cycles,30000)
        self.assertLess(result.speed_rms,2)
        self.assertLess(abs(result.final_speed),0.1)
        self.assertLess(result.max_bus_v,51)
        self.assertLess(result.max_current_a,8)
        self.assertGreater(result.brake_energy_j,0.1)

    def test_injected_encoder_fault_stops_loop(self):
        result = simulate(encoder_fault_cycle=100)
        self.assertEqual(result.fault,"ENCODER")
        self.assertEqual(result.cycles,100)


if __name__ == "__main__":
    unittest.main()
