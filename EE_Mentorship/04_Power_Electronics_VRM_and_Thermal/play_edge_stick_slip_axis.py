"""EE MENTORSHIP - BAI 253 - BX.1: STATIC/COULOMB/VISCOUS FRICTION.

BUOC 1 - HOP CONG CU
  J=0.001 kg*m^2, viscous b=0.001 Nm*s/rad, Fc=0.010 Nm, Fs=0.015 Nm.
  Dang dung: |torque|<=Fs -> stick, omega=0. Vuot Fs -> truot theo torque.
  Dang truot: J*domega/dt=torque-Fc*sign(omega)-b*omega.
  Giu torque trong dt, w_eq=(torque-Fc*sign)/b:
    w(t)=w_eq+(w0-w_eq)*exp(-b*t/J)
    delta_q=w_eq*t+(w0-w_eq)*(1-exp(-b*t/J))*J/b
  FrictionAxis.step(torque,dt) tim su kien omega=0 neu co, tich phan toi
  do, roi ap lai static law cho phan dt con lai. Khong de Coulomb tu day
  truc quay nguoc khi torque bang 0.

BUOC 2 - BAI TOAN TU LAM
  Tu so torque 0.014 va 0.016 Nm luc dung. Quay omega=1 rad/s roi bo
  torque: du doan thoi gian dung, so voi cach Euler chia buoc vuot omega=0.

BUOC 3 - PHONG VE
  Model dry friction don gian, khong Stribeck dong, LuGre, nhiet hay wear.
  b>0 bat buoc de dung nghiem mu. Torque actuator ly tuong, chua co PMSM.
  dt<=1 ms; state chi mutate sau validation. CPU/RAM O(1), toi da hai pha
  truot cach nhau boi mot su kien dung trong moi buoc torque khong doi.

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo/test stop/reversal; commit/push BX.1.
  Nguon nguyen ly: https://www.mathworks.com/help/simscape/ref/rotationalfriction.html
"""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class FrictionConfig:
    inertia: float = 0.001
    viscous: float = 0.001
    coulomb: float = 0.010
    static: float = 0.015

    def __post_init__(self):
        if not all(math.isfinite(v) for v in vars(self).values()) or min(self.inertia,self.viscous,self.coulomb)<=0 or self.static<self.coulomb:
            raise ValueError("J/b/Fc >0, Fs>=Fc, tat ca huu han")


class FrictionAxis:
    def __init__(self,config: FrictionConfig | None=None):
        self.config=config if config is not None else FrictionConfig()
        self.position=self.velocity=0.0

    def _slide(self,velocity,torque,direction,time):
        c=self.config
        equilibrium=(torque-c.coulomb*direction)/c.viscous
        decay=math.exp(-c.viscous*time/c.inertia)
        end=equilibrium+(velocity-equilibrium)*decay
        distance=equilibrium*time+(velocity-equilibrium)*(-math.expm1(-c.viscous*time/c.inertia))*c.inertia/c.viscous
        return end,distance,equilibrium

    def step(self,torque: float,dt: float):
        if not all(math.isfinite(v) for v in (torque,dt,self.position,self.velocity)) or not 0<dt<=0.001:
            raise ValueError("Friction input khong hop le, 0<dt<=1 ms")
        c=self.config
        velocity=self.velocity
        if velocity==0 and abs(torque)<=c.static:
            return
        direction=math.copysign(1,velocity if velocity else torque)
        end,distance,equilibrium=self._slide(velocity,torque,direction,dt)
        if velocity*end<0:
            crossing=-c.inertia/c.viscous*math.log(-equilibrium/(velocity-equilibrium))
            crossing=max(0.0,min(dt,crossing))
            _,distance,_=self._slide(velocity,torque,direction,crossing)
            end=0.0
            if abs(torque)>c.static:
                end,remainder,_=self._slide(0,torque,math.copysign(1,torque),dt-crossing)
                distance+=remainder
        new_position=self.position+distance
        if not all(math.isfinite(v) for v in (end,new_position)):
            raise ValueError("Friction state tran")
        self.velocity,self.position=end,new_position


if __name__=="__main__":
    axis=FrictionAxis()
    axis.step(0.014,0.001)
    assert axis.velocity==0
    axis.step(0.016,0.001)
    print(f"BX.1: below Fs -> stick; above Fs -> velocity={axis.velocity:.8f} rad/s")
