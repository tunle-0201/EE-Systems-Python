"""EE MENTORSHIP - BAI 252 - BW.5: FLEXIBLE ROBOT TRANSMISSION CAPSTONE.

BUOC 1 - HOP CONG CU
  Ringdown BW.2 -> notch fn BW.3 -> load-position controller BW.4 -> torque
  actuator -> two-inertia shaft BW.1. Quintic reference 0 -> 0.1 rad dung BV.
  De thay kich thich resonance, chen torque sinusoid 0.0015 Nm tai fn SAU
  controller va TRUOC notch. So baseline (khong notch/krel) voi tuned.
  simulate(tuned=True,encoder_fault_cycle=None) tra RMS twist/load-error
  trong 1.5..3 s, peak twist toan hanh trinh va fault. sampling=4 kHz.

BUOC 2 - BAI TOAN TU LAM
  Tu ghep 4 bai. So baseline/tuned, doi stiffness va notch sai tan so de
  thay trade-off. Tai sao motor encoder on dinh chua dam bao load on dinh?

BUOC 3 - PHONG VE
  Sinusoid la command contamination CO CHU DICH, khong phai nhieu do duoc.
  Notch chi loc torque path, khong tu loai disturbance o load. Tuned doi
  CA notch va krel; ket qua so sanh khong tach dong gop tung bien phap.
  Encoder/current actuator ly tuong; chua co PMSM, backlash, gear ratio,
  thermal, sampled delay hay hardware safety. Inject offset encoder load
  +0.2 rad de test guard, khong thay doi plant that. Fault ket thuc simulation,
  khong chung minh phanh dung truc. CPU O(N), memory O(peaks ringdown).

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo/test, cap nhat roadmap, commit/push BW.5.
  Nguon: https://webhelp.kollmorgen.com/AKD/English/Content/Tuning/Tuning-Fundamentals/Tuning-with-Filters.htm
"""

from dataclasses import dataclass
import math
from axis_edge_quintic_motion_profile import QuinticMove
from flex_edge_two_inertia_plant import FlexibleShaft
from flex_edge_ringdown_identification import identify
from flex_edge_notch_filter import Notch
from flex_edge_dual_encoder_damping import DualEncoderController,TwistGuard


@dataclass(frozen=True)
class FlexResult:
    twist_rms: float
    load_error_rms: float
    peak_twist: float
    fault: str | None
    cycles: int


def simulate(tuned=True,encoder_fault_cycle=None):
    plant=FlexibleShaft()
    identified=identify(plant.config)
    notch=Notch(identified.natural_hz)
    controller=DualEncoderController(0.003 if tuned else 0)
    guard=TwistGuard()
    move=QuinticMove(0,0.1,vmax=0.5,amax=2,jmax=20)
    dt=0.00025
    twist_square=error_square=peak=0.0
    count=executed=0
    for cycle in range(12000):
        time=cycle*dt
        measured_load=plant.tl+(0.2 if cycle==encoder_fault_cycle else 0)
        if not guard.check(cycle,plant.tm,measured_load,plant.wm,plant.wl):
            break
        reference=move.sample(time)
        request=controller.command(reference,plant.tm,plant.wm,measured_load,plant.wl,plant.config)
        request+=0.0015*math.sin(math.tau*plant.config.natural_hz*time)
        applied=notch.push(request) if tuned else request
        applied=max(-0.03,min(0.03,applied))
        plant.step(applied,0,dt)
        twist=plant.tm-plant.tl
        peak=max(peak,abs(twist))
        if time>=1.5:
            twist_square+=twist**2
            error_square+=(plant.tl-0.1)**2
            count+=1
        executed+=1
    return FlexResult(math.sqrt(twist_square/count) if count else math.inf,
                      math.sqrt(error_square/count) if count else math.inf,
                      peak,guard.fault,executed)


def demo():
    baseline,tuned=simulate(False),simulate(True)
    faulty=simulate(encoder_fault_cycle=1000)
    assert baseline.fault is None and tuned.fault is None
    assert tuned.twist_rms<baseline.twist_rms/3
    assert faulty.fault=="TWIST" and faulty.cycles==1000
    print(f"BW.5: twist RMS baseline={baseline.twist_rms:.8f}, tuned={tuned.twist_rms:.8f} rad; "
          f"load error baseline={baseline.load_error_rms:.8f}, tuned={tuned.load_error_rms:.8f} rad; "
          f"peak tuned={tuned.peak_twist:.8f} rad")
    print(f"BW.5 injected load encoder offset -> {faulty.fault} at cycle {faulty.cycles}")


if __name__=="__main__":
    demo()
