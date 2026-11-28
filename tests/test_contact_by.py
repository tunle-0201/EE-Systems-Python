"""BY regression: python -m unittest discover -s tests -v; standard library only."""

import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"EE_Mentorship"/
                      "08_Robotics_Autonomous_Driving_and_Control"))
from contact_edge_unilateral_wall import Wall
from contact_edge_force_sensor_calibration import ForceSensor,ForceFrame,ForceCalibration,calibration_fixture
from contact_edge_contact_state_machine import ContactFSM
from contact_edge_force_pi_velocity import ForcePI
from contact_edge_backward_euler_admittance import Admittance,State
from contact_edge_discrete_energy_observer import energy_report
from contact_edge_force_supervisor import ForceSupervisor
from contact_edge_robot_surface_force_capstone import simulate


class WallTests(unittest.TestCase):
    def test_no_contact_and_separation(self):
        wall=Wall()
        for position in (-0.1,0,wall.surface):
            self.assertEqual(wall.force(position,0.1),0)
            self.assertEqual(wall.stored_energy(position),0)

    def test_spring_damper_units_and_no_adhesion(self):
        wall=Wall()
        self.assertAlmostEqual(wall.force(0.015,0.001),10.02)
        self.assertAlmostEqual(wall.stored_energy(0.015),0.025)
        self.assertEqual(wall.force(0.015,-1),0)

    def test_invalid_parameters_and_inputs(self):
        with self.assertRaises(ValueError):
            Wall(stiffness=0)
        with self.assertRaises(ValueError):
            Wall().force(math.nan,0)


class SensorTests(unittest.TestCase):
    def test_calibration_on_unseen_forces(self):
        sensor=ForceSensor()
        cal=calibration_fixture(sensor)
        for force in (-5,0,7.3,12.7,25,40):
            self.assertAlmostEqual(cal.decode(sensor.sample(force,0)),force,delta=0.004)

    def test_clip_and_malformed_code_rejected(self):
        sensor=ForceSensor()
        cal=calibration_fixture(sensor)
        for frame in (sensor.sample(200,0),sensor.sample(-100,0),ForceFrame(0,-1),
                      ForceFrame(0,65536),ForceFrame(0,1.5)):
            with self.assertRaises(ValueError):
                cal.decode(frame)

    def test_invalid_calibration_pairs(self):
        for zero,loaded in ((ForceFrame(0,100),ForceFrame(0,100)),
                            (ForceFrame(0,200),ForceFrame(0,100)),
                            (ForceFrame(0,100,True),ForceFrame(0,200))):
            with self.assertRaises(ValueError):
                ForceCalibration.fit(zero,loaded)


class ContactFSMTests(unittest.TestCase):
    def test_threshold_hysteresis_and_dwell(self):
        fsm=ContactFSM()
        for force in (1.01,0.99,1.01,0.99):
            self.assertEqual(fsm.update(force),"APPROACH")
        for _ in range(2):
            self.assertEqual(fsm.update(1.0),"APPROACH")
        self.assertEqual(fsm.update(1.0),"REGULATE")
        for _ in range(20):
            self.assertEqual(fsm.update(0.5),"REGULATE")
        for _ in range(9):
            self.assertEqual(fsm.update(0.3),"REGULATE")
        self.assertEqual(fsm.update(0.3),"APPROACH")

    def test_contact_loss_counter_resets(self):
        fsm=ContactFSM()
        for _ in range(3):
            fsm.update(2)
        for _ in range(5):
            fsm.update(0)
        fsm.update(1)
        for _ in range(9):
            self.assertEqual(fsm.update(0),"REGULATE")

    def test_invalid_force_does_not_change_state(self):
        fsm=ContactFSM()
        with self.assertRaises(ValueError):
            fsm.update(math.nan)
        self.assertEqual((fsm.state,fsm.on_samples),("APPROACH",0))


class PITests(unittest.TestCase):
    def test_force_error_sign(self):
        self.assertGreater(ForcePI().step(10,5,0.001),0)
        self.assertLess(ForcePI().step(10,15,0.001),0)

    def test_bumpless_reset(self):
        pi=ForcePI()
        pi.reset(0.005,9)
        self.assertAlmostEqual(pi.step(10,1,0.001),0.005)

    def test_saturation_does_not_wind_up(self):
        pi=ForcePI()
        for _ in range(1000):
            self.assertEqual(pi.step(100,0,0.001),0.01)
        self.assertEqual(pi.integral,0)
        self.assertEqual(pi.step(0,0,0.001),0)

    def test_unwind_and_invalid_step(self):
        pi=ForcePI()
        pi.integral=0.02
        pi.step(10,11,0.001)
        self.assertLess(pi.integral,0.02)
        before=pi.integral
        with self.assertRaises(ValueError):
            pi.step(10,math.nan,0.001)
        self.assertEqual(pi.integral,before)


class AdmittanceTests(unittest.TestCase):
    def test_backward_euler_equations(self):
        model=Admittance(mass=2,damping=30,stiffness=50)
        model.position,model.velocity=0.02,-0.1
        old=model.state
        new=model.step(4,0.001)
        self.assertAlmostEqual(new.position-old.position,0.001*new.velocity)
        self.assertAlmostEqual(2*(new.velocity-old.velocity)/0.001+30*new.velocity+50*new.position,4)

    def test_constant_force_terminal_velocity(self):
        model=Admittance()
        for _ in range(100):
            new=model.step(10,0.001)
        self.assertAlmostEqual(new.velocity,0.01)

    def test_unforced_storage_decays(self):
        model=Admittance(mass=2,damping=30,stiffness=50)
        model.position,model.velocity=0.1,0.2
        previous=(2*0.2**2+50*0.1**2)/2
        for _ in range(1000):
            new=model.step(0,0.001)
            energy=(2*new.velocity**2+50*new.position**2)/2
            self.assertLessEqual(energy,previous+1e-14)
            previous=energy

    def test_invalid_input_does_not_mutate(self):
        model=Admittance()
        with self.assertRaises(ValueError):
            model.step(math.inf,0.001)
        self.assertEqual(model.state,State(0,0))
        with self.assertRaises(ValueError):
            Admittance(mass=0)


class EnergyTests(unittest.TestCase):
    def test_discrete_identity_for_spring_and_no_spring(self):
        for stiffness in (0,50):
            model=Admittance(mass=2,damping=30,stiffness=stiffness)
            model.position,model.velocity=0.02,-0.1
            for k in range(300):
                force=10*math.sin(k/20)
                old=model.state
                new=model.step(force,0.001)
                report=energy_report(model,old,new,force,0.001)
                self.assertLess(abs(report.residual),1e-14)
                self.assertGreaterEqual(report.viscous_loss,0)
                self.assertGreaterEqual(report.numerical_loss,0)
                self.assertLessEqual(report.storage_change,report.input_work+1e-14)

    def test_inconsistent_state_is_not_certified(self):
        model=Admittance()
        report=energy_report(model,State(0,0),State(0.001,1),0,0.001)
        self.assertGreater(report.residual,0.1)


class SupervisorTests(unittest.TestCase):
    def make(self):
        return ForceSupervisor(ForceCalibration(1000,100))

    def frame(self,time,force=10):
        return ForceFrame(time,round(1000+100*force))

    def test_nominal_and_motion_boundaries(self):
        guard=self.make()
        self.assertTrue(guard.check(0,self.frame(0),-0.01,0.01))
        self.assertTrue(guard.check(0.001,self.frame(0.001,25),0.03,-0.01))

    def test_force_clip_and_motion_faults_latch(self):
        cases=((self.frame(0,26),0.015,0,"OVERFORCE"),
               (self.frame(0,-2),0.015,0,"FORCE_RANGE"),
               (ForceFrame(0,2000,True),0.015,0,"ADC"),
               (self.frame(0),0.031,0,"MOTION"),
               (self.frame(0),0.015,0.011,"MOTION"))
        for frame,x,v,reason in cases:
            guard=self.make()
            self.assertFalse(guard.check(0,frame,x,v))
            self.assertEqual(guard.fault,reason)
            self.assertFalse(guard.check(0.001,self.frame(0.001),0.015,0))

    def test_replay_old_and_future_frames(self):
        guard=self.make()
        self.assertTrue(guard.check(0,self.frame(0),0,0))
        self.assertFalse(guard.check(0.001,self.frame(0),0,0))
        self.assertEqual(guard.fault,"STALE")
        guard=self.make()
        self.assertFalse(guard.check(0.006,self.frame(0),0,0))
        self.assertEqual(guard.fault,"STALE")
        guard=self.make()
        self.assertFalse(guard.check(0,self.frame(0.001),0,0))
        self.assertEqual(guard.fault,"CLOCK")

    def test_age_exactly_5ms_is_allowed(self):
        guard=self.make()
        self.assertTrue(guard.check(0.005,self.frame(0),0,0))

    def test_missing_data_recovers_before_timeout(self):
        guard=self.make()
        guard.check(0,self.frame(0),0,0)
        self.assertFalse(guard.check(0.001,None,0,0))
        self.assertTrue(guard.check(0.002,self.frame(0.002),0,0))

    def test_timeout_before_late_healthy_frame(self):
        guard=self.make()
        guard.check(0,self.frame(0),0,0)
        for k in range(1,20):
            self.assertFalse(guard.check(k*0.001,None,0,0))
            self.assertIsNone(guard.fault)
        self.assertFalse(guard.check(0.020,self.frame(0.020),0,0))
        self.assertEqual(guard.fault,"TIMEOUT")

    def test_clock_cadence_and_nonfinite_faults(self):
        for now,x,reason in ((0,0,"CLOCK"),(-1,0,"CLOCK"),(0.004,0,"TIMING"),
                             (0.001,math.nan,"NONFINITE")):
            guard=self.make()
            guard.check(0,self.frame(0),0,0)
            self.assertFalse(guard.check(now,self.frame(now),x,0))
            self.assertEqual(guard.fault,reason)


class IntegrationTests(unittest.TestCase):
    def test_approach_contact_and_both_force_controllers(self):
        for mode in ("pi","admittance"):
            result=simulate(mode)
            self.assertIsNone(result.fault)
            self.assertEqual(result.cycles,6000)
            self.assertLess(result.contact_time,2.2)
            self.assertLess(result.force_rms,0.5)
            self.assertLess(result.peak_force,25)
            self.assertLess(result.max_energy_residual,1e-10)

    def test_stiffness_changes_with_same_gains(self):
        for mode in ("pi","admittance"):
            for stiffness in (1000,5000):
                result=simulate(mode,stiffness)
                self.assertIsNone(result.fault)
                self.assertLess(abs(result.final_force-10),1)
                self.assertLess(result.peak_force,25)

    def test_sensor_replay_stops_both_modes(self):
        for mode in ("pi","admittance"):
            result=simulate(mode,replay_cycle=3000)
            self.assertEqual(result.fault,"STALE")
            self.assertEqual(result.cycles,3000)


if __name__=="__main__":
    unittest.main()
