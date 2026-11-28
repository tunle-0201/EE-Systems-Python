"""EE MENTORSHIP - BAI 261 - BY.5: BACKWARD-EULER ADMITTANCE.

BUOC 1 - HOP CONG CU
  Virtual mass/spring/damper: M*dv/dt+D*v+K*x=f [N]. Backward Euler:
    v_new=(M*v_old+dt*(f-K*x_old))/(M+D*dt+K*dt^2)
    x_new=x_old+dt*v_new
  Admittance(M=2 kg,D=1000 Ns/m,K=0 N/m).step(force,dt) tra State(x,v).
  stored energy E=M*v^2/2+K*x^2/2. Dung co the co K=0, nhung M>0.
  f la virtual input; capstone chon f=Fref-Fmeasured de tao velocity.

BUOC 2 - BAI TOAN TU LAM
  Tu giai hai phuong trinh backward Euler dong thoi, khong cap nhat x roi
  moi dung x da doi cho v. Thu K=0 va force khong doi: v -> f/D.

BUOC 3 - PHONG VE
  Day la virtual subsystem, khong la physical robot inertia. Backward Euler
  them numerical damping. Khong clamp x/v trong khoi nay de giu identity
  nang luong BY.6; clamp actuator ben ngoai khong nam trong identity do.
  Force reference la nguon chu dong: khong suy whole robot passivity tu
  virtual subsystem. CPU/RAM O(1), chi x/v.

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo va test equilibrium/discrete equations; commit/push BY.5.
  Nguon admittance: https://control.ros.org/rolling/doc/ros2_controllers/admittance_controller/doc/userdoc.html
"""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class State:
    position: float
    velocity: float


class Admittance:
    def __init__(self,mass=2.0,damping=1000.0,stiffness=0.0):
        if not all(math.isfinite(v) for v in (mass,damping,stiffness)) or mass<=0 or min(damping,stiffness)<0:
            raise ValueError("M>0, D/K>=0, tat ca huu han")
        self.mass,self.damping,self.stiffness=mass,damping,stiffness
        self.position=self.velocity=0.0

    @property
    def state(self):
        return State(self.position,self.velocity)

    def step(self,force: float,dt: float) -> State:
        if not all(math.isfinite(v) for v in (force,dt,self.position,self.velocity)) or dt<=0:
            raise ValueError("Admittance inputs khong hop le")
        velocity=(self.mass*self.velocity+dt*(force-self.stiffness*self.position))/(
            self.mass+self.damping*dt+self.stiffness*dt*dt)
        position=self.position+dt*velocity
        if not all(math.isfinite(v) for v in (position,velocity)):
            raise ValueError("Admittance state tran")
        self.position,self.velocity=position,velocity
        return self.state


if __name__=="__main__":
    model=Admittance()
    for _ in range(100):
        state=model.step(10,0.001)
    print(f"BY.5: force=10 N, K=0 -> velocity={state.velocity:.8f} m/s")
