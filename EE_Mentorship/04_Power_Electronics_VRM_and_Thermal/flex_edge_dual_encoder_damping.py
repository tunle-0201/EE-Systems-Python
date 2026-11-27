"""EE MENTORSHIP - BAI 251 - BW.4: DUAL-ENCODER RELATIVE DAMPING.

BUOC 1 - HOP CONG CU
  Encoder motor/load cho omega_m,omega_l; relative velocity=omega_m-omega_l.
  Torque command:
    kp*(q_ref-theta_load)+kd*(v_ref-omega_motor)
      -krel*(omega_motor-omega_load)+(Jm+Jl)*a_ref
  Relative damping tao torque chong rung tuong doi. DualEncoderController
  clamp tong torque +/-0.03 Nm. Chua co speed/current loop dien.
  TwistGuard.check(cycle,tm,tl,wm,wl,sensor_ok) chot khi twist>0.05 rad,
  speed>10 rad/s, code cycle lap/mat hoac input nonfinite/sensor fault.

BUOC 2 - BAI TOAN TU LAM
  Cho wm=+1, wl=-1, krel=0.003; tinh torque damping. Thu krel=0 va krel
  duong tren plant BW.1. Encoder load bias 0.2 rad se anh huong gi?

BUOC 3 - PHONG VE
  Hai encoder ly tuong, dong bo; khong dao ham tin hieu nhieu, delay hay
  encoder wrap. Day khong la disturbance observer. krel sai dau tao feedback
  duong; clamp torque khong dam bao motion safety. Guard la software caller
  tick, khong hard-limit/STO hay watchdog doc lap. CPU/RAM O(1).

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo, test sign va fault latch; commit/push BW.4.
  Nguon resonance tuning: https://www.kollmorgen.com/sites/default/files/AKD%20Tuning%20Guide.pdf
"""

import math
from flex_edge_two_inertia_plant import ShaftConfig


class DualEncoderController:
    def __init__(self,relative_gain=0.003):
        if not math.isfinite(relative_gain) or relative_gain<0:
            raise ValueError("Relative gain phai huu han, khong am")
        self.relative_gain=relative_gain

    def command(self,reference,tm,wm,tl,wl,config: ShaftConfig):
        values=(reference.position,reference.velocity,reference.acceleration,tm,wm,tl,wl)
        if not all(math.isfinite(v) for v in values):
            raise ValueError("Controller inputs phai huu han")
        torque=(0.04*(reference.position-tl)+0.006*(reference.velocity-wm)
                -self.relative_gain*(wm-wl)+(config.jm+config.jl)*reference.acceleration)
        return max(-0.03,min(0.03,torque))


class TwistGuard:
    def __init__(self):
        self.last_cycle=-1
        self.fault=None
        self.drive_enabled=False

    def check(self,cycle,tm,tl,wm,wl,sensor_ok=True):
        self.drive_enabled=False
        if self.fault is not None:
            return False
        if not isinstance(cycle,int) or cycle!=self.last_cycle+1:
            self.fault="SEQUENCE"
        elif not sensor_ok:
            self.fault="ENCODER"
        elif not all(math.isfinite(v) for v in (tm,tl,wm,wl)):
            self.fault="NONFINITE"
        elif abs(tm-tl)>0.05:
            self.fault="TWIST"
        elif max(abs(wm),abs(wl))>10:
            self.fault="SPEED"
        else:
            self.last_cycle=cycle
            self.drive_enabled=True
        return self.drive_enabled


if __name__=="__main__":
    from axis_edge_quintic_motion_profile import MotionPoint
    c=DualEncoderController()
    value=c.command(MotionPoint(0),0,1,0,-1,ShaftConfig())
    print(f"BW.4: motor/load speeds +1/-1 -> torque={value:.6f} Nm")
