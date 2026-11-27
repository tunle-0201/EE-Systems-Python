"""BW regression: python -m unittest discover -s tests -v."""

import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"EE_Mentorship"/
                      "04_Power_Electronics_VRM_and_Thermal"))
from axis_edge_quintic_motion_profile import MotionPoint
from flex_edge_two_inertia_plant import FlexibleShaft,ShaftConfig
from flex_edge_ringdown_identification import identify
from flex_edge_notch_filter import Notch
from flex_edge_dual_encoder_damping import DualEncoderController,TwistGuard
from flex_edge_robot_transmission_capstone import simulate


class PlantTests(unittest.TestCase):
    def test_natural_mode_constants(self):
        config=ShaftConfig()
        self.assertAlmostEqual(config.natural_hz,math.sqrt(5000)/math.tau)
        self.assertAlmostEqual(config.zeta,12.5/(2*math.sqrt(5000)))

    def test_undamped_energy_and_momentum_conserved(self):
        plant=FlexibleShaft(ShaftConfig(damping=0))
        plant.tm=0.01
        initial=plant.energy
        for _ in range(4000):
            plant.step(0,0,0.00025)
        self.assertAlmostEqual(plant.energy,initial,delta=1e-10)
        self.assertAlmostEqual(plant.config.jm*plant.wm+plant.config.jl*plant.wl,0,places=12)

    def test_damper_dissipates_energy(self):
        plant=FlexibleShaft()
        plant.tm=0.01
        previous=plant.energy
        for _ in range(2000):
            plant.step(0,0,0.00025)
            self.assertLessEqual(plant.energy,previous+1e-15)
            previous=plant.energy
        self.assertLess(plant.energy,1e-6)

    def test_rk4_converges_and_bad_inputs_preserve_state(self):
        coarse,fine=FlexibleShaft(),FlexibleShaft()
        for _ in range(400):
            coarse.step(0.001,0,0.00025)
        for _ in range(800):
            fine.step(0.001,0,0.000125)
        self.assertAlmostEqual(coarse.tl,fine.tl,delta=1e-8)
        before=(coarse.tm,coarse.wm,coarse.tl,coarse.wl)
        for args in ((math.nan,0,0.00025),(0,0,0),(0,0,0.001)):
            with self.assertRaises(ValueError):
                coarse.step(*args)
            self.assertEqual((coarse.tm,coarse.wm,coarse.tl,coarse.wl),before)


class IdentificationTests(unittest.TestCase):
    def test_ringdown_identifies_frequency_and_damping(self):
        for stiffness in (0.6,0.8,1.0):
            config=ShaftConfig(stiffness=stiffness)
            result=identify(config)
            self.assertAlmostEqual(result.natural_hz,config.natural_hz,delta=0.005)
            self.assertAlmostEqual(result.zeta,config.zeta,delta=0.0001)
            self.assertLess(result.damped_hz,result.natural_hz)

    def test_unsupported_modes_rejected(self):
        for damping in (0,0.1):
            with self.assertRaises(ValueError):
                identify(ShaftConfig(damping=damping))


class NotchTests(unittest.TestCase):
    def test_dc_center_and_off_center_gain(self):
        notch=Notch(11.25)
        self.assertAlmostEqual(notch.gain(0),1,places=10)
        self.assertAlmostEqual(notch.gain(2000),1,places=10)
        self.assertLess(notch.gain(11.25),1e-9)
        self.assertGreater(notch.gain(13.5),0.3)

    def test_streaming_sinusoid_matches_center_rejection(self):
        notch=Notch(11.25)
        tail=[]
        for k in range(12000):
            value=notch.push(math.sin(math.tau*11.25*k/4000))
            if k>=8000:
                tail.append(value)
        self.assertLess(max(abs(v) for v in tail),1e-8)

    def test_dc_step_settles_to_unity(self):
        notch=Notch(11.25)
        for _ in range(12000):
            result=notch.push(1)
        self.assertAlmostEqual(result,1,places=9)

    def test_bad_input_does_not_poison_delays(self):
        notch=Notch(11.25)
        notch.push(1)
        before=(notch.x1,notch.x2,notch.y1,notch.y2)
        with self.assertRaises(ValueError):
            notch.push(math.nan)
        self.assertEqual((notch.x1,notch.x2,notch.y1,notch.y2),before)
        for f in (0,2000,math.inf):
            with self.assertRaises(ValueError):
                Notch(f)


class ControllerTests(unittest.TestCase):
    def test_relative_damping_sign_and_magnitude(self):
        controller=DualEncoderController()
        reference=MotionPoint(0)
        self.assertAlmostEqual(controller.command(reference,0,1,0,-1,ShaftConfig()),-0.012)
        self.assertAlmostEqual(controller.command(reference,0,-1,0,1,ShaftConfig()),0.012)

    def test_command_clamp_and_invalid_inputs(self):
        controller=DualEncoderController()
        self.assertEqual(controller.command(MotionPoint(100),0,0,0,0,ShaftConfig()),0.03)
        self.assertEqual(controller.command(MotionPoint(-100),0,0,0,0,ShaftConfig()),-0.03)
        with self.assertRaises(ValueError):
            controller.command(MotionPoint(0),math.nan,0,0,0,ShaftConfig())
        with self.assertRaises(ValueError):
            DualEncoderController(-0.001)


class GuardTests(unittest.TestCase):
    def test_nominal_and_boundary(self):
        guard=TwistGuard()
        self.assertTrue(guard.check(0,0.05,0,10,-10))
        self.assertTrue(guard.check(1,0,0,0,0))

    def test_faults_latch_and_close_gate(self):
        for args,reason in (((0,0.051,0,0,0),"TWIST"),((0,0,0,10.1,0),"SPEED"),
                            ((0,0,0,0,0,False),"ENCODER"),
                            ((0,math.nan,0,0,0),"NONFINITE")):
            guard=TwistGuard()
            self.assertFalse(guard.check(*args))
            self.assertEqual(guard.fault,reason)
            self.assertFalse(guard.check(0,0,0,0,0))
            self.assertFalse(guard.drive_enabled)

    def test_lost_or_repeated_cycle(self):
        for cycle in (0,2):
            guard=TwistGuard()
            guard.check(0,0,0,0,0)
            self.assertFalse(guard.check(cycle,0,0,0,0))
            self.assertEqual(guard.fault,"SEQUENCE")


class IntegrationTests(unittest.TestCase):
    def test_tuned_and_baseline_transmission(self):
        baseline,tuned=simulate(False),simulate(True)
        self.assertIsNone(baseline.fault)
        self.assertIsNone(tuned.fault)
        self.assertEqual(tuned.cycles,12000)
        self.assertLess(tuned.twist_rms,baseline.twist_rms/3)
        self.assertLess(tuned.load_error_rms,baseline.load_error_rms)
        self.assertLess(tuned.peak_twist,0.05)

    def test_load_encoder_offset_injection(self):
        result=simulate(encoder_fault_cycle=1000)
        self.assertEqual(result.fault,"TWIST")
        self.assertEqual(result.cycles,1000)


if __name__=="__main__":
    unittest.main()
