"""EE MENTORSHIP - BAI 221 - MODULE BQ.2: SINCOS CALIBRATION & UNWRAP.

BUOC 1 - HOP CONG CU
  Mo hinh cam bien MOT chu ky dien / vong co, kenh da vuong pha:
    s_raw = offset_s + gain_s * sin(theta)
    c_raw = offset_c + gain_c * cos(theta)
  Khi quay tron vong cham, deu, lay du mau phu cac cuc tri:
    offset = (max + min) / 2; gain = (max - min) / 2
    s = (s_raw - offset_s) / gain_s; c = (c_raw - offset_c) / gain_c
    angle = degrees(atan2(s, c)) modulo 360
  calibrate(samples): uoc luong offset/gain tu cac cap (sin, cos).
  angle(s_raw, c_raw): tra goc; hypot(s,c) kiem tra dut day/sai bien do.
  signed_delta(now, before) = (now - before + 180) modulo 360 - 180
  Cong delta de unwrap: 359 -> 1 cho +2 deg, khong phai -358 deg.

BUOC 2 - BAI TOAN TU LAM
  S co offset +0.18, gain 1.12; C co offset -0.09, gain 0.87. Tu chon cong cu
  bu sai so, quay qua 360 deg va so sanh sai so truoc/sau bu tren tap goc MOI.

BUOC 3 - PHONG VE
  Min/max chi dung khi tap hieu chuan bao phu DU VONG va nhieu nho. Khong sua
  lech pha, meo hai, clipping, hay cam bien nhieu cuc; khong tu nhan la fit ellipse.
  Unwrap chi dung khi chuyen dong giua hai mau < 180 deg. Mat nguyen vong se
  khong the phat hien tu goc wrapped; can gioi han toc do va thoi gian lay mau.
  Tu choi NaN/inf va vector bien do qua nho/lon. RAM O(N) luc calibration,
  O(1) khi doc goc; CPU O(N) calibration, O(1) moi mau.

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo, so sanh RMS va unwrap; commit/push BQ.2.
  Nguon: https://www.ti.com/lit/ug/sprui54/sprui54.pdf (gain/offset + atan2).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable


def signed_delta(now: float, before: float) -> float:
    return (now - before + 180.0) % 360.0 - 180.0


@dataclass(frozen=True)
class SinCosCalibration:
    offset_s: float
    offset_c: float
    gain_s: float
    gain_c: float

    def __post_init__(self) -> None:
        if not all(math.isfinite(v) for v in (
            self.offset_s, self.offset_c, self.gain_s, self.gain_c
        )) or min(self.gain_s, self.gain_c) <= 0:
            raise ValueError("He so calibration phai huu han, gain > 0")

    @classmethod
    def calibrate(cls, samples: Iterable[tuple[float, float]]) -> SinCosCalibration:
        points = list(samples)
        if len(points) < 8 or not all(
            math.isfinite(s) and math.isfinite(c) for s, c in points
        ):
            raise ValueError("Can >= 8 mau huu han phu du vong")
        sins, coses = zip(*points)
        return cls((max(sins) + min(sins)) / 2,
                   (max(coses) + min(coses)) / 2,
                   (max(sins) - min(sins)) / 2,
                   (max(coses) - min(coses)) / 2)

    def angle(self, s_raw: float, c_raw: float) -> float:
        s = (s_raw - self.offset_s) / self.gain_s
        c = (c_raw - self.offset_c) / self.gain_c
        if not all(math.isfinite(v) for v in (s, c)) or not 0.75 <= math.hypot(s, c) <= 1.25:
            raise ValueError("Bien do sin/cos khong hop le")
        return math.degrees(math.atan2(s, c)) % 360.0


def sensor_sample(angle_deg: float) -> tuple[float, float]:
    """Mo hinh co offset/gain; khong chen nhieu hay lech pha."""
    theta = math.radians(angle_deg)
    return 0.18 + 1.12 * math.sin(theta), -0.09 + 0.87 * math.cos(theta)


def demo() -> None:
    cal = SinCosCalibration.calibrate(sensor_sample(k) for k in range(360))
    raw_errors, corrected_errors = [], []
    for k in range(720):
        truth = (k + 0.37) / 2
        s, c = sensor_sample(truth)
        raw_errors.append(signed_delta(math.degrees(math.atan2(s, c)), truth))
        corrected_errors.append(signed_delta(cal.angle(s, c), truth))
    rms = lambda values: math.sqrt(sum(v * v for v in values) / len(values))
    continuous = 358.0
    previous = 358.0
    for wrapped in (359.0, 0.0, 1.0, 2.0):
        continuous += signed_delta(wrapped, previous)
        previous = wrapped
    assert rms(corrected_errors) < 1e-10 and continuous == 362.0
    print(f"BQ.2: RMS raw={rms(raw_errors):.4f} deg, "
          f"calibrated={rms(corrected_errors):.10f} deg, unwrap={continuous:.1f} deg")


if __name__ == "__main__":
    demo()
