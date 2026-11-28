"""EE MENTORSHIP - BAI 256 - BX.4: FRICTION/BACKLASH REVERSING AXIS.

BUOC 1 - HOP CONG CU
  BV quintic reference -> optional BX compensation -> motor PD + torque FF
  -> friction axis BX.1 -> backlash signal operator BX.2 -> load position.
  Motor PD kp=1 Nm/rad, kd=0.06 Nm*s/rad, torque clamp +/-0.06 Nm; dt=1 ms.
  Hai doan 0 -> +0.3 -> -0.2 rad, giu moi dich 0.5 s. Motor encoder dong
  feedback; load encoder chi danh gia error va gap plausibility guard.
  simulate(compensated=True,encoder_fault_cycle=None) tra ReversalResult:
  load RMS, peak error, final error, torque peak va fault.

BUOC 2 - BAI TOAN TU LAM
  Tu ghep 3 bai, so baseline va compensation. Tai sao biet do ro van khong
  loai duoc thoi gian take-up? Thu Fc/Fs uoc luong sai va quan sat limit cycle.

BUOC 3 - PHONG VE
  Backlash la signal model massless, khong couple reaction torque ve motor.
  Day KHONG la mo phong gearbox contact/energy day du. Cac tham so gap va
  friction biet truoc; feedback ideal, khong PMSM/current loop, delay, wear
  hay hardware STO. Guard |motor-load|>0.03 rad phat hien offset +0.1 rad
  duoc chen vao load encoder; guard dua tren model, khong chan doan doc lap.
  Compensation doi ca backlash va friction FF, khong tach tac dong tung cai.
  Fault ket thuc simulation, khong chung minh truc that dung ngay.
  CPU O(N), RAM O(1); khong luu trace.

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo/tests va cap nhat roadmap; commit/push BX.4.
  Nguon backlash: https://www.mathworks.com/help/simulink/slref/backlash.html
"""

from dataclasses import dataclass
import math
from axis_edge_quintic_motion_profile import QuinticMove
from play_edge_stick_slip_axis import FrictionAxis
from play_edge_backlash_operator import Backlash
from play_edge_reversal_compensator import ReversalCompensator,MotorReference


@dataclass(frozen=True)
class ReversalResult:
    load_rms: float
    peak_error: float
    final_error: float
    peak_torque: float
    fault: str | None
    cycles: int


def simulate(compensated=True,encoder_fault_cycle=None):
    axis,play,comp=FrictionAxis(),Backlash(),ReversalCompensator()
    first=QuinticMove(0,0.3,vmax=0.5,amax=2,jmax=20)
    second=QuinticMove(0.3,-0.2,vmax=0.5,amax=2,jmax=20)
    second_start=first.duration+0.5
    duration=second_start+second.duration+0.5
    dt=0.001
    square=peak=torque_peak=last_error=0.0
    fault=None
    executed=0
    for cycle in range(math.ceil(duration/dt)):
        time=cycle*dt
        reference=first.sample(time) if time<second_start else second.sample(time-second_start)
        load=play.push(axis.position)
        measured_load=load+(0.1 if cycle==encoder_fault_cycle else 0)
        if abs(axis.position-measured_load)>0.03:
            fault="ENCODER_DISAGREEMENT"
            break
        motor_ref=comp.step(reference,dt) if compensated else MotorReference(reference.position,reference.velocity,0,0)
        request=(motor_ref.position-axis.position)+0.06*(motor_ref.velocity-axis.velocity)+motor_ref.torque_ff
        torque=max(-0.06,min(0.06,request))
        axis.step(torque,dt)
        load=play.push(axis.position)
        last_error=reference.position-load
        square+=last_error**2
        peak=max(peak,abs(last_error))
        torque_peak=max(torque_peak,abs(torque))
        executed+=1
    return ReversalResult(math.sqrt(square/executed) if executed else math.inf,
                          peak,last_error,torque_peak,fault,executed)


def demo():
    baseline,tuned=simulate(False),simulate(True)
    bad=simulate(encoder_fault_cycle=1000)
    assert baseline.fault is None and tuned.fault is None
    assert tuned.load_rms<baseline.load_rms/2
    assert bad.fault=="ENCODER_DISAGREEMENT" and bad.cycles==1000
    print(f"BX.4: RMS baseline={baseline.load_rms:.8f}, compensated={tuned.load_rms:.8f} rad; "
          f"peak={tuned.peak_error:.8f}, final error={tuned.final_error:.8f} rad; "
          f"torque peak={tuned.peak_torque:.8f} Nm")
    print(f"BX.4 injected load encoder offset -> {bad.fault}")


if __name__=="__main__":
    demo()
