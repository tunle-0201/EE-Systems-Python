"""EE MENTORSHIP - BAI 228 - MODULE BS.1: PT100 CALLENDAR-VAN DUSEN.

BUOC 1 - HOP CONG CU
  Pt100 co R0 = 100 ohm tai 0 degC. Chon he so platinum alpha=0.00385:
    R(T) = R0 * (1 + A*T + B*T^2)                    khi T >= 0
    R(T) = R0 * (1 + A*T + B*T^2 + C*(T-100)*T^3)   khi T < 0
    A = 3.9083e-3; B = -5.775e-7; C = -4.183e-12
  resistance(temp_c) tra ohm. temperature(resistance_ohm) dung chia doi
  tren [-200,850] degC: so R(mid) voi Rdo, giu nua khoang co nghiem.
  48 buoc -> be rong khoang <= 1050/2^48 degC. Day la sai so so hoc,
  KHONG phai do chinh xac thuc cua Pt100/ADC. R(T) don dieu trong mien nay.
  Xap xi tuyen tinh (R/R0-1)/0.00385 chi de so sanh, khong thay CVD.

BUOC 2 - BAI TOAN TU LAM
  Tu tinh R tai -100, 0, 100 degC, roi doi nguoc tu ohm sang degC. Chon
  chia doi thay vi bang tra; thu he so C=0 tai -100 degC va phan tich sai so.

BUOC 3 - PHONG VE
  Chan NaN/inf va du lieu ngoai mien. Gia tri R=0/dut day khong phai nhiet
  do hop le. Day la duong dac tinh danh dinh, chua co tolerance class, drift,
  hysteresis, dien tro day hay self-heating. Khong chung nhan IEC compliance.
  RAM O(1); CPU O(48) phep tinh cho inverse, khong can NumPy/SciPy.

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo va doi chieu R(100)=138.5055 ohm; commit/push BS.1.
  Nguon he so: https://www.ti.com/lit/an/sbaa275a/sbaa275a.pdf
  https://www.analog.com/media/en/reference-design-documentation/reference-designs/cn0383.pdf
"""

from __future__ import annotations

import math

R0_OHM = 100.0
A = 3.9083e-3
B = -5.775e-7
C = -4.183e-12
MIN_TEMP_C = -200.0
MAX_TEMP_C = 850.0


def resistance(temp_c: float) -> float:
    if not math.isfinite(temp_c) or not MIN_TEMP_C <= temp_c <= MAX_TEMP_C:
        raise ValueError("Pt100 temperature phai trong [-200,850] degC")
    ratio = 1 + A * temp_c + B * temp_c**2
    if temp_c < 0:
        ratio += C * (temp_c - 100) * temp_c**3
    return R0_OHM * ratio


def temperature(resistance_ohm: float) -> float:
    if (not math.isfinite(resistance_ohm)
            or not resistance(MIN_TEMP_C) <= resistance_ohm <= resistance(MAX_TEMP_C)):
        raise ValueError("Dien tro nam ngoai mien Pt100 danh dinh")
    low, high = MIN_TEMP_C, MAX_TEMP_C
    for _ in range(48):
        midpoint = (low + high) / 2
        if resistance(midpoint) < resistance_ohm:
            low = midpoint
        else:
            high = midpoint
    return (low + high) / 2


def demo() -> None:
    for truth in (-100.0, 0.0, 100.0, 500.0):
        measured_r = resistance(truth)
        estimate = temperature(measured_r)
        linear = (measured_r / R0_OHM - 1) / 0.00385
        assert abs(estimate - truth) < 1e-10
        print(f"BS.1: T={truth:+7.1f} degC, R={measured_r:.6f} ohm, "
              f"inverse={estimate:.6f} degC, linear_error={linear - truth:+.4f} degC")


if __name__ == "__main__":
    demo()
