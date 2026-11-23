"""EE MENTORSHIP - BAI 230 - MODULE BS.3: SELF-HEATING & PULSED EXCITATION.

BUOC 1 - HOP CONG CU
  Dong kich tao nhiet tren chinh cam bien: power_mw = 1000 * I^2 * R(T).
  Dissipation H = 0.4 mW/degC (tham so gia dinh cua goi cam bien):
    equilibrium_rise = power_mw / H
    dTs/dt = (Tenv + equilibrium_rise - Ts) / tau
  Cam bien RC bac 1, tau=0.5 s. Giu R(Ts) trong mot buoc dt, tich phan RC:
    Ts_new = Ts + (Tenv + equilibrium_rise - Ts)*(1-exp(-dt/tau))
  ThermalRTD(initial_temp_c, dissipation_mw_per_c, tau_sec).step(Tenv,I,dt)
  tra Ts, la nhiet do PHAN TU do duoc, co the khac nhiet do vat can do.
  excitation_on(tick, period_ticks=100, on_ticks=10): lich 10 ms ON moi
  100 ms voi dt=1 ms. Duty=10%; cong suat trung binh xap xi I^2*R*duty.

BUOC 2 - BAI TOAN TU LAM
  Tai 80 degC, so dong 3 mA lien tuc va 3 mA xung 10%. Tu chon lich kich,
  do o CUOI khoang ON, so bias tai thoi diem do, khong chi trung binh ca chu ky.

BUOC 3 - PHONG VE
  ON phai du lau cho hai pha MUX/ADC settling; thiet ke bai nay gia dinh
  tong settling <10 ms, chua mo phong settling dien. Dung lich tick nguyen
  de tranh sai so modulo float tai canh xung. Khi OFF, I=0 -> khong do ohm.
  Pulsing giam tu nung nhung khong loai tre nhiet cam bien. H va tau thay
  doi theo lap dat/luong gio; khong lay con so mo phong lam datasheet.
  R(T) duoc cap nhat moi buoc: giam dt de kiem tra hoi tu khi can. CPU/RAM O(1).

BUOC 4 - KIEM CHUNG VA GIT
  Chay demo so bias cuoi ON va bias DC; commit/push BS.3.
  Nguon: https://www.ti.com/lit/an/sbaa275a/sbaa275a.pdf
  https://www.analog.com/en/resources/technical-articles/rtd-measurement-system-design-essentials.html
"""

from __future__ import annotations

import math

from rtd_edge_pt100_callendar_van_dusen import resistance


def excitation_on(tick: int, period_ticks: int = 100, on_ticks: int = 10) -> bool:
    if not all(isinstance(v, int) for v in (tick, period_ticks, on_ticks)):
        raise ValueError("Lich excitation dung tick nguyen")
    if tick < 0 or period_ticks <= 0 or not 1 <= on_ticks <= period_ticks:
        raise ValueError("Tick >= 0, 1 <= on_ticks <= period_ticks")
    return tick % period_ticks < on_ticks


class ThermalRTD:
    def __init__(self, initial_temp_c: float = 20.0,
                 dissipation_mw_per_c: float = 0.4, tau_sec: float = 0.5) -> None:
        resistance(initial_temp_c)
        if not all(math.isfinite(v) and v > 0 for v in (dissipation_mw_per_c, tau_sec)):
            raise ValueError("H va tau phai huu han, duong")
        self.sensor_temp_c = initial_temp_c
        self.dissipation_mw_per_c = dissipation_mw_per_c
        self.tau_sec = tau_sec

    def step(self, environment_c: float, current_a: float, dt_sec: float) -> float:
        resistance(environment_c)
        if not math.isfinite(current_a) or current_a < 0:
            raise ValueError("Dong kich phai huu han, khong am")
        if not math.isfinite(dt_sec) or dt_sec <= 0:
            raise ValueError("dt phai huu han, duong")
        power_mw = 1000 * current_a**2 * resistance(self.sensor_temp_c)
        equilibrium = environment_c + power_mw / self.dissipation_mw_per_c
        next_temp = self.sensor_temp_c + (equilibrium - self.sensor_temp_c) * (
            -math.expm1(-dt_sec / self.tau_sec))
        resistance(next_temp)  # Chan tran/mo hinh vuot mien truoc khi thay doi state.
        self.sensor_temp_c = next_temp
        return next_temp


def demo() -> None:
    continuous, pulsed = ThermalRTD(80), ThermalRTD(80)
    sampled_bias = []
    for tick in range(15000):
        on = excitation_on(tick)
        continuous.step(80, 0.003, 0.001)
        pulsed.step(80, 0.003 if on else 0, 0.001)
        if tick >= 10000 and tick % 100 == 9:
            sampled_bias.append(pulsed.sensor_temp_c - 80)
    dc_bias = continuous.sensor_temp_c - 80
    pulse_bias = sum(sampled_bias) / len(sampled_bias)
    assert 0 < pulse_bias < dc_bias * 0.15
    print(f"BS.3: 3 mA @ 80 degC, DC bias={dc_bias:.6f} degC, "
          f"10% duty end-ON bias={pulse_bias:.6f} degC")


if __name__ == "__main__":
    demo()
