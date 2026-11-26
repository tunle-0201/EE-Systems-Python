"""EE MENTORSHIP - BAI 246 - BV.5: SOFT LIMIT / FOLLOWING ERROR / SETTLING.

BUOC 1 - HOP CONG CU
  MotionSupervisor.update(now,reference,position,velocity,homed,finished):
    HOMED bat buoc; reference va position nam trong [-1,1] rad.
    |q_ref-q_actual| >0.1 rad lien tuc >=20 ms -> FOLLOWING_ERROR chot.
    finished va |error|<=0.001 rad, |velocity|<=0.1 rad/s lien tuc >=50 ms
    -> DONE. Neu chua on dinh -> SETTLING; dang chay -> MOVING.
  Dwell dung thoi gian that, khong dem mot mau tot thanh move complete.
  now phai tang; khoang tick >3 ms -> TIMING, vi monitor chon chu ky 1 kHz.

BUOC 2 - BAI TOAN TU LAM
  Chen sai so 0.2 rad trong 5 ms va 25 ms, so ket qua. Tai sao chi kiem tra
  q_error=0 o mot thoi diem chua du de ket luan truc da dung? Thu q_ref ngoai
  soft limits va thu quen homing.

BUOC 3 - PHONG VE
  Soft limits phu thuoc encoder/home dung, khong thay hard-limit switch hay
  STO. Chi tick caller moi phat hien timing; khong watchdog doc lap. Khong
  co braking-distance envelope, collision sensing hay safety certification.
  Fault chot, khong tu clear; DONE co the ve SETTLING neu bi day lech.
  CPU/RAM O(1), chi luu thoi diem bat dau following-error/settling.

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo/test thoi gian bien va fault latch; commit/push BV.5.
  Nguon settling/following error: https://www.kollmorgen.com/sites/default/files/public_downloads/SCuser.pdf
"""

import math

from axis_edge_quintic_motion_profile import MotionPoint


class MotionSupervisor:
    def __init__(self) -> None:
        self.last_time: float | None = None
        self.error_since: float | None = None
        self.settled_since: float | None = None
        self.state = "MOVING"
        self.fault: str | None = None
        self.drive_enabled = False

    def update(self, now: float, reference: MotionPoint, position: float,
               velocity: float, homed: bool, finished: bool) -> str:
        self.drive_enabled = False
        if self.fault is not None:
            return self.state
        if not all(math.isfinite(v) for v in (now,reference.position,position,velocity)):
            self.fault = "NONFINITE"
        elif self.last_time is not None and (now <= self.last_time or now-self.last_time > 0.003+1e-12):
            self.fault = "TIMING"
        elif not homed:
            self.fault = "NOT_HOMED"
        elif not -1 <= reference.position <= 1 or not -1 <= position <= 1:
            self.fault = "SOFT_LIMIT"
        else:
            self.last_time = now
            error = abs(reference.position-position)
            if error > 0.1:
                if self.error_since is None:
                    self.error_since = now
                if now-self.error_since >= 0.020-1e-12:
                    self.fault = "FOLLOWING_ERROR"
            else:
                self.error_since = None
            if finished and error <= 0.001 and abs(velocity) <= 0.1:
                if self.settled_since is None:
                    self.settled_since = now
                self.state = "DONE" if now-self.settled_since >= 0.050-1e-12 else "SETTLING"
            else:
                self.settled_since = None
                self.state = "SETTLING" if finished else "MOVING"
        if self.fault is not None:
            self.state = "FAULT"
        else:
            self.drive_enabled = True
        return self.state


def demo() -> None:
    supervisor = MotionSupervisor()
    for k in range(51):
        supervisor.update(k/1000,MotionPoint(0.6),0.6,0,True,True)
    assert supervisor.state == "DONE" and supervisor.drive_enabled
    print(f"BV.5: held endpoint for 50 ms -> {supervisor.state}")


if __name__ == "__main__":
    demo()
