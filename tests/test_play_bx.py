"""BX regression: python -m unittest discover -s tests -v."""

import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"EE_Mentorship"/
                      "04_Power_Electronics_VRM_and_Thermal"))
from axis_edge_quintic_motion_profile import MotionPoint
from play_edge_stick_slip_axis import FrictionAxis,FrictionConfig
from play_edge_backlash_operator import Backlash
from play_edge_reversal_compensator import ReversalCompensator
from play_edge_reversing_axis_capstone import simulate


class FrictionTests(unittest.TestCase):
    def test_static_threshold_both_directions(self):
        for torque in (-0.015,-0.014,0,0.014,0.015):
            axis=FrictionAxis()
            for _ in range(100):
                axis.step(torque,0.001)
            self.assertEqual((axis.position,axis.velocity),(0,0))

    def test_breakaway_matches_analytic_sliding_solution(self):
        for direction in (-1,1):
            axis=FrictionAxis()
            axis.step(direction*0.016,0.001)
            self.assertAlmostEqual(axis.velocity,direction*6*(1-math.exp(-0.001)))
            self.assertEqual(math.copysign(1,axis.position),direction)

    def test_zero_torque_stops_without_spontaneous_reversal(self):
        axis=FrictionAxis()
        axis.velocity=1
        previous_energy=0.5*axis.config.inertia
        for _ in range(1000):
            axis.step(0,0.001)
            self.assertGreaterEqual(axis.velocity,0)
            energy=0.5*axis.config.inertia*axis.velocity**2
            self.assertLessEqual(energy,previous_energy+1e-15)
            previous_energy=energy
        self.assertEqual(axis.velocity,0)
        self.assertAlmostEqual(axis.position,1-10*math.log(1.1),places=10)

    def test_reversal_event_matches_split_timestep(self):
        whole,split=FrictionAxis(),FrictionAxis()
        whole.velocity=split.velocity=0.001
        whole.step(-0.02,0.001)
        split.step(-0.02,0.0005)
        split.step(-0.02,0.0005)
        self.assertLess(whole.velocity,0)
        self.assertAlmostEqual(whole.velocity,split.velocity,places=11)
        self.assertAlmostEqual(whole.position,split.position,places=11)

    def test_invalid_inputs_do_not_mutate(self):
        axis=FrictionAxis()
        for args in ((math.nan,0.001),(0,0),(0,0.002)):
            with self.assertRaises(ValueError):
                axis.step(*args)
            self.assertEqual((axis.position,axis.velocity),(0,0))
        with self.assertRaises(ValueError):
            FrictionConfig(static=0.005)


class BacklashTests(unittest.TestCase):
    def test_reversal_holds_output_for_full_gap(self):
        play=Backlash()
        self.assertAlmostEqual(play.push(0.1),0.09)
        for value in (0.099,0.095,0.085,0.08):
            self.assertAlmostEqual(play.push(value),0.09)
        self.assertAlmostEqual(play.push(0.07),0.08)

    def test_both_directions_and_origin_shift(self):
        positive,shifted=Backlash(),Backlash(initial_output=10)
        for value in (0,0.1,0.095,-0.1,-0.09,0.05):
            self.assertAlmostEqual(shifted.push(value+10)-10,positive.push(value))

    def test_zero_gap_and_gap_invariant(self):
        direct,play=Backlash(0),Backlash()
        for value in (0,0.1,0.02,-0.2,0.3):
            self.assertEqual(direct.push(value),value)
            self.assertLessEqual(abs(value-play.push(value)),0.01+1e-14)

    def test_nonfinite_does_not_mutate_memory(self):
        play=Backlash()
        play.push(0.1)
        previous=play.output
        with self.assertRaises(ValueError):
            play.push(math.inf)
        self.assertEqual(play.output,previous)
        with self.assertRaises(ValueError):
            Backlash(-0.1)


class CompensationTests(unittest.TestCase):
    def test_offset_rate_limit_and_reversal_takeup(self):
        comp=ReversalCompensator()
        for _ in range(50):
            previous=comp.offset
            output=comp.step(MotionPoint(0,0.1),0.001)
            self.assertLessEqual(abs(output.offset-previous),0.0002+1e-15)
        self.assertAlmostEqual(comp.offset,0.01)
        for _ in range(100):
            previous=comp.offset
            output=comp.step(MotionPoint(0,-0.1),0.001)
            self.assertLessEqual(abs(output.offset-previous),0.0002+1e-15)
        self.assertAlmostEqual(comp.offset,-0.01)

    def test_dwell_keeps_last_direction_and_offset(self):
        comp=ReversalCompensator()
        for _ in range(60):
            comp.step(MotionPoint(0,0.1),0.001)
        output=comp.step(MotionPoint(0.3),0.001)
        self.assertAlmostEqual(output.position,0.31)
        self.assertAlmostEqual(output.offset,0.01)
        self.assertAlmostEqual(output.torque_ff,0)

    def test_friction_feedforward_sign(self):
        for direction in (-1,1):
            comp=ReversalCompensator(half_gap=0)
            output=comp.step(MotionPoint(0,direction*0.1),0.001)
            self.assertEqual(math.copysign(1,output.torque_ff),direction)
            self.assertAlmostEqual(abs(output.torque_ff),0.0101,delta=1e-8)

    def test_invalid_reference_preserves_state(self):
        comp=ReversalCompensator()
        with self.assertRaises(ValueError):
            comp.step(MotionPoint(0,math.nan),0.001)
        self.assertEqual((comp.offset,comp.direction),(0,0))
        with self.assertRaises(ValueError):
            ReversalCompensator(offset_rate=0)


class IntegrationTests(unittest.TestCase):
    def test_combined_compensation_reduces_tracking_error(self):
        baseline,tuned=simulate(False),simulate(True)
        self.assertIsNone(baseline.fault)
        self.assertIsNone(tuned.fault)
        self.assertGreater(tuned.cycles,3000)
        self.assertLess(tuned.load_rms,baseline.load_rms/2)
        self.assertLess(tuned.peak_error,0.01)
        self.assertLessEqual(tuned.peak_torque,0.06)
        # Use a practical tolerance; compensation need not produce exact zero error.
        self.assertLess(abs(tuned.final_error),0.01)

    def test_load_encoder_offset_disables_simulation(self):
        result=simulate(encoder_fault_cycle=1000)
        self.assertEqual(result.fault,"ENCODER_DISAGREEMENT")
        self.assertEqual(result.cycles,1000)


if __name__=="__main__":
    unittest.main()
