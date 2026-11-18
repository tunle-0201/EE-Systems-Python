"""
================================================================================
CHUYEN DE AH: POWER DELIVERY NETWORK (PDN) IMPEDANCE & DVFS POWER GOVERNOR
BAI 3: BO DIEU PHOI NANG LUONG DVFS P-STATES VA SLEW-RATE CONTROLLED RAMP CHO SOC
================================================================================
Hoc vien: Le Dac Anh Tuan (18 tuoi)
Muc tieu: Tiet kiem 70% nang luong pin cho chip Apple M-Series va Tesla FSD
Ngon ngu: Python 3 thuan tuy, may trang thai dieu phoi P-States & Voltage-First Rule
================================================================================
"""

import math
from typing import Tuple, List, Dict

# ------------------------------------------------------------------------------
# 1. BANG TRANG THAI HIEU NANG P-STATES (VOLTAGE - FREQUENCY OPERATING POINTS)
# ------------------------------------------------------------------------------

class PState:
    """
    Diem lam viec hieu nang P-State:
    - name: Ten trang thai (P0, P1, P2, P3)
    - vdd: Dien ap cap cho loi silicon (Volt)
    - freq_ghz: Tan so xung nhip CPU/NPU (GHz)
    """
    def __init__(self, name: str, vdd: float, freq_ghz: float):
        self.name = name
        self.vdd = vdd
        self.freq_ghz = freq_ghz

    def compute_power(self, c_eff_nf: float = 8.0, leakage_ma: float = 200.0) -> float:
        """
        Tinh cong suat tieu thu P = C_eff * Vdd^2 * f + Vdd * I_leakage (Watt):
        - c_eff_nf: Dien dung dong ky sinh hieu dung (nF)
        - leakage_ma: Dong ro ban dan tinh (mA)
        """
        f_hz = self.freq_ghz * 1e9
        c_f = c_eff_nf * 1e-9
        p_dynamic = c_f * (self.vdd ** 2) * f_hz
        p_leakage = self.vdd * (leakage_ma * 1e-3)
        return p_dynamic + p_leakage

# Bang 4 cap P-States chuan tren SoC AI
P_STATES_TABLE = [
    PState("P0_BOOST",   vdd=1.05, freq_ghz=3.6), # Chay suy luan AI nang cap bach
    PState("P1_NOMINAL", vdd=0.95, freq_ghz=3.0), # Chay camera & he thong lai xe
    PState("P2_MEDIUM",  vdd=0.85, freq_ghz=2.2), # Chay dieu huong ban do
    PState("P3_LOW",     vdd=0.75, freq_ghz=1.4), # Che do cho tiet kiem pin Sentry Mode
]

# ------------------------------------------------------------------------------
# 2. BO DIEU PHOI DVFS THICH UNG TAI TRONG (LOAD-ADAPTIVE DVFS GOVERNOR)
# ------------------------------------------------------------------------------

class DVFSPowerGovernor:
    """
    Bo quan tri nang luong DVFS tich hop quy tac an toan phan cung:
    1. Voltage-First Rule khi Scale Up: Tang Vdd truoc -> Doi Slew-rate on dinh -> Tang Frequency.
    2. Frequency-First Rule khi Scale Down: Ha Frequency truoc -> Ha Vdd sau.
    3. Slew-Rate Controlled Voltage Ramp: Gioi han toc do tang/giam dien ap (dV/dt)
       de chong soc dong inrush vao mang tu PDN: I_inrush = C_pdn * (dV/dt).
    """
    def __init__(self,
                 p_states: List[PState] = P_STATES_TABLE,
                 initial_state_idx: int = 1,     # Mac dinh bat dau tai P1
                 slew_rate_v_per_us: float = 0.010): # 10 mV / micro-giay
        self.p_states = p_states
        self.current_idx = initial_state_idx
        self.target_idx = initial_state_idx

        # Dien ap va tan so thuc te tuc thoi
        self.actual_vdd = p_states[initial_state_idx].vdd
        self.actual_freq = p_states[initial_state_idx].freq_ghz

        self.slew_rate = slew_rate_v_per_us * 1e6 # V / giay
        self.is_transitioning = False

    def update_governor(self, core_utilization: float, dt: float) -> Dict[str, any]:
        """
        Kiem tra tai trong loi (Utilization: 0.0 den 1.0) va cap nhat P-State:
        - Neu Utilization > 0.80 -> Scale Up (Tang hieu nang)
        - Neu Utilization < 0.30 -> Scale Down (Tiet kiem pin)
        """
        # 1. Danh gia tai trong neu khong dang trong qua trinh chuyen doi
        if not self.is_transitioning:
            if core_utilization > 0.80 and self.current_idx > 0:
                self.target_idx = self.current_idx - 1 # Tang toc (P1 -> P0)
                self.is_transitioning = True
            elif core_utilization < 0.30 and self.current_idx < len(self.p_states) - 1:
                self.target_idx = self.current_idx + 1 # Giam toc (P1 -> P2 -> P3)
                self.is_transitioning = True

        target_state = self.p_states[self.target_idx]

        # 2. May trang thai chuyen doi (Transition State Machine)
        if self.is_transitioning:
            # Truong hop A: SCALE UP (Can tang dien ap va tang tan so)
            if self.target_idx < self.current_idx:
                # QUY TAC 1: TANG DIEN AP TRUOC
                if self.actual_vdd < target_state.vdd:
                    # Ramp dien ap theo Slew-rate
                    self.actual_vdd = min(target_state.vdd, self.actual_vdd + self.slew_rate * dt)
                else:
                    # Dien ap da dat muc an toan -> BAY GIO MOI DUOC TANG TAN SO
                    self.actual_freq = target_state.freq_ghz
                    self.current_idx = self.target_idx
                    self.is_transitioning = False

            # Truong hop B: SCALE DOWN (Can giam dien ap va giam tan so)
            else:
                # QUY TAC 2: GIAM TAN SO TRUOC
                if self.actual_freq > target_state.freq_ghz:
                    self.actual_freq = target_state.freq_ghz
                # Sau khi tan so da ha, giam dien ap theo Slew-rate
                if self.actual_vdd > target_state.vdd:
                    self.actual_vdd = max(target_state.vdd, self.actual_vdd - self.slew_rate * dt)
                else:
                    self.current_idx = self.target_idx
                    self.is_transitioning = False

        # Tinh toan cong suat tuc thoi
        p_now = (8e-9 * (self.actual_vdd ** 2) * (self.actual_freq * 1e9)) + (self.actual_vdd * 0.200)

        return {
            "current_state": self.p_states[self.current_idx].name,
            "target_state": self.p_states[self.target_idx].name,
            "actual_vdd": self.actual_vdd,
            "actual_freq": self.actual_freq,
            "power_w": p_now,
            "is_transitioning": self.is_transitioning
        }

# ------------------------------------------------------------------------------
# 3. MO PHONG VA KIEM CHUNG TIET KIEM NANG LUONG DVFS
# ------------------------------------------------------------------------------

def test_dvfs_power_reduction():
    """
    Kiem tra 1: Do giam cong suat giua P0_BOOST va P3_LOW:
    So sanh cong suat tieu thu tren chip.
    """
    p0 = P_STATES_TABLE[0] # 1.05V, 3.6 GHz
    p3 = P_STATES_TABLE[3] # 0.75V, 1.4 GHz

    pow_p0 = p0.compute_power(c_eff_nf=8.0, leakage_ma=200.0)
    pow_p3 = p3.compute_power(c_eff_nf=8.0, leakage_ma=200.0)

    reduction_percent = ((pow_p0 - pow_p3) / pow_p0) * 100.0

    print("--------------------------------------------------------------------------------")
    print("SO SANH CONG SUAT TIEU THU DVFS (APPLE M-SERIES / TESLA FSD NPU):")
    print(f"-> P0_BOOST (Max Compute) : {p0.vdd:.2f} V | {p0.freq_ghz:.1f} GHz | Power = {pow_p0:6.2f} W")
    print(f"-> P3_LOW   (Sentry Mode) : {p3.vdd:.2f} V | {p3.freq_ghz:.1f} GHz | Power = {pow_p3:6.2f} W")
    print(f"-> Ty le tiet kiem nang luong: -{reduction_percent:.2f}% (Giam hon 70% nhiet luong!)")
    print("--------------------------------------------------------------------------------")

    # Kiem tra tieu chi:
    # Che do P3 phai tiet kiem duoc tren 70% cong suat so voi P0
    assert reduction_percent > 70.0, f"Loi: Ty le tiet kiem khong dat: {reduction_percent:.2f}%"
    print("[PASS] Test 1: Cong thuc DVFS giam hon 70% cong suat thanh cong!")

def test_dvfs_governor_transitions():
    """
    Kiem tra 2: Chuyen doi P-States tuan tu va quy tac Voltage-First:
    - Bat dau o P1 (0.95V, 3.0 GHz)
    - Dua tai len 95% -> Kich hoat Scale Up len P0 (1.05V, 3.6 GHz)
    - Kiem tra: Dien ap phai dat 1.05V truoc khi tan so duoc phep nhay len 3.6 GHz!
    """
    gov = DVFSPowerGovernor(initial_state_idx=1, slew_rate_v_per_us=0.010) # 10 mV/us
    dt = 1e-6 # 1 micro-giay moi buoc

    print("Bat dau mo phong chuyen doi tai trong AI: Utilization = 95% (Scale Up)...")

    freq_increased_before_voltage = False

    # Chay 25 micro-giay
    for step in range(25):
        state = gov.update_governor(core_utilization=0.95, dt=dt)

        # Kiem tra vi pham Voltage-First Rule:
        if state["actual_freq"] > 3.0 and state["actual_vdd"] < 1.049:
            freq_increased_before_voltage = True

    # Sau 25 us dien ap tang 100 mV (tu 0.95V len 1.05V mat 10 us theo Slew-rate 10 mV/us)
    assert not freq_increased_before_voltage, "Loi: Vi pham Voltage-First Rule (Tan so tang truoc dien ap)!"
    assert gov.current_idx == 0, f"Loi: Phai dat P0_BOOST, hien tai: {gov.p_states[gov.current_idx].name}"
    assert abs(gov.actual_vdd - 1.05) < 1e-4, f"Loi dien ap cuoi: {gov.actual_vdd}"
    assert abs(gov.actual_freq - 3.6) < 1e-4, f"Loi tan so cuoi: {gov.actual_freq}"

    print(f"[PASS] Test 2: Voltage-First Rule tuan thu 100%, chuyen doi len P0_BOOST an toan tuyet doi!")

if __name__ == "__main__":
    print("================================================================================")
    print("DEMO DVFS P-STATES POWER GOVERNOR (APPLE SILICON / TESLA FSD NPU)")
    print("================================================================================")
    test_dvfs_power_reduction()
    test_dvfs_governor_transitions()
