"""EE MENTORSHIP - BAI 232 - MODULE BT.1: SHUNT CURRENT AFE.

BUOC 1 - HOP CONG CU
  Rshunt=1 milliohm, gain=50, ADC 12-bit 0..3.3 V, bias=1.65 V:
    R(T) = R25 * (1 + 50e-6*(T-25))
    Vout = 1.65 + gain*(1+gain_error)*(I*R(T) + input_offset_v)
    code = round(Vout/3.3 * 4095); Pshunt = I^2 * R(T)
  ShuntAFE.convert(current_a, temp_c) tra ADCReading(code, clipped).
  Calibration.fit(negative, positive, reference_a=10) dung tai chuan +/-10 A:
    zero_code = (code_plus + code_minus)/2
    slope = (code_plus - code_minus)/(2*reference_a) [counts/A]
    I_hat = (code-zero_code)/(slope*(1+50e-6*(T-25)))
  decode(reading,temp) bu shunt TCR da biet, khong bu drift gain/offset nhiet.

BUOC 2 - BAI TOAN TU LAM
  Tu tinh cong suat shunt o 20 A; hieu chuan voi offset 100 uV va gain error
  +0.4%, roi kiem tra tai MOI -17..17 A tai 25/100 degC. Vi sao dong am can
  bias giua thang ADC? LSB danh dinh = 3.3/(4095*50*0.001) = 0.01612 A.

BUOC 3 - PHONG VE
  Calibration khi PWM OFF va tai chuan da biet; khong coi motor dang tai la
  0 A. Clip tu choi, khong giai ma rail thanh dong that. Mo hinh khong co
  inductance shunt, Kelvin layout, ADC noise, common-mode transient hay input
  settling; viec lay mau duoc hoc rieng o BT.2. Do phan giai khac do chinh xac.
  CPU/RAM O(1); hai he so calibration tuong ung hai thanh ghi MCU.

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo kiem tra loi luong tu va Pshunt; commit/push BT.1.
  Nguon: https://www.ti.com/lit/an/slyt762/slyt762.pdf
"""

from __future__ import annotations

from dataclasses import dataclass
import math

ADC_MAX = 4095
SHUNT_OHM = 0.001
SHUNT_TCR = 50e-6


def thermal_factor(temp_c: float) -> float:
    if not math.isfinite(temp_c) or not -40 <= temp_c <= 150:
        raise ValueError("Nhiet shunt ngoai mien mo phong -40..150 degC")
    return 1 + SHUNT_TCR * (temp_c - 25)


@dataclass(frozen=True)
class ADCReading:
    code: int
    clipped: bool = False


class ShuntAFE:
    def __init__(self, input_offset_v: float = 100e-6, gain_error: float = 0.004) -> None:
        if not all(math.isfinite(v) for v in (input_offset_v, gain_error)) or gain_error <= -1:
            raise ValueError("Offset/gain phai huu han va gain > 0")
        self.input_offset_v = input_offset_v
        self.gain_error = gain_error

    def convert(self, current_a: float, temp_c: float = 25) -> ADCReading:
        if not math.isfinite(current_a):
            raise ValueError("Dong dien phai huu han")
        shunt = SHUNT_OHM * thermal_factor(temp_c)
        voltage = 1.65 + 50 * (1 + self.gain_error) * (current_a * shunt + self.input_offset_v)
        if not math.isfinite(voltage):
            raise ValueError("AFE voltage tran")
        clipped = not 0 <= voltage <= 3.3
        code = round(max(0.0, min(3.3, voltage)) / 3.3 * ADC_MAX)
        return ADCReading(code, clipped)


@dataclass(frozen=True)
class Calibration:
    zero_code: float
    counts_per_a: float

    def __post_init__(self) -> None:
        if (not math.isfinite(self.zero_code) or not 0 <= self.zero_code <= ADC_MAX
                or not math.isfinite(self.counts_per_a) or self.counts_per_a <= 0):
            raise ValueError("Calibration khong hop le")

    @classmethod
    def fit(cls, negative: ADCReading, positive: ADCReading,
            reference_a: float = 10.0) -> Calibration:
        for reading in (negative, positive):
            cls.validate(reading)
        if not math.isfinite(reference_a) or reference_a <= 0:
            raise ValueError("Reference current phai duong")
        return cls((positive.code + negative.code) / 2,
                   (positive.code - negative.code) / (2 * reference_a))

    @staticmethod
    def validate(reading: ADCReading) -> None:
        if reading.clipped or not isinstance(reading.code, int) or not 0 <= reading.code <= ADC_MAX:
            raise ValueError("ADC clip hoac code khong hop le")

    def decode(self, reading: ADCReading, temp_c: float = 25) -> float:
        self.validate(reading)
        return (reading.code - self.zero_code) / (self.counts_per_a * thermal_factor(temp_c))


def calibrate(afe: ShuntAFE) -> Calibration:
    """Fixture +/-10 A tai 25 degC; khong uoc luong tu dong khi motor dang chay."""
    return Calibration.fit(afe.convert(-10), afe.convert(10))


def demo() -> None:
    afe = ShuntAFE()
    calibration = calibrate(afe)
    errors = [calibration.decode(afe.convert(current, temp), temp) - current
              for current in range(-17, 18) for temp in (25, 100)]
    maximum = max(abs(error) for error in errors)
    assert maximum < 0.025
    print(f"BT.1: max error={maximum:.6f} A, "
          f"Pshunt(20 A,100 degC)={20**2 * SHUNT_OHM * thermal_factor(100):.6f} W")


if __name__ == "__main__":
    demo()
