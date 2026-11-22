"""EE MENTORSHIP - BAI 224 - MODULE BR.1: FULL-BRIDGE STRAIN GAUGE.

BUOC 1 - HOP CONG CU
  Strain = delta_length / length (khong don vi); gauge factor GF = 2:
    delta_R / R = GF * strain
  Bon dien tro 350 ohm xep thanh hai nhanh, moi nhanh hai dien tro noi tiep.
  R1,R3 o tren; R2,R4 o duoi. Cap excitation Vexc giua dau tren va mass.
    Vleft = Vexc * R2/(R1+R2); Vright = Vexc * R4/(R3+R4)
    ratio = (Vleft - Vright) / Vexc
  Chon R1=R4=R*(1-d), R2=R3=R*(1+d) -> ratio = d CHINH XAC.
  Tai 100 N -> strain 1000 microstrain -> d=0.002 -> 2 mV/V.
  Moi dong mau: GF*strain*(1 + span_tc*delta_T) + zero + zero_tc*delta_T.
  BridgeSpec: tham so mo hinh, khong phai datasheet mot load cell cu the.
  sample(force_n, temp_c, excitation_v): tra dien ap vi sai, common-mode,
  excitation va bon dien tro. ratio la phep chia dien ap, chua phai luc N.

BUOC 2 - BAI TOAN TU LAM
  Tu tinh dien tro va dien ap o -100, 0, +100 N voi Vexc=5 V. Sau do doi
  Vexc sang 4.5 V: vi sao dien ap doi nhung ty so mV/V khong doi?

BUOC 3 - PHONG VE
  Nhiet lam bon dien tro cung doi thi ty so ly tuong khong doi. Zero/span
  drift con lai duoc mo hinh rieng; full bridge khong loai moi loi nhiet.
  Khong mo phong creep, hysteresis, lead resistance, dut day hay tu nung.
  Bien dang dan hoi chi la gia dinh; khong dung mo hinh de chung minh kha
  nang chiu qua tai cua phan cung. Chan thong so NaN/inf va dien tro am.
  RAM/CPU O(1) moi mau; 4 floats tuong ung bon nhanh cau dien tro.

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo -> cau ly tuong -10/0/+10 mV tai 5 V; commit/push BR.1.
  Nguon: https://www.ni.com/docs/en-US/bundle/ni-daqmx/page/full1.html
  https://www.ti.com/lit/an/sbaa532a/sbaa532a.pdf
"""

from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class BridgeSpec:
    resistance_ohm: float = 350.0
    full_scale_n: float = 100.0
    strain_at_full_scale: float = 0.001
    gauge_factor: float = 2.0
    reference_temp_c: float = 20.0
    common_tcr_per_c: float = 25e-6
    zero_ratio: float = 30e-6
    zero_tc_per_c: float = 2e-6
    span_tc_per_c: float = -400e-6

    def __post_init__(self) -> None:
        if not all(math.isfinite(v) for v in vars(self).values()):
            raise ValueError("BridgeSpec phai huu han")
        if min(self.resistance_ohm, self.full_scale_n,
               self.strain_at_full_scale, self.gauge_factor) <= 0:
            raise ValueError("R, full scale, strain va GF phai duong")


@dataclass(frozen=True)
class BridgeReading:
    differential_v: float
    common_mode_v: float
    excitation_v: float
    resistances_ohm: tuple[float, float, float, float]

    @property
    def ratio(self) -> float:
        return self.differential_v / self.excitation_v


class FullBridge:
    def __init__(self, spec: BridgeSpec | None = None) -> None:
        self.spec = spec if spec is not None else BridgeSpec()

    def sample(self, force_n: float, temp_c: float = 20.0,
               excitation_v: float = 5.0) -> BridgeReading:
        if not all(math.isfinite(v) for v in (force_n, temp_c, excitation_v)):
            raise ValueError("Dau vao cau phai huu han")
        if excitation_v <= 0:
            raise ValueError("Excitation phai > 0")
        cfg = self.spec
        delta_t = temp_c - cfg.reference_temp_c
        strain = force_n / cfg.full_scale_n * cfg.strain_at_full_scale
        d = (cfg.gauge_factor * strain * (1 + cfg.span_tc_per_c * delta_t)
             + cfg.zero_ratio + cfg.zero_tc_per_c * delta_t)
        resistance = cfg.resistance_ohm * (1 + cfg.common_tcr_per_c * delta_t)
        if not math.isfinite(d) or abs(d) >= 0.25 or resistance <= 0:
            raise ValueError("Ngoai mien cau dan hoi gia dinh")
        r1 = r4 = resistance * (1 - d)
        r2 = r3 = resistance * (1 + d)
        left = excitation_v * r2 / (r1 + r2)
        right = excitation_v * r4 / (r3 + r4)
        return BridgeReading(left - right, (left + right) / 2,
                             excitation_v, (r1, r2, r3, r4))


def demo() -> None:
    ideal = FullBridge(BridgeSpec(zero_ratio=0, zero_tc_per_c=0, span_tc_per_c=0))
    for force in (-100, 0, 100):
        reading = ideal.sample(force)
        assert math.isclose(reading.differential_v, force * 0.0001, abs_tol=1e-14)
        assert math.isclose(reading.ratio, ideal.sample(force, excitation_v=4.5).ratio,
                            abs_tol=1e-15)
        print(f"BR.1: F={force:+4d} N, Vdiff={reading.differential_v * 1000:+.4f} mV, "
              f"ratio={reading.ratio * 1000:+.4f} mV/V")


if __name__ == "__main__":
    demo()
