"""
Chuyen de AV: Mo phong Nhiet - Dien Tich hop & Quan tri Tan nhiet Phan cung
Bai 136 (Milestone AV.1): Mang nhiet tuong duong RC bac thang Foster va Cauer

Author: Le Dac Anh Tuan (18 tuoi) - Electrical Engineering Student
Muc tieu: Lam chu mo hinh tuong duong Nhiet - Dien (Electro-Thermal Analogy), phan biet mang Foster
          (duong cong toan hoc datasheet) va mang Cauer (mang bac thang vat ly thuc te cac lop Silicon/TIM/Heatsink),
          giai he phuong trinh vi phan truyen nhiet qua do cho chip Apple M-Max va module SiC Tesla.

QUY TAC GIANG DAY CONSTRUCTIVIST BOTTOM-UP:
- KHONG dung ky hieu LaTeX hoac cap dau dollar.
- Toan bo bieu thuc toan hoc duoc bieu dien duoi dang khoi ASCII truc quan.
- Chuan hoa ma nguon tuong thich Windows cp1252.
"""

import math
from typing import List, Tuple, Dict


class PhysicalThermalLayer:
    """
    Lop vat lieu truyen nhiet vat ly (Silicon, TIM, Dong IHS, Nhom Heatsink).
    
    Phan tich toan hoc & vat ly nhiet:
    ┌────────────────────────────────────────────────────────┐
    │                                                        │
    │   1. Nhiet tro dan nhiet (Thermal Resistance):         │
    │                    L                                   │
    │      R_th = ──────────────  (don vi K/W)               │
    │                 k * A                                  │
    │                                                        │
    │      L: Do day lop vat lieu (m)                        │
    │      k: Do dan nhiet (W / (m * K))                     │
    │      A: Dien tich tiep xuc (m^2)                       │
    │                                                        │
    │   2. Nhiet dung vat lieu (Thermal Capacitance):        │
    │      C_th = rho * c_p * A * L  (don vi J/K)            │
    │                                                        │
    │      rho: Khoi luong rieng (kg / m^3)                  │
    │      c_p: Nhiet dung rieng (J / (kg * K))              │
    │                                                        │
    │   3. Hang so thoi gian nhiet: tau = R_th * C_th (sec)  │
    │                                                        │
    └────────────────────────────────────────────────────────┘
    """
    def __init__(
        self,
        name: str,
        thickness_mm: float,
        area_mm2: float,
        conductivity_w_per_mk: float,
        density_kg_per_m3: float,
        specific_heat_j_per_kgk: float
    ):
        self.name = name
        self.l_m = float(thickness_mm) * 1e-3
        self.a_m2 = float(area_mm2) * 1e-6
        self.k = float(conductivity_w_per_mk)
        self.rho = float(density_kg_per_m3)
        self.c_p = float(specific_heat_j_per_kgk)

        # Tinh R_th va C_th
        self.r_th = self.l_m / (self.k * self.a_m2)
        volume_m3 = self.a_m2 * self.l_m
        self.c_th = self.rho * self.c_p * volume_m3
        self.tau_sec = self.r_th * self.c_th


class CauerThermalLadderNetwork:
    """
    Mang nhiet bac thang Cauer (Cauer Thermal Ladder).
    Moi nut dai dien cho mot lop vat ly thuc te:
    Node 0: Die Junction (Nguon nhiet P)
    Node 1: TIM1 (Keo kim loai long / Thermal Paste)
    Node 2: Heat Spreader (IHS Dong)
    Node 3: TIM2
    Node 4: Heatsink Base
    
    Phuong trinh can bang nhiet tai nut k:
    C_k * (d T_k / dt) = (T_{k-1} - T_k) / R_{k-1,k} - (T_k - T_{k+1}) / R_{k,k+1}
    """
    def __init__(self, layers: List[PhysicalThermalLayer], ambient_temp_deg_c: float = 25.0):
        if not layers:
            raise ValueError("Danh sach lop vat lieu khong duoc rong")
        self.layers = layers
        self.t_amb = float(ambient_temp_deg_c)
        self.num_nodes = len(layers)
        # Nhiet do khoi tao cac nut bang nhiet do moi truong
        self.node_temperatures = [self.t_amb] * self.num_nodes

    def reset(self):
        """Dat lai nhiet do toan bo he thong ve nhiet do moi truong."""
        self.node_temperatures = [self.t_amb] * self.num_nodes

    def step(self, power_input_watts: float, dt_sec: float) -> List[float]:
        """
        Giai he phuong trinh vi phan truyen nhiet bang tich phan so kem chia nho buoc an toan (Sub-stepping).
        Tra ve danh sach nhiet do tai tat ca cac nut.
        """
        p_in = float(power_input_watts)
        min_tau = min(layer.tau_sec for layer in self.layers)
        max_safe_dt = max(1e-6, min_tau / 5.0)
        n_sub = max(1, int(math.ceil(dt_sec / max_safe_dt)))
        dt_sub = dt_sec / float(n_sub)

        for _ in range(n_sub):
            new_temps = list(self.node_temperatures)
            for i in range(self.num_nodes):
                c_i = max(1e-6, self.layers[i].c_th)

                # Dong nhiet truyen vao nut i tu nut i-1
                if i == 0:
                    q_in = p_in
                else:
                    r_prev = self.layers[i - 1].r_th
                    q_in = (self.node_temperatures[i - 1] - self.node_temperatures[i]) / r_prev

                # Dong nhiet truyen ra tu nut i sang nut i+1
                if i == self.num_nodes - 1:
                    r_out = self.layers[i].r_th
                    q_out = (self.node_temperatures[i] - self.t_amb) / r_out
                else:
                    r_next = self.layers[i].r_th
                    q_out = (self.node_temperatures[i] - self.node_temperatures[i + 1]) / r_next

                # dT_i / dt = (q_in - q_out) / C_i
                dt_temp = (q_in - q_out) / c_i
                new_temps[i] += dt_temp * dt_sub

            self.node_temperatures = new_temps

        return list(self.node_temperatures)


class FosterThermalModel:
    """
    Mo hinh mang nhiet Foster (Foster RC Network) thuong gap tren datasheet linh kien.
    
    Phan tich toan hoc:
    ┌────────────────────────────────────────────────────────┐
    │                                                        │
    │   Tro khang nhiet qua do Z_th(t):                      │
    │                                                        │
    │             M                                          │
    │            ───                     -t / tau_i          │
    │   Z_th(t) = ───  R_i * ( 1.0 - exp(──────────) )       │
    │            i=1                        tau_i            │
    │                                                        │
    │   Nhiet do tiep giap: T_j(t) = T_amb + P * Z_th(t)     │
    │                                                        │
    └────────────────────────────────────────────────────────┘
    """
    def __init__(self, r_list_k_per_w: List[float], tau_list_sec: List[float]):
        if len(r_list_k_per_w) != len(tau_list_sec):
            raise ValueError("Do dai danh sach R va tau phai bang nhau")
        self.r_vals = [float(x) for x in r_list_k_per_w]
        self.tau_vals = [float(x) for x in tau_list_sec]
        self.r_th_total = sum(self.r_vals)

    def calculate_transient_zth(self, t_sec: float) -> float:
        """Tinh tro khang nhiet qua do Z_th tai thoi diem t_sec."""
        if t_sec <= 0.0:
            return 0.0
        z_th = 0.0
        for r_i, tau_i in zip(self.r_vals, self.tau_vals):
            z_th += r_i * (1.0 - math.exp(-t_sec / max(1e-9, tau_i)))
        return z_th

    def junction_temperature(self, power_watts: float, t_sec: float, t_amb_deg_c: float = 25.0) -> float:
        """Tinh nhiet do tiep giap T_j(t) sau khi bom cong suat P trong thoi gian t."""
        return t_amb_deg_c + power_watts * self.calculate_transient_zth(t_sec)


def test_thermal_rc_ladder():
    print("================================================================================")
    print("TEST SUITE: MANG NHIET RC BAC THANG CAUER VA FOSTER CHO CHIP APPLE & TESLA")
    print("================================================================================")

    # 1. Khoi tao cac lop vat ly thuc te cho chip Apple Silicon M-Max:
    # Lop 1: Silicon Die (day 0.3 mm, dien tich 400 mm2 = 20x20 mm, k = 149 W/mK)
    die_silicon = PhysicalThermalLayer(
        name="Silicon_Die",
        thickness_mm=0.3,
        area_mm2=400.0,
        conductivity_w_per_mk=149.0,
        density_kg_per_m3=2330.0,
        specific_heat_j_per_kgk=710.0
    )
    # Lop 2: TIM1 (Liquid Metal / Paste day 0.05 mm, k = 8.5 W/mK)
    tim1 = PhysicalThermalLayer(
        name="TIM1_Interface",
        thickness_mm=0.05,
        area_mm2=400.0,
        conductivity_w_per_mk=8.5,
        density_kg_per_m3=2600.0,
        specific_heat_j_per_kgk=1000.0
    )
    # Lop 3: Copper IHS (day 1.5 mm, dien tich 900 mm2 = 30x30 mm, k = 398 W/mK)
    ihs_copper = PhysicalThermalLayer(
        name="Copper_IHS",
        thickness_mm=1.5,
        area_mm2=900.0,
        conductivity_w_per_mk=398.0,
        density_kg_per_m3=8960.0,
        specific_heat_j_per_kgk=385.0
    )

    print(f"[1] Thong so nhiet vat ly cac lop (Silicon, TIM1, Copper IHS):")
    print(f"    - Silicon Die:  R_th = {die_silicon.r_th:.5f} K/W | C_th = {die_silicon.c_th:.4f} J/K | tau = {die_silicon.tau_sec*1000:.2f} ms")
    print(f"    - TIM1 Paste:   R_th = {tim1.r_th:.5f} K/W | C_th = {tim1.c_th:.4f} J/K | tau = {tim1.tau_sec*1000:.2f} ms")
    print(f"    - Copper IHS:   R_th = {ihs_copper.r_th:.5f} K/W | C_th = {ihs_copper.c_th:.4f} J/K | tau = {ihs_copper.tau_sec*1000:.2f} ms")

    assert die_silicon.r_th < 0.01, "Silicon co do dan nhiet cao, R_th phai rat nho"
    assert tim1.r_th > die_silicon.r_th, "TIM1 co do dan nhiet kem hon Silicon dang ke"

    # 2. Kiem tra mang Foster tu datasheet (vi du module IGBT/SiC Tesla)
    # R_th tong cong = 0.15 K/W gom 3 nhanh thoi gian (nhanh 1 ms, 50 ms, 500 ms)
    foster_model = FosterThermalModel(
        r_list_k_per_w=[0.05, 0.06, 0.04],
        tau_list_sec=[0.005, 0.08, 0.6]
    )
    print(f"\n[2] Mo hinh Foster Datasheet: Tong R_th = {foster_model.r_th_total:.3f} K/W")
    
    # Kiem tra dap ung qua do khi cap cong suat xung 400W trong 10 ms (xung khoi dong xe Tesla)
    p_pulse = 400.0 # 400W
    t_pulse = 0.010 # 10 ms
    tj_pulse = foster_model.junction_temperature(power_watts=p_pulse, t_sec=t_pulse, t_amb_deg_c=25.0)
    zth_10ms = foster_model.calculate_transient_zth(t_pulse)
    print(f"    - Sau xung 400W trong 10 ms: Z_th = {zth_10ms:.4f} K/W | T_j = {tj_pulse:.2f} deg C")
    assert tj_pulse < 50.0, "Xung 10 ms ngan chua kip lam nong ca khoi nhiet"

    # Kiem tra xac lap (Steady-State sau 10 giay):
    tj_steady = foster_model.junction_temperature(power_watts=p_pulse, t_sec=10.0, t_amb_deg_c=25.0)
    expected_steady = 25.0 + p_pulse * foster_model.r_th_total
    print(f"    - Trang thai xac lap (10 sec): T_j = {tj_steady:.2f} deg C (Ky vong = {expected_steady:.2f} deg C)")
    assert abs(tj_steady - expected_steady) < 0.1, "Loi tinh nhiet do xac lap mang Foster"

    # 3. Kiem tra mang bac thang Cauer mo phong dong hoc thoi gian
    cauer_net = CauerThermalLadderNetwork(layers=[die_silicon, tim1, ihs_copper], ambient_temp_deg_c=25.0)
    dt_sim = 0.0005 # 0.5 ms
    num_steps = 2000 # 1 giay

    # Chay mo phong voi cong suat 100W lien tuc
    p_chip = 100.0
    for _ in range(num_steps):
        temps = cauer_net.step(power_input_watts=p_chip, dt_sec=dt_sim)

    tj_cauer = temps[0]
    t_tim1 = temps[1]
    t_ihs = temps[2]

    print(f"\n[3] Mo phong mang Cauer sau 1.0 giay cap 100W:")
    print(f"    - T_junction (Silicon Die): {tj_cauer:.2f} deg C")
    print(f"    - T_tim1:                   {t_tim1:.2f} deg C")
    print(f"    - T_ihs:                    {t_ihs:.2f} deg C")

    # Quy luat vat ly: T_junction > T_tim1 > T_ihs > T_amb
    assert tj_cauer > t_tim1 > t_ihs > 25.0, "Quy luat truyen nhiet don dieu tu trong ra ngoai bi vi pham"
    print("    -> Tuan thu chat che chieu truyen dong nhiet vat ly!")

    print("\n--> TAT CA CAC KIEM TRA MILESTONE AV.1 DA THANH CONG 100%!")


if __name__ == "__main__":
    test_thermal_rc_ladder()
