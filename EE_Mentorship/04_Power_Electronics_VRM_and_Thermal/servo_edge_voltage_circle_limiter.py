"""EE MENTORSHIP - BAI 237 - BU.2: D-Q VOLTAGE CIRCLE LIMITER.

BUOC 1 - HOP CONG CU
  Chon gioi han vector cho vung tuyen tinh SVPWM:
    vmax = margin * Vdc / sqrt(3), margin=0.90
    magnitude = hypot(vd,vq); scale = min(1, vmax/magnitude)
    vd_applied = scale*vd; vq_applied = scale*vq
  limit_voltage(vd,vq,vbus,margin) tra VoltageVector co vd,vq,scale va
  saturated. Kep RIENG hai truc +/-vmax se co the tao norm sqrt(2)*vmax.
  scale chung giu huong vector, giam bien do. Vector 0 tra scale=1.

BUOC 2 - BAI TOAN TU LAM
  Vbus=48 V, yeu cau (vd,vq)=(30,40) V. Tu tim norm va vector sau limit;
  so voi kep rieng hai truc. Thu bus sut con 24 V.

BUOC 3 - PHONG VE
  Circle la tap dien ap cho plant averaged, KHONG tao PWM gate hay dam bao
  cua so shunt cua BT. Circle khong thuc hien field weakening, MTPA hay
  overmodulation. Anti-windup phai dung voltage DA limit. Chan Vbus<=0,
  margin ngoai (0,1], NaN/inf. CPU/RAM O(1).

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo, kiem tra norm va huong; commit/push BU.2.
  Nguon: https://microchiptech.github.io/mcaf-doc/6.0.2/algorithms/flux_control/fw_types/fw_eq_based.html
"""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class VoltageVector:
    vd: float
    vq: float
    scale: float

    @property
    def saturated(self) -> bool:
        return self.scale < 1.0


def limit_voltage(vd: float, vq: float, vbus: float, margin: float = 0.9) -> VoltageVector:
    if not all(math.isfinite(v) for v in (vd,vq,vbus,margin)) or vbus <= 0 or not 0 < margin <= 1:
        raise ValueError("Voltage/margin khong hop le")
    magnitude = math.hypot(vd,vq)
    if not math.isfinite(magnitude):
        raise ValueError("Voltage norm tran")
    maximum = margin*vbus/math.sqrt(3)
    scale = min(1.0, maximum/magnitude) if magnitude else 1.0
    return VoltageVector(vd*scale,vq*scale,scale)


def demo() -> None:
    result = limit_voltage(30,40,48)
    assert math.isclose(math.hypot(result.vd,result.vq), 0.9*48/math.sqrt(3))
    assert math.isclose(result.vd/result.vq, 0.75)
    print(f"BU.2: norm=50 -> {math.hypot(result.vd,result.vq):.6f} V, scale={result.scale:.6f}")


if __name__ == "__main__":
    demo()
