"""EE MENTORSHIP - BAI 243 - BV.2: HOMING SEEK/BACKOFF/LATCH.

BUOC 1 - HOP CONG CU
  Homing dat lien he giua encoder raw va goc co khi. State:
    IDLE -> SEEK (-0.3 rad/s) -> BACKOFF (+0.1) -> LATCH (-0.03) -> HOMED.
  Bat dau tren cam thi BACKOFF truoc. Cam release roi moi cho phep LATCH;
  3 mau ON lien tiep trong LATCH xac nhan moc, khong phai hardware latch.
  offset = raw_at_latch - home_position (-0.2 rad); position = raw-offset.
  start(now,raw,switch_active) khoi tao; update(now,raw,switch_active) tra
  lenh velocity. position(raw) chi hop le khi HOMED. Thoi gian toi da 5 s,
  do doi raw so voi diem dau toi da 1 rad.

BUOC 2 - BAI TOAN TU LAM
  Raw encoder co offset +10 rad. Tu tim goc -0.2 rad, thu bat dau tren cam,
  bounce ON/OFF, switch ket ON/OFF va timestamp giam.

BUOC 3 - PHONG VE
  Capstone dung homing fixture dong hoc ly tuong, khong dong PMSM trong luc
  homing. Zero duoc chot sau debounce nen co sai so do toc do/sample period.
  Khong co zero-index, hardware latch, hard limit hay cable diagnostic that.
  Fault chot, can tao workflow reset/homing moi ben ngoai; khong tu clear.
  Caller phai tick, timeout khong chay nen. CPU/RAM O(1).

BUOC 4 - KIEM CHUNG VA GIT
  Chay fixture va test switch ket; commit/push BV.2.
  Nguon: https://download.beckhoff.com/download/document/automation/twincat3/TF5200_homing_en.pdf
"""

import math


class HomingFSM:
    def __init__(self, home_position: float = -0.2) -> None:
        if not math.isfinite(home_position):
            raise ValueError("Home position phai huu han")
        self.home_position = home_position
        self.state = "IDLE"
        self.offset: float | None = None
        self.fault: str | None = None
        self.started_at = self.last_time = self.start_raw = 0.0
        self.pressed_samples = 0

    def start(self, now: float, raw: float, switch_active: bool) -> None:
        if self.state != "IDLE" or not all(math.isfinite(v) for v in (now,raw)):
            raise ValueError("Chi start tu IDLE voi du lieu huu han")
        self.started_at = self.last_time = now
        self.start_raw = raw
        self.state = "BACKOFF" if switch_active else "SEEK"

    @property
    def velocity(self) -> float:
        return {"SEEK":-0.3,"BACKOFF":0.1,"LATCH":-0.03}.get(self.state,0.0)

    def update(self, now: float, raw: float, switch_active: bool) -> float:
        if self.fault is not None or self.state == "HOMED":
            return 0.0
        if self.state == "IDLE":
            raise ValueError("Phai start homing truoc")
        if not all(math.isfinite(v) for v in (now,raw)) or now <= self.last_time:
            self.fault = "CLOCK_OR_SENSOR"
        elif now-self.started_at >= 5:
            self.fault = "TIMEOUT"
        elif abs(raw-self.start_raw) > 1:
            self.fault = "TRAVEL"
        else:
            self.last_time = now
            if self.state == "SEEK" and switch_active:
                self.state = "BACKOFF"
            elif self.state == "BACKOFF" and not switch_active:
                self.state = "LATCH"
            elif self.state == "LATCH":
                self.pressed_samples = self.pressed_samples+1 if switch_active else 0
                if self.pressed_samples >= 3:
                    self.offset = raw-self.home_position
                    self.state = "HOMED"
        if self.fault is not None:
            self.state = "FAULT"
        return self.velocity

    def position(self, raw: float) -> float:
        if self.state != "HOMED" or not math.isfinite(raw):
            raise ValueError("Position can HOMED va raw huu han")
        return raw-self.offset


def homing_fixture() -> tuple[HomingFSM,float,float]:
    """Kinematic actuator 1 kHz; cong tac tai goc co khi -0.2 rad."""
    fsm, physical = HomingFSM(),0.25
    fsm.start(0,physical+10,False)
    for tick in range(1,5001):
        physical += fsm.velocity*0.001
        now = tick*0.001
        fsm.update(now,physical+10,physical <= -0.2)
        if fsm.state == "HOMED" or fsm.fault is not None:
            return fsm,physical,now
    raise AssertionError("Fixture khong ket thuc")


def demo() -> None:
    fsm,physical,time = homing_fixture()
    assert fsm.state == "HOMED" and abs(fsm.position(physical+10)+0.2) < 1e-10
    print(f"BV.2: state={fsm.state}, time={time:.3f} s, "
          f"raw offset={fsm.offset:.8f} rad, physical={physical:.8f} rad")


if __name__ == "__main__":
    demo()
