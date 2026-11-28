"""EE MENTORSHIP - BAI 262 - BY.6: DISCRETE ENERGY IDENTITY.

BUOC 1 - HOP CONG CU
  Nhan BE mass equation voi v_new*dt va dung x_new-x_old=v_new*dt:
    E_new-E_old = f*v_new*dt - D*v_new^2*dt
                 -M*(v_new-v_old)^2/2 - K*(x_new-x_old)^2/2
  Hai so hang cuoi la numerical dissipation, khong phai physical damper.
  energy_report(model,old,new,force,dt) tra input_work, storage_change,
  viscous_loss, numerical_loss, residual. Residual ly tuong=0.

BUOC 2 - BAI TOAN TU LAM
  Tu bien doi a^2-b^2=2*a*(a-b)-(a-b)^2 de chung minh identity. Chen mot
  state update sai co chu dich va xem residual khac zero.

BUOC 3 - PHONG VE
  Observer chi kiem tra VIRTUAL BE subsystem cua BY.5. Khong la energy tank,
  khong limit work, khong chung nhan robot/actuator/controller passive.
  Clip velocity, delay, changing gains/reference position va sensor errors
  ben ngoai khong duoc bao phu. CPU/RAM O(1), moi report la mot buoc.

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo va test identity ca K=0/K>0; commit/push BY.6.
  Nen tang M/D/K: https://control.ros.org/rolling/doc/ros2_controllers/admittance_controller/doc/userdoc.html
"""

from dataclasses import dataclass
import math
from contact_edge_backward_euler_admittance import Admittance,State


@dataclass(frozen=True)
class EnergyReport:
    input_work: float
    storage_change: float
    viscous_loss: float
    numerical_loss: float
    residual: float


def energy_report(model: Admittance,old: State,new: State,force: float,dt: float) -> EnergyReport:
    if not all(math.isfinite(v) for v in (old.position,old.velocity,new.position,new.velocity,force,dt)) or dt<=0:
        raise ValueError("Energy report inputs khong hop le")
    delta=(model.mass*(new.velocity**2-old.velocity**2)+
           model.stiffness*(new.position**2-old.position**2))/2
    work=force*new.velocity*dt
    viscous=model.damping*new.velocity**2*dt
    numerical=(model.mass*(new.velocity-old.velocity)**2+
               model.stiffness*(new.position-old.position)**2)/2
    return EnergyReport(work,delta,viscous,numerical,delta-work+viscous+numerical)


if __name__=="__main__":
    model=Admittance(stiffness=50)
    old=model.state
    report=energy_report(model,old,model.step(10,0.001),10,0.001)
    print(f"BY.6: discrete energy residual={report.residual:.3e} J")
