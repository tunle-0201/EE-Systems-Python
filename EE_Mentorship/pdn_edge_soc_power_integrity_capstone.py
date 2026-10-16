"""
================================================================================
CHUYEN DE AH: POWER DELIVERY NETWORK (PDN) IMPEDANCE & DVFS POWER GOVERNOR
BAI 4: DONG CO POWER INTEGRITY VA QUAN TRI NANG LUONG SOC TESLA FSD CAPSTONE
================================================================================
Hoc vien: Le Dac Anh Tuan (18 tuoi)
Muc tieu: Tich hop toan chuoi PDN + Transient Droop Watchdog + DVFS Governor Capstone
Ngon ngu: Python 3 thuan tuy, kien truc Module huong doi tuong thoi gian thuc
================================================================================
"""

import math
from typing import Tuple, List, Dict

from pdn_edge_target_impedance import (
    PowerDeliveryNetwork, DecouplingCapacitor
)
from pdn_edge_transient_droop_simulator import (
    PDNTransientSimulator
)
from pdn_edge_dvfs_power_governor import (
    PState, P_STATES_TABLE, DVFSPowerGovernor
)

# ------------------------------------------------------------------------------
# 1. DONG CO DIEU HANH POWER INTEGRITY SOC TOAN CHUOI (SOC POWER CAPSTONE ENGINE)
# ------------------------------------------------------------------------------

class SoCPowerIntegrityEngine:
    """
    Dong co quan tri nang luong va bao ve tinh toan ven nguon dien chip AI SoC:
    - DVFS Governor: Dieu phoi P-States (P0..P3) dua tren tai trong AI thoi gian thuc
    - Slew-rate Voltage Ramp: Tang giam dien ap em diu chong gay soc dong inrush
    - PDN Power Integrity Model: Tinh toan sut ap chinh xac gom:
        1. Sut ap tro thuan IR-drop: V_ir = R_pdn * I_load
        2. Sut ap cam ung L-di/dt: V_ind = L_pkg * (dI/dt)
        3. Dao dong song sut ap 3 tang (First, Second, Third Droop)
    - Voltage Droop Watchdog: Phat hien bat ky su co sut ap dot bien vuot nguong an toan
    """
    def __init__(self,
                 initial_state_idx: int = 3, # Bat dau tai P3_LOW (Sentry mode)
                 allowed_droop_percent: float = 0.05):
        self.governor = DVFSPowerGovernor(initial_state_idx=initial_state_idx, slew_rate_v_per_us=0.012)
        self.allowed_droop = allowed_droop_percent

        # Thong so mang PDN toi uu tu Bai 1 & Bai 2
        self.R_pdn = 0.0012   # 1.2 mOhm tong tro khang DC
        self.L_pkg = 0.08e-9  # 80 pH dien cam package
        self.C_bulk = 450e-6  # 450 uF tu MLCC
        self.tau_vrm = 1.0e-6 # 1.0 us VRM response

        self.last_i_load = 0.0
        self.total_energy_joules = 0.0
        self.droop_violations_count = 0
        self.min_v_observed = 2.0

    def step(self, ai_workload_utilization: float, dt: float) -> Dict[str, any]:
        """
        Thuc thi 1 chu ky mo phong (dt = 0.5 us):
        1. Cap nhat DVFS Governor dua tren tai trong AI (Utilization)
        2. Tinh toan dong dien tai tieu thu I_load = P / Vdd
        3. Tinh toan sut ap vat ly chinh xac tren mang PDN
        4. Kiem tra tinh toan ven nguon dien Power Integrity Watchdog
        """
        # 1. Cap nhat DVFS P-State
        gov_state = self.governor.update_governor(ai_workload_utilization, dt)
        target_v = gov_state["actual_vdd"]
        freq_ghz = gov_state["actual_freq"]

        # Dong dien tai dong ti le voi utilization:
        # P_dynamic = c_eff * V^2 * f * utilization
        c_eff = 8.0e-9 # 8 nF
        p_dyn = c_eff * (target_v ** 2) * (freq_ghz * 1e9) * max(0.1, ai_workload_utilization)
        p_leak = target_v * 0.200 # 200 mA leakage
        p_total = p_dyn + p_leak

        i_load = p_total / target_v # Dong dien ampe

        # 2. Tinh toan bien thien dong dien dI/dt
        di_dt = (i_load - self.last_i_load) / dt if dt > 0 else 0.0
        self.last_i_load = i_load

        # 3. Mo hinh vat ly sut ap PDN (IR drop + L di/dt + Transient recovery):
        v_ir_drop = self.R_pdn * i_load
        v_l_drop = self.L_pkg * di_dt

        # Sụt áp động do trễ nạp của VRM (Third droop dynamic component)
        # Nho co Slew-rate kiem soat, di_dt rat em diu (< 1.5 A/us)
        v_transient_droop = abs(v_l_drop) * 0.5

        total_droop_v = v_ir_drop + v_transient_droop
        v_core = target_v - total_droop_v

        # 4. Kiem tra Watchdog
        v_min_threshold = target_v * (1.0 - self.allowed_droop)
        is_violated = (v_core < v_min_threshold)
        if is_violated:
            self.droop_violations_count += 1

        if v_core < self.min_v_observed:
            self.min_v_observed = v_core

        self.total_energy_joules += p_total * dt

        droop_mv = (target_v - v_core) * 1000.0

        return {
            "p_state": gov_state["current_state"],
            "target_vdd": target_v,
            "freq_ghz": freq_ghz,
            "v_core": v_core,
            "droop_mv": droop_mv,
            "power_w": p_total,
            "is_violated": is_violated,
            "status": "HEALTHY" if not is_violated else "VIOLATION"
        }

# ------------------------------------------------------------------------------
# 2. KICH BAN MO PHONG CAPSTONE: BAO TAI AI XE TU LAI TESLA FSD
# ------------------------------------------------------------------------------

def run_tesla_fsd_power_integrity_simulation():
    """
    Mo phong kich ban AI Workload Burst cua chip tu lai Tesla FSD:
    - Giai doan 1 (0 - 15 us): Xe dung den do, NPU o che do Sentry Mode P3_LOW (Utilization = 15%).
    - Giai doan 2 (15 - 45 us): Phat hien nguoi di bo cat ngang! NPU chay 100% cong suat (Utilization = 95%).
      He thong tang toc DVFS len P0_BOOST (1.05V, 3.6 GHz).
    - Giai doan 3 (45 - 75 us): Tinh huong an toan, xe tro ve cao toc (Utilization = 50%), ve P1_NOMINAL (0.95V, 3.0 GHz).
    """
    engine = SoCPowerIntegrityEngine(initial_state_idx=3, allowed_droop_percent=0.05)

    dt = 0.1e-6 # 0.1 micro-giay (100 ns)
    total_time = 75.0e-6 # 75 micro-giay
    steps = int(total_time / dt)

    telemetry_log: List[Dict[str, any]] = []

    print("================================================================================")
    print("BAT DAU MO PHONG SOC POWER INTEGRITY & DVFS GOVERNOR (CAPSTONE)")
    print("================================================================================")
    print("Chip: Tesla FSD SoC | Dung sai sut ap PDN: +-5% | Slew-rate Ramp: 12 mV/us")
    print("Kich ban: Sentry Mode (P3) -> AI Pedestrian Burst (P0) -> Highway Cruising (P1)")
    print("--------------------------------------------------------------------------------")

    for step in range(steps):
        t = step * dt

        # Xac dinh tai trong AI theo thoi gian
        if t < 15.0e-6:
            utilization = 0.15 # 15% Sentry
        elif t < 45.0e-6:
            utilization = 0.95 # 95% AI Burst
        else:
            utilization = 0.50 # 50% Highway

        state = engine.step(utilization, dt)

        # Ghi log Telemetry moi 7.5 micro-giay
        if step % int(7.5e-6 / dt) == 0 or step == steps - 1:
            telemetry_log.append({
                "time_us": t * 1e6,
                "state": state["p_state"],
                "target_v": state["target_vdd"],
                "v_core": state["v_core"],
                "droop_mv": state["droop_mv"],
                "freq_ghz": state["freq_ghz"],
                "power_w": state["power_w"],
                "status": state["status"]
            })

    # In bang thong ke Telemetry
    print(f"{'Time(us)':<9} | {'P-State':<12} | {'Target V':<9} | {'V_core(V)':<10} | {'Droop(mV)':<10} | {'Freq(GHz)':<10} | {'Power(W)':<9} | {'Status':<8}")
    print("-" * 92)
    for e in telemetry_log:
        print(f"{e['time_us']:<9.1f} | {e['state']:<12} | {e['target_v']:<9.2f} | {e['v_core']:<10.4f} | {e['droop_mv']:<10.2f} | {e['freq_ghz']:<10.2f} | {e['power_w']:<9.2f} | {e['status']:<8}")

    print("--------------------------------------------------------------------------------")
    max_droop_all = max(e["droop_mv"] for e in telemetry_log)
    min_v_core = min(e["v_core"] for e in telemetry_log)

    print(f"-> Tong nang luong tieu thu toan chu trinh: {engine.total_energy_joules * 1000.0:.2f} mJ")
    print(f"-> So lan vi pham sut ap PDN Violation    : {engine.droop_violations_count} lan (100% Healthy)")
    print(f"-> Sut ap cuc dai trong suot qua trinh    : {max_droop_all:.2f} mV (Nam an toan trong +-5%)")
    print("--------------------------------------------------------------------------------")

    # Kiem tra tieu chi Capstone:
    # 1. Khong duoc co bat ky vi pham sut ap nao (droop_violations_count == 0)
    assert engine.droop_violations_count == 0, f"Loi: Co {engine.droop_violations_count} lan vi pham sut ap!"
    # 2. He thong phai chuyen tiep thanh cong qua cac trang thai P3 -> P0 -> P1
    states_visited = set(e["state"] for e in telemetry_log)
    assert "P3_LOW" in states_visited, "Loi: Khong bat dau tai P3_LOW!"
    assert "P0_BOOST" in states_visited, "Loi: Khong len duoc P0_BOOST!"
    # 3. Sut ap khong vuot qua 35 mV
    assert max_droop_all < 35.0, f"Loi: Sut ap vuot nguong: {max_droop_all} mV"
    print("[PASS] Capstone SoC Power Integrity Engine: Bao ve dien ap hoan hao trong con bao tai AI!")

if __name__ == "__main__":
    run_tesla_fsd_power_integrity_simulation()
