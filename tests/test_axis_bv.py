"""BV position/homing regression: python -m unittest discover -s tests -v."""

import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "EE_Mentorship" /
                       "04_Power_Electronics_VRM_and_Thermal"))

from axis_edge_acceleration_feedforward import acceleration_current
from axis_edge_homing_state_machine import HomingFSM, homing_fixture
from axis_edge_motion_supervisor import MotionSupervisor
from axis_edge_position_velocity_cascade import PositionController
from axis_edge_quintic_motion_profile import MotionPoint, QuinticMove
from axis_edge_robot_positioning_capstone import simulate
from servo_edge_pmsm_dq_plant import MotorConfig


class ProfileTests(unittest.TestCase):
    def test_endpoint_position_velocity_acceleration(self):
        for start,target in ((-0.2,0.6),(0.6,-0.4)):
            move = QuinticMove(start,target)
            for time,q in ((0,start),(move.duration,target)):
                point = move.sample(time)
                self.assertAlmostEqual(point.position,q)
                self.assertAlmostEqual(point.velocity,0)
                self.assertAlmostEqual(point.acceleration,0)

    def test_analytic_limits_and_direction(self):
        for distance in (-1,-0.01,0.01,1):
            move = QuinticMove(0,distance,vmax=0.8,amax=2,jmax=10)
            for k in range(1001):
                point = move.sample(move.duration*k/1000)
                self.assertLessEqual(abs(point.velocity),0.8+1e-10)
                self.assertLessEqual(abs(point.acceleration),2+1e-10)
                self.assertLessEqual(abs(point.jerk),10+1e-10)
                self.assertGreaterEqual(point.velocity*distance,-1e-12)

    def test_derivatives_against_finite_difference(self):
        move = QuinticMove(-0.2,0.6)
        t,h = move.duration*0.31,1e-5
        left,right,mid = move.sample(t-h),move.sample(t+h),move.sample(t)
        self.assertAlmostEqual((right.position-left.position)/(2*h),mid.velocity,delta=1e-7)
        self.assertAlmostEqual((right.velocity-left.velocity)/(2*h),mid.acceleration,delta=1e-7)
        self.assertAlmostEqual((right.acceleration-left.acceleration)/(2*h),mid.jerk,delta=1e-6)

    def test_zero_distance_and_outside_time(self):
        stationary = QuinticMove(0.3,0.3)
        self.assertEqual(stationary.duration,0)
        self.assertEqual(stationary.sample(0),MotionPoint(0.3))
        move = QuinticMove(0,1)
        self.assertEqual(move.sample(-1),MotionPoint(0))
        self.assertEqual(move.sample(move.duration+1),MotionPoint(1))

    def test_invalid_limits_and_time(self):
        for kwargs in ({"vmax":0},{"amax":-1},{"jmax":math.nan}):
            with self.assertRaises(ValueError):
                QuinticMove(0,1,**kwargs)
        with self.assertRaises(ValueError):
            QuinticMove(0,1).sample(math.inf)


class HomingTests(unittest.TestCase):
    def test_kinematic_fixture_finds_offset(self):
        fsm,physical,time = homing_fixture()
        self.assertEqual(fsm.state,"HOMED")
        self.assertLess(time,5)
        self.assertLess(abs(fsm.offset-10),0.0002)
        self.assertAlmostEqual(fsm.position(physical+10),-0.2)
        self.assertEqual(fsm.update(time+0.001,physical+10,True),0)

    def test_start_on_switch_backs_off_before_latch(self):
        fsm = HomingFSM()
        fsm.start(0,9.79,True)
        self.assertEqual(fsm.state,"BACKOFF")
        self.assertGreater(fsm.velocity,0)
        fsm.update(0.001,9.81,False)
        self.assertEqual(fsm.state,"LATCH")
        self.assertLess(fsm.velocity,0)

    def test_debounce_requires_consecutive_pressed_samples(self):
        fsm = HomingFSM()
        fsm.start(0,9.8,True)
        fsm.update(0.001,9.81,False)
        for k,pressed in enumerate((True,True,False,True,True),2):
            fsm.update(k*0.001,9.8,pressed)
            self.assertEqual(fsm.state,"LATCH")
        fsm.update(0.007,9.8,True)
        self.assertEqual(fsm.state,"HOMED")

    def test_stuck_switch_times_out_both_states(self):
        for pressed in (False,True):
            fsm = HomingFSM()
            fsm.start(0,10,pressed)
            self.assertEqual(fsm.update(5,10,pressed),0)
            self.assertEqual(fsm.fault,"TIMEOUT")
            self.assertEqual(fsm.update(5.001,10,False),0)
            self.assertEqual(fsm.state,"FAULT")

    def test_raw_travel_and_clock_faults_latch(self):
        for now,raw,reason in ((0,10,"CLOCK_OR_SENSOR"),(0.001,math.nan,"CLOCK_OR_SENSOR"),
                               (0.001,8.9,"TRAVEL")):
            fsm = HomingFSM()
            fsm.start(0,10,False)
            self.assertEqual(fsm.update(now,raw,False),0)
            self.assertEqual(fsm.fault,reason)

    def test_position_unavailable_before_home_and_no_restart(self):
        fsm = HomingFSM()
        with self.assertRaises(ValueError):
            fsm.position(10)
        fsm.start(0,10,False)
        with self.assertRaises(ValueError):
            fsm.start(0.1,10,False)


class CascadeTests(unittest.TestCase):
    def test_velocity_feedforward_plus_position_correction(self):
        controller = PositionController()
        self.assertAlmostEqual(controller.command(MotionPoint(0.5,1),0.49),1.2)
        self.assertEqual(controller.command(MotionPoint(10),0),2)
        self.assertEqual(controller.command(MotionPoint(-10),0),-2)

    def test_position_is_not_shortest_angle_path(self):
        controller = PositionController()
        self.assertGreater(controller.command(MotionPoint(3.1),-3.1),0)
        with self.assertRaises(ValueError):
            controller.command(MotionPoint(math.nan),0)

    def test_acceleration_friction_and_load_units(self):
        config = MotorConfig()
        self.assertAlmostEqual(acceleration_current(MotionPoint(0,1,6),config,0.01),0.0113/0.12)
        self.assertAlmostEqual(acceleration_current(MotionPoint(0,-1,-6),config,-0.01),-0.0113/0.12)

    def test_feedforward_zero_and_invalid_inputs(self):
        self.assertEqual(acceleration_current(MotionPoint(0),MotorConfig()),0)
        with self.assertRaises(ValueError):
            acceleration_current(MotionPoint(0,0,math.nan),MotorConfig())


class SupervisorTests(unittest.TestCase):
    def test_settling_requires_full_50ms_dwell(self):
        supervisor = MotionSupervisor()
        for k in range(51):
            state = supervisor.update(k*0.001,MotionPoint(0.6),0.6,0,True,True)
            self.assertEqual(state,"DONE" if k == 50 else "SETTLING")
        self.assertTrue(supervisor.drive_enabled)

    def test_settling_resets_if_velocity_exceeds_band(self):
        supervisor = MotionSupervisor()
        for k in range(40):
            supervisor.update(k*0.001,MotionPoint(0.6),0.6,0,True,True)
        supervisor.update(0.04,MotionPoint(0.6),0.6,0.2,True,True)
        for k in range(41,91):
            self.assertEqual(supervisor.update(k*0.001,MotionPoint(0.6),0.6,0,True,True),"SETTLING")
        self.assertEqual(supervisor.update(0.091,MotionPoint(0.6),0.6,0,True,True),"DONE")

    def test_following_error_rejects_short_spike_then_trips_at_20ms(self):
        supervisor = MotionSupervisor()
        for k in range(6):
            supervisor.update(k*0.001,MotionPoint(0.2),0,0,True,False)
        supervisor.update(0.006,MotionPoint(0),0,0,True,False)
        self.assertIsNone(supervisor.fault)
        for k in range(7,28):
            supervisor.update(k*0.001,MotionPoint(0.2),0,0,True,False)
        self.assertEqual(supervisor.fault,"FOLLOWING_ERROR")
        self.assertFalse(supervisor.drive_enabled)
        self.assertEqual(supervisor.update(0.028,MotionPoint(0),0,0,True,True),"FAULT")

    def test_home_soft_limit_and_nonfinite_faults(self):
        for reference,position,homed,reason in ((MotionPoint(0),0,False,"NOT_HOMED"),
                                               (MotionPoint(1.01),0,True,"SOFT_LIMIT"),
                                               (MotionPoint(0),-1.01,True,"SOFT_LIMIT"),
                                               (MotionPoint(0),math.nan,True,"NONFINITE")):
            supervisor = MotionSupervisor()
            self.assertEqual(supervisor.update(0,reference,position,0,homed,False),"FAULT")
            self.assertEqual(supervisor.fault,reason)

    def test_soft_limit_endpoints_and_bad_cadence(self):
        for endpoint in (-1,1):
            supervisor = MotionSupervisor()
            self.assertNotEqual(supervisor.update(0,MotionPoint(endpoint),endpoint,0,True,False),"FAULT")
        for now in (0,-1,0.00301):
            supervisor = MotionSupervisor()
            supervisor.update(0,MotionPoint(0),0,0,True,False)
            supervisor.update(now,MotionPoint(0),0,0,True,False)
            self.assertEqual(supervisor.fault,"TIMING")


class IntegrationTests(unittest.TestCase):
    def test_homing_two_position_moves_and_torque_feedforward(self):
        with_ff,without_ff = simulate(),simulate(use_feedforward=False)
        self.assertIsNone(with_ff.fault)
        self.assertIsNone(without_ff.fault)
        self.assertEqual(with_ff.completed_moves,2)
        self.assertLess(abs(with_ff.final_error),0.001)
        self.assertLess(with_ff.peak_error,0.01)
        self.assertLess(with_ff.tracking_rms,without_ff.tracking_rms/2)

    def test_ideal_jam_latches_following_error(self):
        blocked = simulate(jam=True)
        self.assertEqual(blocked.fault,"FOLLOWING_ERROR")
        self.assertEqual(blocked.completed_moves,0)


if __name__ == "__main__":
    unittest.main()
