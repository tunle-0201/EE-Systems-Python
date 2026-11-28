"""EE MENTORSHIP - BAI 264 - BY.8: ROBOT APPROACH/CONTACT/FORCE HOLD.

BUOC 1 - HOP CONG CU
  Wall BY.1 -> sensor/cal BY.2 -> supervisor BY.7 -> contact FSM BY.3.
  APPROACH: velocity=0.005 m/s; REGULATE: chon ForcePI BY.4 hoac admittance
  BE BY.5, target=10 N. Bumpless PI reset hoac dat v_adm=approach velocity.
  BY.6 kiem tra nang luong moi buoc virtual admittance TRUOC velocity clamp.
  Ideal velocity actuator: x_next=x+v_cmd*dt, dt=1 ms; mo phong 6 s.
  simulate(mode='pi'|'admittance',stiffness=2000,replay_cycle=None) tra metrics.
  contact_time la luc FSM xac nhan REGULATE, khong la luc cham vat ly dau tien.

BUOC 2 - BAI TOAN TU LAM
  Tu ghep 7 bai; so hai controller va doi stiffness 1000/5000 N/m. Thu
  frame sensor replay tai cycle 3000 va giai thich vi sao fault chu khong
  duoc tiep tuc ep bang force value cu.

BUOC 3 - PHONG VE
  Ideal velocity source khong mo phong motor inertia, inner servo lag hay
  contact impact compliance cua robot. Identities energy chi virtual BE;
  force reference, clamp va actuator khong nam trong passivity proof.
  Sensor ly tuong ngoai ADC/gain/offset. Khong contact tangential, 6D hybrid
  projection, real robot IO hay STO. Chua co retreat/release task cuoi run.
  Metrics force so voi target dung force plant that, khong chi so sensor.
  Fault dong cong va ket thuc sim, khong chung minh motor that dung ngay.
  CPU O(cycles), RAM O(1), chi giu metrics.

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo/test, cap nhat roadmap, commit/push BY.8.
  Nguon: https://control.ros.org/rolling/doc/ros2_controllers/admittance_controller/doc/userdoc.html
"""

from dataclasses import dataclass
import math
from contact_edge_unilateral_wall import Wall
from contact_edge_force_sensor_calibration import ForceSensor,calibration_fixture
from contact_edge_contact_state_machine import ContactFSM
from contact_edge_force_pi_velocity import ForcePI
from contact_edge_backward_euler_admittance import Admittance
from contact_edge_discrete_energy_observer import energy_report
from contact_edge_force_supervisor import ForceSupervisor


@dataclass(frozen=True)
class ContactResult:
    mode: str
    contact_time: float | None
    final_force: float
    force_rms: float
    peak_force: float
    max_energy_residual: float
    fault: str | None
    cycles: int


def simulate(mode="pi",stiffness=2000.0,replay_cycle=None) -> ContactResult:
    if mode not in ("pi","admittance"):
        raise ValueError("Chon pi hoac admittance")
    wall=Wall(stiffness=stiffness)
    sensor=ForceSensor()
    supervisor=ForceSupervisor(calibration_fixture(sensor))
    contact,pi,admittance=ContactFSM(),ForcePI(),Admittance()
    position=velocity=square=peak=residual=0.0
    contact_time=None
    count=executed=0
    previous_frame=None
    final_force=0.0
    dt=0.001
    for cycle in range(6000):
        now=cycle*dt
        true_force=wall.force(position,velocity)
        frame=sensor.sample(true_force,now)
        if replay_cycle is not None and cycle>=replay_cycle and previous_frame is not None:
            frame=previous_frame
        if not supervisor.check(now,frame,position,velocity):
            break
        previous_frame=frame
        measured=supervisor.force_n
        previous_state=contact.state
        state=contact.update(measured)
        if state=="APPROACH":
            command=0.005
        else:
            error=10-measured
            if previous_state!="REGULATE":
                if contact_time is None:
                    contact_time=now
                pi.reset(velocity,error)
                admittance.velocity=velocity
                admittance.position=0
            if mode=="pi":
                command=pi.step(10,measured,dt)
            else:
                old=admittance.state
                new=admittance.step(error,dt)
                report=energy_report(admittance,old,new,error,dt)
                residual=max(residual,abs(report.residual))
                command=new.velocity
        velocity=max(-0.01,min(0.01,command))
        position+=velocity*dt
        final_force=wall.force(position,velocity)
        peak=max(peak,final_force)
        if now>=5:
            square+=(final_force-10)**2
            count+=1
        executed+=1
    return ContactResult(mode,contact_time,final_force,math.sqrt(square/count) if count else math.inf,
                         peak,residual,supervisor.fault,executed)


def demo():
    for mode in ("pi","admittance"):
        result=simulate(mode)
        assert result.fault is None and result.force_rms<0.5
        assert result.peak_force<25 and result.max_energy_residual<1e-10
        print(f"BY.8 {mode}: contact={result.contact_time:.3f} s, "
              f"force RMS={result.force_rms:.6f} N, final={result.final_force:.6f} N, "
              f"peak={result.peak_force:.6f} N, energy residual={result.max_energy_residual:.3e} J")
    bad=simulate(replay_cycle=3000)
    assert bad.fault=="STALE" and bad.cycles==3000
    print(f"BY.8 injected sensor replay -> {bad.fault} at cycle {bad.cycles}")


if __name__=="__main__":
    demo()
