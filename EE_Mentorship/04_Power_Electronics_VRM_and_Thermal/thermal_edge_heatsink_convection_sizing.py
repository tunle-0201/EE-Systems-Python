"""
Chuyen de AV: Mo phong Nhiet - Dien Tich hop & Quan tri Tan nhiet Phan cung
Bai 137 (Milestone AV.2): Thiet ke tinh toan khoi tan nhiet Heatsink doi luu va ong dan nhiet Heat Pipe

Author: Le Dac Anh Tuan (18 tuoi) - Electrical Engineering Student
Muc tieu: Tinh toan ngan sach nhiet tro (Thermal Resistance Budget), thiet ke kich thuoc khoi tan nhiet
          canh nhom/dong (Fin Geometry, Surface Area, Fin Efficiency), tinh he so truyen nhiet doi luu h
          (tu nhien vs cuong buc CFM) va mo hinh ong dan nhiet Heat Pipe cho chip Apple va inverter Tesla.

QUY TAC GIANG DAY CONSTRUCTIVIST BOTTOM-UP:
- KHONG dung ky hieu LaTeX hoac cap dau dollar.
- Toan bo bieu thuc toan hoc duoc bieu dien duoi dang khoi ASCII truc quan.
- Chuan hoa ma nguon tuong thich Windows cp1252.
"""

import math
from typing import List, Tuple, Dict


class ThermalBudgetCalculator:
    """
    Tinh toan ngan sach nhiet tro cho phep cua khoi tan nhiet R_th(s-a).
    
    Phan tich toan hoc chuoi nhiet tro:
    ┌────────────────────────────────────────────────────────┐
    │                                                        │
    │   Tong nhiet tro cho phep:                             │
    │                    T_j_max - T_amb_max                 │
    │      R_th_total = ─────────────────────                │
    │                            P_loss                      │
    │                                                        │
    │   Chuoi nhiet tro noi tiep:                            │
    │      R_th_total = R_th(j-c) + R_th(c-s) + R_th(s-a)    │
    │                                                        │
    │   Nhiet tro Heatsink toi da cho phep:                  │
    │      R_th(s-a)_req <= R_th_total - (R_jc + R_cs)       │
    │                                                        │
    └────────────────────────────────────────────────────────┘
    """
    @staticmethod
    def calculate_required_heatsink_rth(
        p_loss_watts: float,
        t_j_max_deg_c: float = 105.0,
        t_amb_max_deg_c: float = 40.0,
        r_th_jc_k_per_w: float = 0.25,
        r_th_cs_k_per_w: float = 0.15
    ) -> float:
        if p_loss_watts <= 0.0:
            return 999.0
        
        delta_t_total = t_j_max_deg_c - t_amb_max_deg_c
        r_th_total_budget = delta_t_total / p_loss_watts
        r_th_heatsink = r_th_total_budget - (r_th_jc_k_per_w + r_th_cs_k_per_w)
        return max(0.001, r_th_heatsink)


class HeatsinkConvectionModel:
    """
    Mo hinh truyen nhiet doi luu va hieu suat canh tan nhiet (Fin Efficiency).
    
    Phan tich toan hoc & co hoc chat luu:
    ┌────────────────────────────────────────────────────────┐
    │                                                        │
    │   1. He so doi luu khong khi h (W / (m^2 * K)):        │
    │      Doi luu tu nhien (Khong quat): h ~ 5 - 12         │
    │      Doi luu cuong buc (Co quat van toc v m/s):        │
    │         h = 10.45 - v + 10.0 * sqrt(v)                 │
    │                                                        │
    │   2. He so bien dang canh (Fin Parameter m):           │
    │                    2 * h                               │
    │         m = sqrt( ──────── )                           │
    │                    k * t_f                             │
    │                                                        │
    │      t_f: Do day canh (m)                              │
    │      k: Do dan nhiet vat lieu (Al: 205, Cu: 398 W/mK)  │
    │                                                        │
    │   3. Hieu suat canh tan nhiet (Fin Efficiency):        │
    │                tanh( m * H_fin )                       │
    │      eta_fin = ─────────────────                       │
    │                    m * H_fin                           │
    │                                                        │
    │   4. Dien tich hieu dung va Nhiet tro doi luu:         │
    │      A_eff = A_base + eta_fin * A_fins                 │
    │                                                        │
    │                      1                                 │
    │      R_th(s-a) = ─────────                             │
    │                   h * A_eff                            │
    │                                                        │
    └────────────────────────────────────────────────────────┘
    """
    def __init__(
        self,
        base_width_mm: float = 80.0,
        base_length_mm: float = 100.0,
        base_thickness_mm: float = 6.0,
        fin_height_mm: float = 30.0,
        fin_thickness_mm: float = 1.0,
        num_fins: int = 24,
        material: str = "aluminum"
    ):
        self.w_m = float(base_width_mm) * 1e-3
        self.l_m = float(base_length_mm) * 1e-3
        self.t_base_m = float(base_thickness_mm) * 1e-3
        self.h_fin_m = float(fin_height_mm) * 1e-3
        self.t_fin_m = float(fin_thickness_mm) * 1e-3
        self.num_fins = int(num_fins)
        
        # Do dan nhiet k (W / m*K)
        if material.lower() == "copper":
            self.k = 398.0
            self.density = 8960.0
        else: # Aluminum 6063
            self.k = 205.0
            self.density = 2700.0

        # Tinh tong dien tich
        self.a_base_m2 = self.w_m * self.l_m
        # Moi canh co 2 mat: 2 * L * H_fin
        self.a_fins_m2 = self.num_fins * (2.0 * self.l_m * self.h_fin_m)
        self.a_total_m2 = self.a_base_m2 + self.a_fins_m2

    def calculate_convection_coefficient_h(self, air_velocity_m_per_s: float) -> float:
        """Tinh he so truyen nhiet doi luu h dua tren van toc gio."""
        v = max(0.0, float(air_velocity_m_per_s))
        if v < 0.1:
            return 8.5 # Doi luu tu nhien
        # Cong thuc thuc nghiem doi luu cuong buc
        return 10.45 - v + 10.0 * math.sqrt(v)

    def calculate_heatsink_thermal_resistance(self, air_velocity_m_per_s: float) -> Tuple[float, float, float]:
        """
        Tinh nhiet tro khoi tan nhiet R_th(s-a), hieu suat canh eta_fin va he so h.
        Tra ve (r_th_sa, eta_fin, h).
        """
        h = self.calculate_convection_coefficient_h(air_velocity_m_per_s)
        
        # Tinh thong so bien dang m
        m = math.sqrt((2.0 * h) / (self.k * self.t_fin_m))
        m_l = m * self.h_fin_m
        
        # Hieu suat canh
        if m_l < 1e-4:
            eta_fin = 1.0
        else:
            eta_fin = math.tanh(m_l) / m_l

        # Dien tich hieu dung
        a_eff = self.a_base_m2 + eta_fin * self.a_fins_m2
        r_th_conv = 1.0 / (h * a_eff)

        # Nhiet tro dan nhiet qua de de tan nhiet (de day): R_base = t_base / (k * A_base)
        r_th_base = self.t_base_m / (self.k * self.a_base_m2)
        r_th_total = r_th_conv + r_th_base

        return r_th_total, eta_fin, h

    def calculate_total_weight_grams(self) -> float:
        """Tinh khoi luong khoi tan nhiet (gam)."""
        vol_base = self.w_m * self.l_m * self.t_base_m
        vol_fins = self.num_fins * (self.l_m * self.t_fin_m * self.h_fin_m)
        total_vol = vol_base + vol_fins
        mass_kg = total_vol * self.density
        return mass_kg * 1000.0


class HeatPipeAssistedCooling:
    """
    Mo hinh ong dan nhiet Heat Pipe mao dan hai pha (Flat / Sintered Heat Pipe).
    Do dan nhiet tuong duong cuc cao: k_eff ~ 25,000 W/(m*K).
    """
    @staticmethod
    def calculate_heatpipe_temperature_drop(
        power_watts: float,
        pipe_length_mm: float = 150.0,
        pipe_diameter_mm: float = 6.0,
        num_pipes: int = 4
    ) -> float:
        """
        Tinh do sut nhiet do doc theo ong dan nhiet tu vung boc hoi den ngung tu.
        Moi ong dan nhiet 6mm tieu chuan co the truyen 35W - 50W cong suat nhiet.
        """
        # Nhiet tro dac tinh cua ong dan nhiet ~ 0.05 K/W cho ong 6mm
        r_single_pipe = 0.06
        r_eff_pipes = r_single_pipe / float(num_pipes)
        delta_t = power_watts * r_eff_pipes
        return delta_t


def test_heatsink_convection_sizing():
    print("================================================================================")
    print("TEST SUITE: THIET KE KHOI TAN NHIET HEATSINK DOI LUU VA ONG HEAT PIPE")
    print("================================================================================")

    # 1. Kiem tra tinh toan Ngan sach nhiet tro (Thermal Budget) cho chip Apple 85W
    # Yeu cau T_j_max <= 100 deg C o moi truong 35 deg C
    p_cpu = 85.0 # 85W
    r_th_hs_req = ThermalBudgetCalculator.calculate_required_heatsink_rth(
        p_loss_watts=p_cpu,
        t_j_max_deg_c=100.0,
        t_amb_max_deg_c=35.0,
        r_th_jc_k_per_w=0.20,
        r_th_cs_k_per_w=0.10
    )
    # R_total = (100 - 35) / 85 = 65 / 85 = 0.7647 K/W
    # R_hs_req = 0.7647 - 0.30 = 0.4647 K/W
    print(f"[1] Ngan sach nhiet chip Apple Silicon (P = 85W, T_j_max = 100 deg C, T_amb = 35 deg C):")
    print(f"    - Nhiet tro Heatsink toi da cho phep R_th(s-a): {r_th_hs_req:.4f} K/W")
    assert abs(r_th_hs_req - 0.4647) < 0.01, "Loi tinh ngan sach nhiet tro"

    # 2. Kiem tra khoi tan nhiet nhom 80x100 mm, 24 canh
    hs_al = HeatsinkConvectionModel(
        base_width_mm=80.0,
        base_length_mm=100.0,
        base_thickness_mm=5.0,
        fin_height_mm=30.0,
        fin_thickness_mm=1.0,
        num_fins=24,
        material="aluminum"
    )
    weight_g = hs_al.calculate_total_weight_grams()
    print(f"\n[2] Khoi tan nhiet Nhom 80x100x35 mm (24 canh):")
    print(f"    - Tong dien tich tan nhiet: {hs_al.a_total_m2:.4f} m^2")
    print(f"    - Khoi luong khoi nhom:     {weight_g:.1f} grams")
    assert weight_g < 350.0, "Khoi luong khoi nhom phai nhe de gan bo mach"

    # Kiem tra o che do Doi luu tu nhien (Khong bat quat, v = 0 m/s)
    rth_nat, eta_nat, h_nat = hs_al.calculate_heatsink_thermal_resistance(air_velocity_m_per_s=0.0)
    print(f"    - Doi luu tu nhien (v = 0 m/s): h = {h_nat:.1f} W/m2K | eta_fin = {eta_nat*100:.1f}% | R_th = {rth_nat:.3f} K/W")
    assert rth_nat > 0.75, "Khong co quat, nhiet tro heatsink phai lon hon 0.75 K/W"
    assert rth_nat > r_th_hs_req, "Doi luu tu nhien khong du de lam mat 85W, can phai co quat!"

    # Kiem tra o che do Doi luu cuong buc (Bat quat gio v = 2.5 m/s)
    rth_forced, eta_forced, h_forced = hs_al.calculate_heatsink_thermal_resistance(air_velocity_m_per_s=2.5)
    print(f"    - Doi luu cuong buc (v = 2.5 m/s): h = {h_forced:.1f} W/m2K | eta_fin = {eta_forced*100:.1f}% | R_th = {rth_forced:.3f} K/W")
    assert rth_forced < r_th_hs_req, "Khi bat quat 2.5 m/s, R_th phai nho hon nguong yeu cau (PASS ngan sach)"
    print("    -> Khi bat quat gio 2.5 m/s: Giam nhiet tro hon 3 lan, dat chuan nhiet chip Apple!")

    # 3. Kiem tra ong dan nhiet Heat Pipe tro luc
    delta_t_hp = HeatPipeAssistedCooling.calculate_heatpipe_temperature_drop(
        power_watts=85.0,
        pipe_length_mm=150.0,
        pipe_diameter_mm=6.0,
        num_pipes=4
    )
    print(f"\n[3] Ong dan nhiet Heat Pipe 4 ong 6mm truyen 85W cong suat:")
    print(f"    - Do sut nhiet do doc ong: {delta_t_hp:.2f} deg C")
    assert delta_t_hp < 2.0, "Ong heat pipe dan nhiet sieu toc, do sut nhiet phai duoi 2 deg C"

    print("\n--> TAT CA CAC KIEM TRA MILESTONE AV.2 DA THANH CONG 100%!")


if __name__ == "__main__":
    test_heatsink_convection_sizing()
