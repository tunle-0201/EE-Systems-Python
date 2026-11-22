"""EE MENTORSHIP - BAI 226 - MODULE BR.3: ZERO/SPAN THERMAL CALIBRATION.

BUOC 1 - HOP CONG CU
  Can mau CHUAN da biet luc, khong tu hoc tu vat chua biet khoi luong.
  Tai moi nhiet do T, do ratio khi 0 N (z) va khi tai chuan Fcal (r_load):
    span(T) = (r_load - z) / Fcal       [ratio/N]
    force = (ratio - z(T)) / span(T)   [N]
  Dung hai moc 20 va 50 degC, noi suy z/span RIENG RE:
    alpha = (T - T0)/(T1 - T0)
    z(T) = z0 + alpha*(z1-z0); span(T) = s0 + alpha*(s1-s0)
  CalibrationPoint(temp_c, zero_ratio, loaded_ratio, known_force_n) la so do
  trong phong calibration. TemperatureCalibration.fit(low, high) tinh he so;
  force(ratio, temp_c) doi so do sang N, tu choi ngoai mien nhiet da hoc.

BUOC 2 - BAI TOAN TU LAM
  Dung tai 80 N tai 20/50 degC de fit. Tu kiem tra tren tai MOI 37 N tai
  35 degC; so voi calibration chi tai 20 degC de nhin thay drift.

BUOC 3 - PHONG VE
  Hai moc nhiet phai khac nhau, span duong va khong gan zero, tai chuan >0.
  Khong extrapolate; khong tare khi dang kep vat vi se xoa luc that. Mo hinh
  chi bu zero/span tuyen tinh; chua xu ly creep, hysteresis, gradient nhiet
  hay sai so nhiet ke. Tu hieu chuan bang cung mo hinh khong chung minh do
  chinh xac phan cung. CPU/RAM O(1), luu hai zero va hai span thay vi bang lon.

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo va test force ngoai tap calibration; commit/push BR.3.
  Nguon ve zero/span drift: https://www.ti.com/lit/an/sbaa532a/sbaa532a.pdf
  https://www.ni.com/en/shop/data-acquisition/sensor-fundamentals/measuring-strain-with-strain-gages/how-is-temperature-affecting-your-strain-measurement-accuracy-.html
"""

from __future__ import annotations

from dataclasses import dataclass
import math

from strain_edge_ratiometric_adc_filter import RatiometricADC
from strain_edge_wheatstone_bridge import FullBridge


@dataclass(frozen=True)
class CalibrationPoint:
    temp_c: float
    zero_ratio: float
    loaded_ratio: float
    known_force_n: float

    @property
    def span(self) -> float:
        return (self.loaded_ratio - self.zero_ratio) / self.known_force_n


@dataclass(frozen=True)
class TemperatureCalibration:
    low: CalibrationPoint
    high: CalibrationPoint

    def __post_init__(self) -> None:
        for point in (self.low, self.high):
            if not all(math.isfinite(v) for v in vars(point).values()):
                raise ValueError("Calibration point phai huu han")
            if point.known_force_n <= 0 or point.span <= 1e-12:
                raise ValueError("Tai chuan va span phai duong, span khong gan zero")
        if self.high.temp_c <= self.low.temp_c:
            raise ValueError("Hai moc nhiet phai tang nghiem ngat")

    @classmethod
    def fit(cls, low: CalibrationPoint, high: CalibrationPoint) -> TemperatureCalibration:
        return cls(low, high)

    def force(self, ratio: float, temp_c: float) -> float:
        if not math.isfinite(ratio) or not math.isfinite(temp_c):
            raise ValueError("Phep do phai huu han")
        if not self.low.temp_c <= temp_c <= self.high.temp_c:
            raise ValueError("Ngoai mien nhiet calibration")
        alpha = (temp_c - self.low.temp_c) / (self.high.temp_c - self.low.temp_c)
        zero = self.low.zero_ratio + alpha * (self.high.zero_ratio - self.low.zero_ratio)
        span = self.low.span + alpha * (self.high.span - self.low.span)
        return (ratio - zero) / span


def lab_calibration(bridge: FullBridge, adc: RatiometricADC) -> TemperatureCalibration:
    """Fixture 0/80 N tai 20/50 degC; trong thuc te phai dung tai chuan do duoc."""
    points = []
    for temp in (20.0, 50.0):
        readings = [bridge.sample(force, temp) for force in (0.0, 80.0)]
        ratios = []
        for reading in readings:
            sample = adc.quantize(reading.differential_v, reading.excitation_v)
            if sample.clipped:
                raise ValueError("ADC clipping trong calibration")
            ratios.append(sample.ratio)
        points.append(CalibrationPoint(temp, ratios[0], ratios[1], 80.0))
    return TemperatureCalibration.fit(*points)


def demo() -> None:
    bridge, adc = FullBridge(), RatiometricADC()
    calibration = lab_calibration(bridge, adc)
    reading = bridge.sample(37, 35, 4.6)
    sample = adc.quantize(reading.differential_v, reading.excitation_v)
    uncompensated = (sample.ratio - calibration.low.zero_ratio) / calibration.low.span
    compensated = calibration.force(sample.ratio, 35)
    assert abs(compensated - 37) < 0.0001
    print(f"BR.3: truth=37 N @ 35 degC, room-only={uncompensated:.6f} N, "
          f"thermal-compensated={compensated:.6f} N")


if __name__ == "__main__":
    demo()
