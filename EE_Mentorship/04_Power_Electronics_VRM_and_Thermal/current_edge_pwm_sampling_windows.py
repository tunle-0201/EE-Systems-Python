"""EE MENTORSHIP - BAI 233 - MODULE BT.2: PWM CURRENT SAMPLING WINDOW.

BUOC 1 - HOP CONG CU
  PWM center-aligned, high-side ON o giua chu ky T; duty d cho canh len tai
  (1-d)*T/2. Moi low-side shunt chi thay dong pha trong khoang low-side dan.
  Chon khoang dau chu ky khi CA HAI low-side A/B ON, khong can noi qua wrap:
    earliest = deadtime + amplifier_settle
    latest = min((1-da)*T/2, (1-db)*T/2) - deadtime - ADC_aperture
  Neu latest < earliest -> BLIND WINDOW. Khong duoc lay mau tai 0 A gia.
  PwmTiming.choose(da,db) tra SampleWindow(start_us,end_us) hoac None.
  trigger_us la trung diem cua khoang thoi gian BAT DAU aperture hop le.
  valid_at(da,db,t) kiem tra trigger co dung khoang an toan hay khong.

BUOC 2 - BAI TOAN TU LAM
  T=50 us (20 kHz), deadtime=0.4 us, settle=1.1 us, aperture=0.6 us.
  Tu tim trigger cho da=0.6, db=0.7; sau do thu da=0.95. Tai sao ADC nhanh
  van khong cuu duoc khi amplifier chua settle? Thu giam duty de mo lai cua so.

BUOC 3 - PHONG VE
  Day la quy uoc PWM va CHIEN LUOC LAY MAU CU THE, khong bao phu tat ca SVPWM,
  discontinuous PWM hay chi tiet diode/deadtime conduction. Khong tu doi duty
  de cuu mau vi se doi dien ap motor. Chua mo phong timer jitter, current ripple
  hay ADC skew; hai ADC duoc gia dinh lay mau dong thoi. Duty 0/1 hop le nhung
  duty 1 khong co khoang do low-side. CPU/RAM O(1) moi chu ky.

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo va kiem tra bien aperture; commit/push BT.2.
  Nguon settling/low-side: https://www.ti.com/lit/an/slyt762/slyt762.pdf
"""

from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class SampleWindow:
    start_us: float
    end_us: float

    @property
    def trigger_us(self) -> float:
        return (self.start_us + self.end_us) / 2


@dataclass(frozen=True)
class PwmTiming:
    period_us: float = 50.0
    deadtime_us: float = 0.4
    settle_us: float = 1.1
    aperture_us: float = 0.6

    def __post_init__(self) -> None:
        if not all(math.isfinite(v) for v in vars(self).values()):
            raise ValueError("PWM timing phai huu han")
        if min(self.period_us, self.aperture_us) <= 0 or min(self.deadtime_us, self.settle_us) < 0:
            raise ValueError("Period/aperture >0, deadtime/settle >=0")

    def choose(self, duty_a: float, duty_b: float) -> SampleWindow | None:
        if not all(math.isfinite(v) and 0 <= v <= 1 for v in (duty_a, duty_b)):
            raise ValueError("Duty phai trong [0,1]")
        earliest = self.deadtime_us + self.settle_us
        leading_edge = (1 - max(duty_a, duty_b)) * self.period_us / 2
        latest = leading_edge - self.deadtime_us - self.aperture_us
        if latest < earliest - 1e-12:
            return None
        return SampleWindow(earliest, max(earliest, latest))

    def valid_at(self, duty_a: float, duty_b: float, trigger_us: float) -> bool:
        window = self.choose(duty_a, duty_b)
        return (window is not None and math.isfinite(trigger_us)
                and window.start_us - 1e-12 <= trigger_us <= window.end_us + 1e-12)


def demo() -> None:
    timing = PwmTiming()
    window = timing.choose(0.6, 0.7)
    assert window is not None and timing.valid_at(0.6, 0.7, window.trigger_us)
    assert timing.choose(0.95, 0.7) is None
    print(f"BT.2: safe start={window.start_us:.3f}..{window.end_us:.3f} us, "
          f"trigger={window.trigger_us:.3f} us; duty=0.95 -> blind")


if __name__ == "__main__":
    demo()
