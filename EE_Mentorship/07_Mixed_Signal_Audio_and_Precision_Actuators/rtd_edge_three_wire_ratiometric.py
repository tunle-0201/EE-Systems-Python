"""EE MENTORSHIP - BAI 229 - MODULE BS.2: 3-WIRE RATIOMETRIC RTD.

BUOC 1 - HOP CONG CU
  Dau A noi dau tren RTD qua Ra. Hai dau B,C noi chung dau duoi qua Rb,Rc.
  Mo hinh MUX hai pha dong kich (khong la so do IC cu the):
    phase A->C: V_ac = I * (Rtd + Ra + Rc)
    phase B->C: V_bc = I * (Rb + Rc)
  Moi pha dung Vref=I*Rref voi Rref=1000 ohm, ADC unipolar 24-bit ly tuong:
    ratio = round((Vbranch/Vref)*(2^24-1))/(2^24-1)
    R_hat = Rref*(ratio_ac-ratio_bc) = Rtd + Ra - Rb
  Rc huy bo; chi khi Ra=Rb moi bu het dien tro day. Do 2-wire A->C cho
  Rtd+Ra+Rc. Wiring(lead_a,lead_b,return_c) luu ohm; ThreeWireAFE.convert
  nhan Rtd, current_a va wiring, tra RTDReading(resistance_ohm, clipped).

BUOC 2 - BAI TOAN TU LAM
  RTD tai 80 degC, moi day 1.2 ohm. Tu chon hai phep do de loai sai so
  day. Sau do cho Ra-Rb=0.2 ohm: du doan sai so nhiet con lai co dau nao?

BUOC 3 - PHONG VE
  Hai pha gia dinh RTD/day khong doi, ADC het settling, reference chinh xac,
  do dong thoi Vbranch/Vref trong tung pha. Khong mo phong IDAC mismatch,
  offset ADC/PGA, common-mode limits hay MUX charge injection. Doi reference
  resistor 0.1% van tao sai so scale: ratiometric khong xoa dung sai Rref.
  Clip phai bao loi; I=0 khong the do; chan day am, NaN/inf. Dut day can
  diagnostic rieng, khong the suy tu phep bu 3-wire. RAM/CPU O(1).

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo va so sai so 2-wire/3-wire/mismatch; commit/push BS.2.
  Nguon nguyen ly: https://www.ti.com/lit/an/sbaa275a/sbaa275a.pdf
"""

from __future__ import annotations

from dataclasses import dataclass
import math

from rtd_edge_pt100_callendar_van_dusen import resistance, temperature


@dataclass(frozen=True)
class Wiring:
    lead_a: float = 1.2
    lead_b: float = 1.2
    return_c: float = 1.2

    def __post_init__(self) -> None:
        if not all(math.isfinite(v) and v >= 0 for v in vars(self).values()):
            raise ValueError("Dien tro day phai huu han va khong am")


@dataclass(frozen=True)
class RTDReading:
    resistance_ohm: float
    clipped: bool = False


class ThreeWireAFE:
    def __init__(self, reference_ohm: float = 1000.0, bits: int = 24) -> None:
        if not math.isfinite(reference_ohm) or reference_ohm <= 0:
            raise ValueError("Reference resistor phai > 0")
        if not isinstance(bits, int) or not 2 <= bits <= 32:
            raise ValueError("ADC bits phai trong 2..32")
        self.reference_ohm = reference_ohm
        self.scale = (1 << bits) - 1

    def convert(self, rtd_ohm: float, current_a: float = 0.0005,
                wiring: Wiring | None = None) -> RTDReading:
        if not all(math.isfinite(v) and v > 0 for v in (rtd_ohm, current_a)):
            raise ValueError("RTD va dong kich phai huu han, duong")
        wires = wiring if wiring is not None else Wiring()
        reference_v = current_a * self.reference_ohm
        branch_resistances = (rtd_ohm + wires.lead_a + wires.return_c,
                              wires.lead_b + wires.return_c)
        codes = []
        clipped = False
        for branch in branch_resistances:
            ratio = current_a * branch / reference_v
            if not math.isfinite(ratio):
                raise ValueError("ADC ratio tran/khong huu han")
            clipped |= not 0 <= ratio <= 1
            code = round(max(0.0, min(1.0, ratio)) * self.scale)
            codes.append(code)
        estimated = self.reference_ohm * (codes[0] - codes[1]) / self.scale
        return RTDReading(estimated, clipped)


def demo() -> None:
    true_r, afe = resistance(80), ThreeWireAFE()
    balanced = afe.convert(true_r)
    mismatched = afe.convert(true_r, wiring=Wiring(1.4, 1.2, 1.2))
    two_wire_error = temperature(true_r + 2.4) - 80
    balanced_error = temperature(balanced.resistance_ohm) - 80
    mismatch_error = temperature(mismatched.resistance_ohm) - 80
    assert not balanced.clipped and abs(balanced_error) < 0.0002
    assert afe.convert(true_r, current_a=0.00045) == balanced
    print(f"BS.2: 2-wire error={two_wire_error:+.6f} degC, "
          f"3-wire={balanced_error:+.6f} degC, Ra-Rb=0.2 ohm -> {mismatch_error:+.6f} degC")


if __name__ == "__main__":
    demo()
