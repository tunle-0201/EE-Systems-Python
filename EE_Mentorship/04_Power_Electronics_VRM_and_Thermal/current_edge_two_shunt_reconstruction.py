"""EE MENTORSHIP - BAI 234 - MODULE BT.3: TWO-SHUNT CURRENT RECONSTRUCTION.

BUOC 1 - HOP CONG CU
  Motor sao KHONG noi neutral, khong co dong ro: ia+ib+ic=0 (KCL).
  Do dong thoi ia/ib trong cua so low-side hop le, suy ra ic=-ia-ib.
  Clarke amplitude-invariant: i_alpha=ia; i_beta=(ia+2*ib)/sqrt(3).
  Day la toa do tinh, chua co phep Park hay goc rotor.
  TwoShuntFrame(cycle,trigger_us,a,b) mang hai ADC sample cung chu ky/trigger.
  reconstruct(frame,cal_a,cal_b,temp,duties,timing) kiem tra cua so va ADC,
  giai ma hai kenh doc lap roi tra PhaseCurrents(ia,ib,ic).

BUOC 2 - BAI TOAN TU LAM
  Cho ia=3 A, ib=-1 A: tu tim ic va alpha/beta. Chen offset rieng tung kenh,
  hieu chuan roi quay vector dong tron 360 deg. Phan tich kenh thu ba khi mot
  ADC bi clip, PWM khong co cua so, hoac lay mau khac thoi diem.

BUOC 3 - PHONG VE
  Tong ia+ib+ic=0 sau reconstruction la DANG THUC TU TAO; khong dung no de
  tuyen bo phat hien duoc sensor drift. Sai so ic co the bang tong sai so hai
  kenh. Khong ap dung neu co neutral/leakage hay common-mode current dang ke.
  Timestamp/trigger la metadata, chua chung minh dong bo phan cung. Khong
  giu mau cu hay thay bang 0 khi invalid. CPU/RAM O(1) moi frame.

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo, so sai so ba pha tren ca vong dien; commit/push BT.3.
  Nguon KCL/two-shunt: https://ww1.microchip.com/downloads/en/AppNotes/01299A.pdf
"""

from __future__ import annotations

from dataclasses import dataclass
import math

from current_edge_pwm_sampling_windows import PwmTiming
from current_edge_shunt_afe_calibration import ADCReading, Calibration, ShuntAFE, calibrate


@dataclass(frozen=True)
class TwoShuntFrame:
    cycle: int
    trigger_us: float
    a: ADCReading
    b: ADCReading


@dataclass(frozen=True)
class PhaseCurrents:
    ia: float
    ib: float
    ic: float

    @property
    def alpha_beta(self) -> tuple[float, float]:
        return self.ia, (self.ia + 2 * self.ib) / math.sqrt(3)


def reconstruct(frame: TwoShuntFrame, cal_a: Calibration, cal_b: Calibration,
                temp_c: float, duties: tuple[float, float, float],
                timing: PwmTiming) -> PhaseCurrents:
    if len(duties) != 3 or not all(math.isfinite(d) and 0 <= d <= 1 for d in duties):
        raise ValueError("Can 3 duty hop le")
    if not timing.valid_at(duties[0], duties[1], frame.trigger_us):
        raise ValueError("Khong co cua so lay mau hoac trigger ngoai cua so")
    ia = cal_a.decode(frame.a, temp_c)
    ib = cal_b.decode(frame.b, temp_c)
    return PhaseCurrents(ia, ib, -ia - ib)


def demo() -> None:
    afe_a, afe_b = ShuntAFE(), ShuntAFE(-70e-6, -0.003)
    cal_a, cal_b = calibrate(afe_a), calibrate(afe_b)
    timing = PwmTiming()
    duties = (0.6, 0.7, 0.4)
    window = timing.choose(*duties[:2])
    errors = []
    for degree in range(360):
        angle = math.radians(degree)
        ia, ib = 12 * math.sin(angle), 12 * math.sin(angle - 2 * math.pi / 3)
        frame = TwoShuntFrame(degree, window.trigger_us, afe_a.convert(ia, 100), afe_b.convert(ib, 100))
        measured = reconstruct(frame, cal_a, cal_b, 100, duties, timing)
        errors.extend((measured.ia - ia, measured.ib - ib, measured.ic + ia + ib))
    maximum = max(abs(e) for e in errors)
    assert maximum < 0.04
    print(f"BT.3: 360 angles, three-phase max error={maximum:.6f} A")


if __name__ == "__main__":
    demo()
