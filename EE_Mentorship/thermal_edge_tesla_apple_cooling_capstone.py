"""
Chuyen de AV: Mo phong Nhiet - Dien Tich hop & Quan tri Tan nhiet Phan cung
Bai 139 (Milestone AV.4 - Capstone Project): Dong co mo phong Nhiet - Dien toan dien cho
                                             Bien tan SiC 800V Tesla Cybertruck & Apple Silicon Capstone

Author: Le Dac Anh Tuan (18 tuoi) - Electrical Engineering Student
Muc tieu: Xay dung dong co mo phong nhiet - dien ghep noi (Coupled Electro-Thermal Engine),
          tinh toan ton hao dan dong va chuyen mach SiC phu thuoc nhiet do R_ds(on)(T_j),
          mo phong mang Cauer da tang (Die, Moi han Solder, Substrate AlN, Baseplate, Cold-Plate),
          du doan tuoi tho moi han theo mo hinh moi nhiet Coffin-Manson va dieu phoi bom lam mat chat long.

QUY TAC GIANG DAY CONSTRUCTIVIST BOTTOM-UP:
- KHONG dung ky hieu LaTeX hoac cap dau dollar.
- Toan bo bieu thuc toan hoc duoc bieu dien duoi dang khoi ASCII truc quan.
- Chuan hoa ma nguon tuong thich Windows cp1252.
"""

import math
from typing import List, Tuple, Dict, Optional


class SiCElectroThermalLossModel:
    """
    Mo hinh ton hao dien - nhiet ghep noi cua module SiC MOSFET 800V gom cac van mac song song.
    
    Phan tich toan hoc & vat ly ban dan:
    ┌────────────────────────────────────────────────────────┐
    │                                                        │
    │   1. Module cong suat 300kW gom 4 van song song:       │
    │      Dong dien moi van: I_die = I_phase / N_parallel   │
    │                                                        │
    │   2. Dien tro mo kenh R_ds(on) tang theo nhiet do:     │
    │      R_ds(T_j) = R_ds_25 * ( 1.0 + alpha_T * (T_j - 25) )│
    │                                                        │
    │   3. Ton hao dan dong module (Conduction Loss):        │
    │      P_cond = N_par * I_die^2 * R_ds(T_j)              │
    │                                                        │
    │   4. Ton hao chuyen mach module (Switching Loss):      │
    │                     V_dc      I_phase                  │
    │      P_sw = E_sw * ─────── * ───────── * f_sw          │
    │                    V_test     I_test                   │
    │                                                        │
    │   5. Tong cong suat nhiet sinh ra:                     │
    │      P_loss(t) = P_cond(t) + P_sw(t)                   │
    │                                                        │
    └────────────────────────────────────────────────────────┘
    """
    def __init__(
        self,
        r_ds_on_25c_ohm: float = 0.006,    # 6 mOhm moi die (module 4 van dat 1.5 mOhm)
        alpha_t: float = 0.006,             # He so tang nhiet 0.6% / deg C
        e_sw_test_joules: float = 0.004,    # 4 mJ tai 800V, 300A
        v_test_volts: float = 800.0,
        i_test_amps: float = 300.0,
        f_sw_hz: float = 20000.0,           # 20 kHz tan so PWM SiC o to
        num_parallel_dies: int = 4          # 4 chip song song trong module
    ):
        self.r_ds_25 = float(r_ds_on_25c_ohm)
        self.alpha_t = float(alpha_t)
        self.e_sw_test = float(e_sw_test_joules)
        self.v_test = float(v_test_volts)
        self.i_test = float(i_test_amps)
        self.f_sw = float(f_sw_hz)
        self.n_par = int(num_parallel_dies)

    def calculate_losses_watts(
        self,
        i_load_amps: float,
        v_dc_volts: float,
        t_junction_deg_c: float
    ) -> Tuple[float, float, float]:
        """
        Tinh ton hao dan dong P_cond, ton hao chuyen mach P_sw va tong cong suat nhiet P_total.
        Tra ve (p_total, p_cond, p_sw).
        """
        i_die = abs(i_load_amps) / float(self.n_par)
        # Dien tro kenh phu thuoc nhiet do tiep giap
        r_ds_act = self.r_ds_25 * (1.0 + self.alpha_t * max(0.0, t_junction_deg_c - 25.0))
        p_cond = self.n_par * (i_die ** 2) * r_ds_act

        # Ton hao chuyen mach ty le voi ap va dong
        scaling = (v_dc_volts / self.v_test) * (abs(i_load_amps) / self.i_test)
        p_sw = self.e_sw_test * scaling * self.f_sw

        p_total = p_cond + p_sw
        return p_total, p_cond, p_sw


class CoffinMansonThermalFatigueModel:
    """
    Mo hinh moi nhiet Coffin-Manson du doan so chu ky hoat dong den khi nut moi han (Solder Fatigue).
    
    Phan tich toan hoc do tin cay:
    ┌────────────────────────────────────────────────────────┐
    │                                                        │
    │   So chu ky toi han (Cycles to Failure):               │
    │                                                        │
    │                            -q                          │
    │      N_f = A * ( Delta_T_j )                           │
    │                                                        │
    │      Delta_T_j = T_j_peak - T_j_min                    │
    │      q ~ 4.0 - 5.0 (So mu moi vat lieu han SAC305)     │
    │                                                        │
    │   Quy luat: Bien do dao dong nhiet tang gap doi        │
    │             => Tuoi tho giam 2^4 = 16 lan!             │
    │                                                        │
    └────────────────────────────────────────────────────────┘
    """
    @staticmethod
    def calculate_cycles_to_failure(delta_t_j_deg_c: float, q_exponent: float = 4.2) -> float:
        if delta_t_j_deg_c <= 1.0:
            return 1e9  # Tuoi tho vo han
        # Hang so chuan hoa: Delta_T = 50 deg C dat 1,000,000 chu ky
        # N_f = 1e6 * (50 / Delta_T)^q
        ratio = 50.0 / delta_t_j_deg_c
        return 1.0e6 * (ratio ** q_exponent)


class LiquidColdPlateCoolingSystem:
    """
    He thong lam mat bang tam nhom luu chat long (Cold-Plate Water-Glycol 50/50).
    Luu luong bom dieu khien linh hoat: 2.0 den 15.0 Lit/phut (LPM).
    """
    def __init__(self, t_coolant_inlet_deg_c: float = 40.0):
        self.t_inlet = float(t_coolant_inlet_deg_c)
        self.flow_rate_lpm = 4.0 # 4 LPM mac dinh

    def calculate_coldplate_rth(self, flow_lpm: float) -> float:
        """
        Nhiet tro giua tam lam mat va chat long giam theo ham luy thua cua luu luong.
        R_th(cp-fluid) = 0.08 * (4.0 / flow_lpm)^0.7
        """
        flow = max(1.0, float(flow_lpm))
        return 0.08 * ((4.0 / flow) ** 0.7)


class TeslaAppleElectroThermalSimulator:
    """
    Dong co mo phong nhiet - dien ghep noi toan dien 5 lop Cauer:
    Node 0: SiC Junction
    Node 1: Die Attach Solder (Moi han nanosilver / SAC305)
    Node 2: AlN Substrate (Gom cach dien dan nhiet)
    Node 3: Cu Baseplate (De dong)
    Node 4: Cold-Plate (Tam nuoc lam mat)
    """
    def __init__(self):
        self.loss_model = SiCElectroThermalLossModel()
        self.cooling = LiquidColdPlateCoolingSystem(t_coolant_inlet_deg_c=40.0)
        
        # Nhiet dung tung lop module SiC (J/K)
        # 4 Die SiC (1.2 J/K), Moi han solder (0.4 J/K), Gom AlN (4.0 J/K), De dong Cu (35.0 J/K), Cold-Plate (100.0 J/K)
        self.c_nodes = [1.2, 0.4, 4.0, 35.0, 100.0]
        # Nhiet tro giua cac lop (K/W)
        self.r_nodes = [0.018, 0.010, 0.022, 0.015] # R_01, R_12, R_23, R_34
        
        self.temps = [40.0] * 5

    def reset(self, initial_temp: float = 40.0):
        self.temps = [float(initial_temp)] * 5

    def step(self, i_load_amps: float, v_dc_volts: float, flow_lpm: float, dt_sec: float) -> Dict[str, any]:
        t_j = self.temps[0]
        p_total, p_cond, p_sw = self.loss_model.calculate_losses_watts(i_load_amps, v_dc_volts, t_j)

        r_fluid = self.cooling.calculate_coldplate_rth(flow_lpm)
        t_coolant = self.cooling.t_inlet

        # Chia nho sub-step de on dinh so (dt_sub <= 0.2 ms)
        n_sub = max(1, int(math.ceil(dt_sec / 0.0002)))
        dt_sub = dt_sec / float(n_sub)

        for _ in range(n_sub):
            # Tinh lai ton hao voi nhiet do tiep giap tuc thoi
            t_j_now = self.temps[0]
            p_tot_now, p_cond, p_sw = self.loss_model.calculate_losses_watts(i_load_amps, v_dc_volts, t_j_now)

            # Tich phan vi phan nhiet do 5 nut
            q01 = (self.temps[0] - self.temps[1]) / self.r_nodes[0]
            dt0 = (p_tot_now - q01) / self.c_nodes[0]

            q12 = (self.temps[1] - self.temps[2]) / self.r_nodes[1]
            dt1 = (q01 - q12) / self.c_nodes[1]

            q23 = (self.temps[2] - self.temps[3]) / self.r_nodes[2]
            dt2 = (q12 - q23) / self.c_nodes[2]

            q34 = (self.temps[3] - self.temps[4]) / self.r_nodes[3]
            dt3 = (q23 - q34) / self.c_nodes[3]

            q_out = (self.temps[4] - t_coolant) / r_fluid
            dt4 = (q34 - q_out) / self.c_nodes[4]

            self.temps[0] += dt0 * dt_sub
            self.temps[1] += dt1 * dt_sub
            self.temps[2] += dt2 * dt_sub
            self.temps[3] += dt3 * dt_sub
            self.temps[4] += dt4 * dt_sub

        return {
            "t_junction": self.temps[0],
            "t_solder": self.temps[1],
            "t_substrate": self.temps[2],
            "t_baseplate": self.temps[3],
            "t_coldplate": self.temps[4],
            "p_total_loss_watts": p_total,
            "p_cond_watts": p_cond,
            "p_sw_watts": p_sw,
            "r_fluid_k_per_w": r_fluid
        }


def test_tesla_apple_cooling_capstone():
    print("================================================================================")
    print("TEST SUITE CAPSTONE: MO PHONG NHIET - DIEN BIEN TAN SiC 800V TESLA & APPLE SoC")
    print("================================================================================")

    sim = TeslaAppleElectroThermalSimulator()
    sim.reset(initial_temp=40.0)

    # 1. Kiem tra tinh toan ton hao dien - nhiet SiC phu thuoc T_j
    # So sanh ton hao khi T_j = 25 deg C vs T_j = 125 deg C
    loss_model = sim.loss_model
    p_tot_25, p_c_25, p_s_25 = loss_model.calculate_losses_watts(i_load_amps=200.0, v_dc_volts=800.0, t_junction_deg_c=25.0)
    p_tot_125, p_c_125, p_s_125 = loss_model.calculate_losses_watts(i_load_amps=200.0, v_dc_volts=800.0, t_junction_deg_c=125.0)

    print(f"[1] Kiem tra ton hao dien - nhiet SiC MOSFET 800V (I = 200A, V_dc = 800V):")
    print(f"    - Tai T_j =  25 deg C: R_ds = {loss_model.r_ds_25*1000:.2f} mOhm | P_cond = {p_c_25:.1f}W | P_sw = {p_s_25:.1f}W | Tong = {p_tot_25:.1f}W")
    print(f"    - Tai T_j = 125 deg C: P_cond = {p_c_125:.1f}W | P_sw = {p_s_125:.1f}W | Tong = {p_tot_125:.1f}W")
    
    # Do R_ds tang 70% o 125 deg C, P_cond phai tang 70%!
    assert p_c_125 > 1.5 * p_c_25, "Ton hao dan dong phai tang theo nhiet do T_j"
    print("    -> Hien tuong nhiet tro duong lam tang ton hao duoc mo phong chinh xac!")

    # 2. Mo phong kich ban Tesla Cybertruck tang toc Ludicrous Launch (0-100 km/h)
    # Giai doan 1 (0-3s): Dong cuc dai 600A tang toc, bom nuoc chay toi da 12 LPM
    # Giai doan 2 (3-10s): Dong chay deu cao toc 150A, bom nuoc giam ve 5 LPM
    print(f"\n[2] Mo phong hanh trinh Tesla Cybertruck Ludicrous Acceleration (600A trong 3s):")
    
    dt = 0.05 # 50 ms
    t_history = []
    tj_history = []
    
    # 3 giay tang toc 600A
    for step_idx in range(60):
        res = sim.step(i_load_amps=600.0, v_dc_volts=800.0, flow_lpm=12.0, dt_sec=dt)
        t_history.append((step_idx + 1) * dt)
        tj_history.append(res["t_junction"])

    tj_peak = max(tj_history)
    print(f"    - Dinh nhiet do tiep giap T_j sau 3 giay tang toc: {tj_peak:.1f} deg C")
    assert tj_peak < 165.0, "Nhiet do SiC phai duoi nguong pha huy 175 deg C"
    assert tj_peak > 100.0, "Xung 600A phai lam nong tiep giap ro ret"

    # 7 giay tiep theo giam ve 150A de lam mat
    for step_idx in range(140):
        res = sim.step(i_load_amps=150.0, v_dc_volts=800.0, flow_lpm=5.0, dt_sec=dt)
        t_history.append(3.0 + (step_idx + 1) * dt)
        tj_history.append(res["t_junction"])

    tj_cooldown = tj_history[-1]
    print(f"    - Nhiet do tiep giap T_j sau khi lam nguoi (10s):   {tj_cooldown:.1f} deg C")
    assert tj_cooldown < tj_peak - 25.0, "He thong lam mat phai giam nhiet thanh cong"

    # 3. Kiem tra du doan moi nhiet moi han Coffin-Manson
    delta_tj = tj_peak - 40.0 # Bien do dao dong nhiet
    cycles_life = CoffinMansonThermalFatigueModel.calculate_cycles_to_failure(delta_t_j_deg_c=delta_tj, q_exponent=4.2)
    print(f"\n[3] Du doan tuoi tho moi han Solder Fatigue Coffin-Manson:")
    print(f"    - Dao dong nhiet Delta_T_j = {delta_tj:.1f} deg C")
    print(f"    - So chu ky toi han uoc tinh (N_f): {cycles_life:,.0f} chu ky dap ga")
    assert cycles_life > 10000.0, "Moi han phai chiu duoc it nhat 10,000 chu ky tang toc nang"

    # 4. Kiem tra phan bo nhiet do 5 tang Cauer tai thoi diem dinh
    print(f"\n[4] Phan bo nhiet do 5 tang Cauer tai cuoi chu trinh:")
    print(f"    - Die SiC:     {res['t_junction']:.1f} deg C")
    print(f"    - Moi han:     {res['t_solder']:.1f} deg C")
    print(f"    - Gom AlN:     {res['t_substrate']:.1f} deg C")
    print(f"    - De dong:     {res['t_baseplate']:.1f} deg C")
    print(f"    - Cold-Plate:  {res['t_coldplate']:.1f} deg C")
    assert res['t_junction'] >= res['t_solder'] >= res['t_substrate'] >= res['t_baseplate'] >= res['t_coldplate']
    print("    -> Quy luat gradient truyen nhiet don dieu 5 tang tuan thu 100% vat ly!")

    print("\n--> TAT CA CAC KIEM TRA MILESTONE AV.4 CAPSTONE DA THANH CONG 100%!")


if __name__ == "__main__":
    test_tesla_apple_cooling_capstone()
