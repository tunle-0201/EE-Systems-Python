"""EE MENTORSHIP - BAI 245 - BV.4: ACCELERATION/LOAD TORQUE FEEDFORWARD.

BUOC 1 - HOP CONG CU
  Tu plant co khi: torque = J*acceleration + friction*velocity + load.
  SPMSM, id_ref=0: Kt = 1.5*p*flux [Nm/A], iq_ff = torque/Kt.
  acceleration_current(reference,config,load_estimate_nm) tra iq_ff [A].
  Cong iq_ff vao speed-PI feedback, ROI moi clamp tong iq_ref +/-6 A.
  Velocity feedforward o BV.3 co don vi rad/s; torque feedforward o day co
  don vi A sau khi chia Kt. Khong cong hai don vi nay voi nhau.

BUOC 2 - BAI TOAN TU LAM
  J=0.0002, friction=0.0001, p=4, flux=0.02; a=6 rad/s^2, v=1 rad/s,
  load_est=0.01 Nm. Tu tinh iq_ff va thu load estimate sai dau.

BUOC 3 - PHONG VE
  Feedforward khong thay feedback; sai J/load/gear ratio tao sai so. Model
  hien tai direct-drive, khong gear, khong gravity map. Khong tu hoc load.
  Ham khong clamp de caller co the limit TONG lenh feedback+feedforward;
  speed PI trong capstone chi thay saturation cua chinh no, chua tracking
  anti-windup ngoai cho moi truong hop tong lenh saturation. CPU/RAM O(1).

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo va so torque/current units; commit/push BV.4.
  Nguon torque: https://www.mathworks.com/help/mcb/ref/pmsmtorqueestimator.html
"""

import math

from axis_edge_quintic_motion_profile import MotionPoint
from servo_edge_pmsm_dq_plant import MotorConfig


def acceleration_current(reference: MotionPoint, config: MotorConfig,
                         load_estimate_nm: float = 0.0) -> float:
    if not all(math.isfinite(v) for v in (reference.velocity,reference.acceleration,load_estimate_nm)):
        raise ValueError("Feedforward inputs phai huu han")
    torque = config.inertia*reference.acceleration+config.friction*reference.velocity+load_estimate_nm
    return torque/(1.5*config.pole_pairs*config.flux)


def demo() -> None:
    current = acceleration_current(MotionPoint(0,1,6),MotorConfig(),0.01)
    assert math.isclose(current,0.0113/0.12)
    print(f"BV.4: acceleration + friction + 0.01 Nm load -> iq_ff={current:.6f} A")


if __name__ == "__main__":
    demo()
