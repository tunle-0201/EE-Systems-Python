"""EE MENTORSHIP - BAI 244 - BV.3: POSITION P + VELOCITY FEEDFORWARD.

BUOC 1 - HOP CONG CU
  Vong vi tri 1 kHz tao lenh toc do cho speed PI cua BU:
    position_error = q_ref-q_measured [rad]
    omega_ref = clip(v_ref + kp_position*position_error, +/-2 rad/s)
  kp_position=20 [1/s]; v_ref tu dao ham quy dao, khong phai toc do do duoc.
  PositionController.command(MotionPoint,position) tra omega_ref. P chi sua
  sai lech vi tri; velocity feedforward cho phep di chuyen ma khong can tao
  sai lech lon de sinh lenh toc do.

BUOC 2 - BAI TOAN TU LAM
  Vref=1 rad/s, q_error=0.01 rad. Tu tinh omega_ref, so khi bo vref, thu
  q_error lon va giai thich vi sao can clamp lenh toc do.

BUOC 3 - PHONG VE
  Encoder raw phai duoc home va unwrap truoc; TUYET DOI khong dung shortest
  angle path cho truc co travel limits. Clamp khong thay soft limit hay
  following-error monitor. Gains phai duoc tune cung speed/current loops;
  khong tu khang dinh on dinh voi gear resonance. CPU/RAM O(1).

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo lenh vref + feedback; commit/push BV.3.
  Nguon servo loops: https://www.kollmorgen.com/sites/default/files/public_downloads/SCuser.pdf
"""

import math

from axis_edge_quintic_motion_profile import MotionPoint


class PositionController:
    def __init__(self, kp: float = 20, speed_limit: float = 2) -> None:
        if not all(math.isfinite(v) and v > 0 for v in (kp,speed_limit)):
            raise ValueError("Position gain/speed limit phai duong")
        self.kp, self.speed_limit = kp,speed_limit

    def command(self, reference: MotionPoint, measured_position: float) -> float:
        if not all(math.isfinite(v) for v in (reference.position,reference.velocity,measured_position)):
            raise ValueError("Position inputs phai huu han")
        raw = reference.velocity+self.kp*(reference.position-measured_position)
        return max(-self.speed_limit,min(self.speed_limit,raw))


def demo() -> None:
    command = PositionController().command(MotionPoint(0.5,1.0),0.49)
    assert math.isclose(command,1.2)
    print(f"BV.3: 1 rad/s feedforward + 0.01 rad error -> command={command:.6f} rad/s")


if __name__ == "__main__":
    demo()
