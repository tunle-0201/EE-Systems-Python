"""
================================================================================
CHUYEN DE AQ: DIEN TU CONG SUAT BANG THONG RONG GAN / SIC & GATE DRIVER SIEU TOC
BAI 3 (MILESTONE AQ.3): MACH PHAT HIEN MAT BAO HOA DESAT VA CAT MEM SOFT TURN-OFF
================================================================================
Chuc nang he thong:
1. Mo phong co che phat hien mat bao hoa (Desaturation Detection - DESAT) bao ve
   ngan mach SiC MOSFET duoi thoi gian chiu dung toi han t_sc < 1.5 micro-giay.
2. Mo hinh hoa mach loc thoi gian lam mo (Blanking Time Filter):
      t_blank = (C_blank * V_desat_th) / I_chg
   loc bo xung dien ap V_ds cao gia tao trong pha bat ban dau.
3. So sanh co che cat cung (Hard Turn-Off) gay xung qua ap chet nguoi L * (di/dt)
   voi co che cat mem (Soft Turn-Off - STO) kiem soat toc do suy giam dong dien.
4. Tinh toan nang luong xung dot ngan mach va kiem chung kha nang bao ve an toan.

QUY TAC KHONG GIAN TOAN HOC THUAN ASCII:
               C_blank * V_desat_th
   t_blank = ────────────────────────
                       I_chg

   V_desat = V_ds + V_diode_f

   V_overshoot_hard = L_parasitic * (di_sc / dt_hard)
   V_overshoot_soft = L_parasitic * (di_sc / dt_soft)
   V_ds_peak        = V_bus + V_overshoot
================================================================================
"""

import math
from dataclasses import dataclass
from typing import List, Tuple, Dict


@dataclass
class DesatCircuitParams:
    """Thong so mach bao ve DESAT va Soft Turn-Off ben trong Gate Driver."""
    v_desat_threshold: float  # Dien ap nguong ngat DESAT (V), thuong 7.0V - 9.0V
    i_charge_current: float   # Nguon dong nap noi bo (A), thuong 250 - 500 uA
    c_blanking: float         # Tu dien lam mo ngoai (F), thuong 100 - 220 pF
    v_diode_forward: float    # Dien ap thuan cua diode cao ap HV Desat Diode (V)
    l_parasitic_loop: float   # Do tu cam ky sinh vong cong suat DC bus (Henry)
    v_ds_breakdown: float     # Dien ap danh thung toi han cua SiC (V)


@dataclass
class ProtectionResult:
    """Ket qua mo phong bao ve ngan mach."""
    fault_detected: bool
    detection_time_us: float
    blanking_time_us: float
    peak_current_a: float
    hard_turn_off_v_peak: float
    hard_turn_off_destroyed: bool
    soft_turn_off_v_peak: float
    soft_turn_off_destroyed: bool
    energy_dissipated_j: float


class DesatProtectionCore:
    """
    Dong co mo phong mach phat hien mat bao hoa va ngat mem (DESAT & STO).
    """

    def __init__(self, params: DesatCircuitParams, v_bus: float, r_ds_on: float):
        self.params = params
        self.v_bus = v_bus
        self.r_ds_on = r_ds_on

    def calculate_blanking_time(self) -> float:
        """
        Tinh thoi gian lam mo ly thuyet khi diode bi chan:
        t_blank = (C_blank * V_th) / I_chg
        """
        return (self.params.c_blanking * self.params.v_desat_threshold) / self.params.i_charge_current

    def simulate_fault_response(
        self,
        is_short_circuit: bool,
        i_fault_target: float,
        fault_occurrence_us: float = 0.5,
        dt_us: float = 0.005,       # 5 ns resolution
        t_total_us: float = 3.0
    ) -> ProtectionResult:
        """
        Mo phong chu trinh phat hien va dap ung bao ve khi co su co ngan mach.
        """
        steps = int(t_total_us / dt_us)
        t_blank_us = self.calculate_blanking_time() * 1e6

        v_desat = 0.0
        c_desat_v = 0.0
        fault_detected = False
        t_detect_us = 0.0
        current_i = 0.0
        peak_current = 0.0
        energy_j = 0.0

        for step in range(steps):
            t_us = step * dt_us

            # Tinh toan dong tai / dong ngan mach
            if not is_short_circuit:
                # Che do dan binh thuong: dong dinh muc 80A
                current_i = 80.0
            else:
                if t_us < fault_occurrence_us:
                    current_i = 80.0
                else:
                    # Ngan mach xay ra: dong tang vot voi toc do cuc nhanh di/dt ~ 30000 A/us (30 A/ns)
                    delta_t = t_us - fault_occurrence_us
                    current_i = min(i_fault_target, 80.0 + 30000.0 * delta_t)

            if current_i > peak_current:
                peak_current = current_i

            # Tinh dien ap roi tren van V_ds:
            if not is_short_circuit or t_us < fault_occurrence_us:
                # Vung Ohmic: V_ds = I * R_ds_on
                v_ds = current_i * self.r_ds_on
            else:
                # Vung mat bao hoa (Desaturation): V_ds tang vot len gan dien ap Bus
                v_ds = min(self.v_bus, 10.0 + (self.v_bus - 10.0) * (current_i / i_fault_target))

            # Dien ap tai chan DESAT:
            # Khi V_ds thap: Diode thuan dan, ghim V_desat = V_ds + V_diode
            # Khi V_ds cao: Diode bi phan cuc nguoc, C_blank duoc nap boi nguon dong I_chg
            v_diode_clamp = v_ds + self.params.v_diode_forward
            if v_diode_clamp < self.params.v_desat_threshold:
                # Diode dan xa dien tich tu C_blank xuong V_ds
                c_desat_v = v_diode_clamp
            else:
                # Diode bi phan cuc nguoc (Reverse Biased)!
                # Nguon dong nap tu C_blank voi toc do: dV/dt = I_chg / C_blank
                dv_dt_v_per_s = self.params.i_charge_current / self.params.c_blanking
                c_desat_v += dv_dt_v_per_s * (dt_us * 1e-6)

            v_desat = c_desat_v

            # Tinh tich luy nhiet nang: E = integral(V_ds * I_ds * dt)
            energy_j += v_ds * current_i * (dt_us * 1e-6)

            # Kiem tra nguong so sanh DESAT Fault
            if v_desat >= self.params.v_desat_threshold and not fault_detected:
                fault_detected = True
                t_detect_us = t_us
                break  # Driver kich hoat ngat bao ve!

        # -------------------------------------------------------------
        # SO SANH 2 CO CHE NGAT: HARD TURN-OFF VS SOFT TURN-OFF
        # -------------------------------------------------------------
        # 1. Hard Turn-Off: Ngat nhanh bang duong xa cong thong thuong (dt_hard ~ 25 ns)
        dt_hard_s = 25e-9
        di_dt_hard = peak_current / dt_hard_s
        v_overshoot_hard = self.params.l_parasitic_loop * di_dt_hard
        hard_v_peak = self.v_bus + v_overshoot_hard
        hard_destroyed = (hard_v_peak >= self.params.v_ds_breakdown)

        # 2. Soft Turn-Off (STO): Ngat em qua dien tro xa lon R_sto (dt_soft ~ 350 ns)
        dt_soft_s = 350e-9
        di_dt_soft = peak_current / dt_soft_s
        v_overshoot_soft = self.params.l_parasitic_loop * di_dt_soft
        soft_v_peak = self.v_bus + v_overshoot_soft
        soft_destroyed = (soft_v_peak >= self.params.v_ds_breakdown)

        return ProtectionResult(
            fault_detected=fault_detected,
            detection_time_us=t_detect_us,
            blanking_time_us=t_blank_us,
            peak_current_a=peak_current,
            hard_turn_off_v_peak=hard_v_peak,
            hard_turn_off_destroyed=hard_destroyed,
            soft_turn_off_v_peak=soft_v_peak,
            soft_turn_off_destroyed=soft_destroyed,
            energy_dissipated_j=energy_j
        )


def main():
    print("=" * 80)
    print("EE MENTORSHIP MODULE AQ - LESSON 3: DESAT PROTECTION & SOFT TURN-OFF")
    print("=" * 80)

    # Thong so mach bao ve cong nghiep chuan SiC (TI UCC21710 / ADI ADuM4135)
    v_bus_800v = 800.0
    r_ds_on_sic = 0.016  # 16 mOhm
    
    # Do tu cam ky sinh vong cong suat giua Bus Capacitor va SiC Module: 25 nH
    # Dien ap danh thung toi han cua SiC MOSFET 1200V: 1200V
    params = DesatCircuitParams(
        v_desat_threshold=6.5,      # Nguong ngat 6.5V toi uu cho SiC
        i_charge_current=500e-6,    # Nguon dong nap 500 uA
        c_blanking=33e-12,          # Tu lam mo nho 33 pF dap ung sub-microsecond
        v_diode_forward=0.8,        # Diode cao ap 0.8V
        l_parasitic_loop=25e-9,     # 25 nH parasitic inductance
        v_ds_breakdown=1200.0       # Dien ap danh thung 1200V
    )

    core = DesatProtectionCore(params, v_bus=v_bus_800v, r_ds_on=r_ds_on_sic)
    t_blank_calc = core.calculate_blanking_time() * 1e6
    print(f"\n[INFO] Thoi gian lam mo ly thuyet (Blanking Time): {t_blank_calc:.3f} us")

    # -------------------------------------------------------------
    # KICH BAN 1: VAN HANH BINH THUONG (NORMAL OPERATION)
    # -------------------------------------------------------------
    print("\n[1] TEST KICH BAN 1: VAN HANH BINH THUONG (I_load = 80A):")
    res_normal = core.simulate_fault_response(is_short_circuit=False, i_fault_target=80.0)
    print(f"  Phat hien loi DESAT: {res_normal.fault_detected}")
    print(f"  Dong dinh muc: {res_normal.peak_current_a:.1f} A")
    print(f"  Dien ap V_ds khi dan: {80.0 * r_ds_on_sic:.2f} V")
    print(f"  Dien ap chan DESAT: {(80.0 * r_ds_on_sic) + params.v_diode_forward:.2f} V (Nguong: {params.v_desat_threshold}V)")
    assert not res_normal.fault_detected, "Van hanh binh thuong khong duoc bao dong gia!"

    # -------------------------------------------------------------
    # KICH BAN 2: SU CO NGAN MACH PHA (SHORT-CIRCUIT FAULT 1000A)
    # -------------------------------------------------------------
    print("\n[2] TEST KICH BAN 2: SU CO NGAN MACH TOAN PHAN (I_sc = 1000A):")
    res_sc = core.simulate_fault_response(
        is_short_circuit=True,
        i_fault_target=1000.0,
        fault_occurrence_us=0.2
    )

    print(f"  Phat hien loi DESAT: {res_sc.fault_detected}")
    print(f"  Thoi diem cat loi: {res_sc.detection_time_us:.3f} us (Khoang cach tu luc loi: {res_sc.detection_time_us - 0.2:.3f} us)")
    print(f"  Dong dinh ngan mach: {res_sc.peak_current_a:.1f} A")
    print(f"  Nang luong phong toa tren van: {res_sc.energy_dissipated_j:.3f} Joules")

    print("\n[3] SO SANH CO CHE NGAT KHI PHAT HIEN NGAN MACH:")
    print(f"{'Co che ngat':<25} | {'Dien ap dinh V_ds (V)':<25} | {'Gioi han V_rated (V)':<22} | {'Ket qua linh kien':<20}")
    print("-" * 98)
    status_hard = "NO TUNG DIE (EXPLODED!)" if res_sc.hard_turn_off_destroyed else "SONG SOT"
    status_soft = "NO TUNG DIE (EXPLODED!)" if res_sc.soft_turn_off_destroyed else "CUU SONG AN TOAN"
    print(f"{'Hard Turn-Off (25 ns)':<25} | {res_sc.hard_turn_off_v_peak:<25.1f} | {params.v_ds_breakdown:<22.1f} | {status_hard:<20}")
    print(f"{'Soft Turn-Off (350 ns)':<25} | {res_sc.soft_turn_off_v_peak:<25.1f} | {params.v_ds_breakdown:<22.1f} | {status_soft:<20}")

    # -------------------------------------------------------------
    # KIEM TRA CAC RANG BUOC HE THONG & ASSERTIONS
    # -------------------------------------------------------------
    # 1. Thoi gian phat hien su co phai duoi 1.0 us de khong lam chay hong die SiC
    t_response = res_sc.detection_time_us - 0.2
    assert res_sc.fault_detected, "Phai phat hien loi ngan mach 100%"
    assert t_response < 1.0, f"Thoi gian phan ung phai < 1.0 us, thuc te={t_response:.3f} us"
    print(f"\n[INFO] Thoi gian phan ung ngat DESAT: {t_response*1000:.1f} ns (< 1000 ns dat chuan ASIL-D)")

    # 2. Hard Turn-Off gay xung qua ap vuot 1200V danh thung van
    assert res_sc.hard_turn_off_destroyed, "Hard Turn-Off phai vuot nguong 1200V gay no linh kien"
    assert res_sc.hard_turn_off_v_peak > 1500.0, "Hard Turn-Off phai gay xung dien ap cuc cao"

    # 3. Soft Turn-Off giu dien ap duoi 1200V dam bao SiC MOSFET song sot
    assert not res_sc.soft_turn_off_destroyed, "Soft Turn-Off phai cuu song duoc SiC MOSFET"
    assert res_sc.soft_turn_off_v_peak < params.v_ds_breakdown, "V_peak Soft Turn-Off phai duoi 1200V"
    safety_margin_v = params.v_ds_breakdown - res_sc.soft_turn_off_v_peak
    print(f"[INFO] Bien do an toan cua Soft Turn-Off con du: {safety_margin_v:.1f} V")

    print("\n>> [PASSED] TEST SUITE 100% SUCCESSFUL: DESAT & SOFT TURN-OFF VERIFIED!")


if __name__ == "__main__":
    main()
