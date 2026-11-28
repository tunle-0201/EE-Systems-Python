"""EE MENTORSHIP - BAI 255 - BX.3: RATE-LIMITED BACKLASH/FRICTION FF.

BUOC 1 - HOP CONG CU
  Chieu lenh tu vref (deadband 1e-4 rad/s); khi dung giu chieu cu.
  offset_target=sign(vref)*h; offset chi doi toi da 0.2*dt rad moi buoc.
    motor_ref=load_ref+offset; motor_vref=vref+delta_offset/dt
  Friction FF muot tu reference, khong tu hoc hay nghich dao plant hoan hao:
    magnitude=Fc+(Fs-Fc)*exp(-(v/0.02)^2)
    torque_ff=J*aref+b*v+magnitude*tanh(v/0.003)
  ReversalCompensator.step(reference,dt) tra MotorReference(q,v,torque_ff,offset).

BUOC 2 - BAI TOAN TU LAM
  Dao chieu tu +h sang -h voi h=0.01 rad: tu tinh thoi gian take-up toi
  thieu. So offset ramp voi buoc nhay offset tuc thoi va thu h uoc luong sai.

BUOC 3 - PHONG VE
  Rate limit offset khong gioi han acceleration/jerk cua motor command;
  khong them offset acceleration vao torque FF. Fs/Fc uoc luong, smooth FF
  khong tai tao dung static stick cua BX.1. Clamp torque tong o caller.
  Doi tham so khong dam bao cai thien tren moi co cau. CPU/RAM O(1).

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo/test offset rate va units; commit/push BX.3.
  Nguon feedforward: https://webhelp.kollmorgen.com/essentials/English/Content/Tuning/Determining-FeedForwards.htm
"""

from dataclasses import dataclass
import math
from play_edge_stick_slip_axis import FrictionConfig


@dataclass(frozen=True)
class MotorReference:
    position: float
    velocity: float
    torque_ff: float
    offset: float


class ReversalCompensator:
    def __init__(self,half_gap: float=0.01,offset_rate: float=0.2):
        if not all(math.isfinite(v) for v in (half_gap,offset_rate)) or half_gap<0 or offset_rate<=0:
            raise ValueError("Compensation gap/rate khong hop le")
        self.half_gap,self.offset_rate=half_gap,offset_rate
        self.offset=0.0
        self.direction=0

    def step(self,reference,dt: float) -> MotorReference:
        if not all(math.isfinite(v) for v in (reference.position,reference.velocity,reference.acceleration,dt)) or dt<=0:
            raise ValueError("Reference/dt khong hop le")
        direction=self.direction
        if abs(reference.velocity)>1e-4:
            direction=1 if reference.velocity>0 else -1
        change=max(-self.offset_rate*dt,min(self.offset_rate*dt,direction*self.half_gap-self.offset))
        velocity=reference.velocity+change/dt
        c=FrictionConfig()
        magnitude=c.coulomb+(c.static-c.coulomb)*math.exp(-(velocity/0.02)**2)
        torque=c.inertia*reference.acceleration+c.viscous*velocity+magnitude*math.tanh(velocity/0.003)
        self.offset+=change
        self.direction=direction
        return MotorReference(reference.position+self.offset,velocity,torque,self.offset)


if __name__=="__main__":
    from axis_edge_quintic_motion_profile import MotionPoint
    compensator=ReversalCompensator()
    for _ in range(50):
        output=compensator.step(MotionPoint(0,0.1),0.001)
    print(f"BX.3: offset after 50 ms={output.offset:.8f} rad, torque FF={output.torque_ff:.8f} Nm")
