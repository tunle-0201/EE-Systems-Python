"""EE MENTORSHIP - BAI 247 - BV.6: HOMED ROBOT POSITION AXIS.

BUOC 1 - HOP CONG CU
  Kinematic homing fixture (BV.2) dat offset encoder, roi khoi tao PMSM BU
  dung tai vi tri latched. Hai move quintic: -0.2 -> +0.6 -> -0.4 rad.
  Position P + velocity FF 1 kHz -> speed PI 1 kHz + torque FF -> current
  PI 20 kHz -> rotating PMSM dq. Load torque that va estimate deu 0.01 Nm
  trong demo de tach anh huong cua feedforward. Tong iq_ref clamp +/-6 A.
  Encoder POSITION la bo dem nhieu vong ly tuong luong tu 16-bit/rev;
  speed estimator BU dung code wrapped. Khong nham raw encoder voi goc da home.
  simulate(use_feedforward=True,jam=False) tra PositionResult voi RMS/peak
  tracking, final error, homing time, so move DONE va fault.

BUOC 2 - BAI TOAN TU LAM
  Tu ghep 5 bai va cac vong BU. Thu tat torque feedforward, so RMS; chen
  clamp co khi ly tuong sau 0.3 s cua move dau va xem following-error trip.

BUOC 3 - PHONG VE
  Homing fixture dong hoc, KHONG dong plant dien-co trong giai doan homing.
  Khi jam=True, theta/omega bi giu co dinh boi reaction clamp ly tuong;
  khong mo phong contact elasticity/energy hay dung de dinh torque collision.
  Chi co sampled software supervision; sensors idq, load estimate va plant
  params ly tuong. Chua noi AFE BT, DC-link BU, geartrain, brake hay STO.
  Reference khong replan tu v/a tuy y; chi bat dau move moi sau DONE.
  Fault dong cong mo phong, khong chung minh truc that dung ngay. CPU O(N),
  state O(1), metrics tich luy thay vi luu trace.

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo/test va cap nhat roadmap; commit/push BV.6.
  Nguon: https://www.kollmorgen.com/sites/default/files/public_downloads/SCuser.pdf
"""

from dataclasses import dataclass
import math

from axis_edge_acceleration_feedforward import acceleration_current
from axis_edge_homing_state_machine import homing_fixture
from axis_edge_motion_supervisor import MotionSupervisor
from axis_edge_position_velocity_cascade import PositionController
from axis_edge_quintic_motion_profile import QuinticMove
from servo_edge_cascaded_pi_controller import CurrentPI, SpeedPI
from servo_edge_encoder_speed_estimator import SpeedEstimator, encoder_code
from servo_edge_pmsm_dq_plant import PMSM


@dataclass(frozen=True)
class PositionResult:
    tracking_rms: float
    peak_error: float
    final_error: float
    home_time: float
    completed_moves: int
    fault: str | None


def simulate(use_feedforward: bool = True, jam: bool = False) -> PositionResult:
    home,physical,home_time = homing_fixture()
    if home.state != "HOMED":
        raise AssertionError("Homing fixture failed")
    motor = PMSM()
    motor.theta = physical
    speed, current, estimator = SpeedPI(),CurrentPI(),SpeedEstimator()
    position_pi = PositionController()
    resolution = math.tau/65536
    dt = 50e-6
    iq_ref = omega_ref = total_square = peak = 0.0
    samples = completed = 0
    fault = None
    jam_theta = None
    final_error = 0.0
    def measured_position() -> float:
        return home.position(round((motor.theta+10)/resolution)*resolution)
    for target in (0.6,-0.4):
        move = QuinticMove(measured_position(),target)
        supervisor = MotionSupervisor()
        for cycle in range(math.ceil((move.duration+0.8)/dt)):
            now = cycle*dt
            measured_speed = estimator.update(encoder_code(motor.theta),dt)
            if cycle % 20 == 0:
                reference = move.sample(now)
                measured = measured_position()
                supervisor.update(now,reference,measured,measured_speed,True,now > move.duration)
                error = reference.position-measured
                peak = max(peak,abs(error))
                total_square += error**2
                samples += 1
                final_error = target-measured
                if supervisor.fault:
                    fault = supervisor.fault
                    break
                if supervisor.state == "DONE":
                    completed += 1
                    break
                omega_ref = position_pi.command(reference,measured)
                feedback = speed.step(omega_ref,measured_speed,0.001)
                feedforward = acceleration_current(reference,motor.config,0.01) if use_feedforward else 0.0
                iq_ref = max(-6.0,min(6.0,feedback+feedforward))
            applied = current.step(motor.id,motor.iq,iq_ref,measured_speed,48,dt)
            previous_theta = motor.theta
            motor.step(applied.vd,applied.vq,0.01,dt)
            if jam and completed == 0 and now >= 0.3:
                if jam_theta is None:
                    jam_theta = previous_theta
                motor.theta,motor.omega = jam_theta,0.0
        else:
            fault = "NOT_SETTLED"
        if fault:
            break
    rms = math.sqrt(total_square/samples)
    return PositionResult(rms,peak,final_error,home_time,completed,fault)


def demo() -> None:
    good = simulate()
    no_ff = simulate(use_feedforward=False)
    blocked = simulate(jam=True)
    assert good.fault is None and good.completed_moves == 2
    assert abs(good.final_error) < 0.001 and good.tracking_rms < 0.01
    assert good.tracking_rms < no_ff.tracking_rms
    assert blocked.fault == "FOLLOWING_ERROR"
    print(f"BV.6: RMS={good.tracking_rms:.8f} rad, no torque FF={no_ff.tracking_rms:.8f} rad, "
          f"peak={good.peak_error:.8f} rad, final error={good.final_error:.8f} rad, "
          f"home={good.home_time:.3f} s, DONE={good.completed_moves}, fault={good.fault}")
    print(f"BV.6 jam injection -> {blocked.fault}")


if __name__ == "__main__":
    demo()
