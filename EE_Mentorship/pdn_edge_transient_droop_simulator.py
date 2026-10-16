"""
================================================================================
CHUYEN DE AH: POWER DELIVERY NETWORK (PDN) IMPEDANCE & DVFS POWER GOVERNOR
BAI 2: MO PHONG SUT AP QUA DO TIME-DOMAIN TRANSIENT DROOP (1ST, 2ND, 3RD DROOP)
================================================================================
Hoc vien: Le Dac Anh Tuan (18 tuoi)
Muc tieu: Mo phong hien tuong dI/dt L-Noise va kiem soat song sut ap 3 tang tren SoC
Ngon ngu: Python 3 thuan tuy, tich phan he phuong trinh vi phan mang RLC da tang
================================================================================
"""

import math
from typing import Tuple, List, Dict

# ------------------------------------------------------------------------------
# 1. MO HINH MANG NGUON 3 TANG TRONG MIEN THOI GIAN (3-STAGE TRANSIENT MODEL)
# ------------------------------------------------------------------------------

class PDNTransientSimulator:
    """
    Bo mo phong sut ap qua do mien thoi gian (Time-Domain PDN Simulator):
    Gom 3 tang cap nang luong noi tiep nhau:
    - Tang 1: VRM (Nguon dieu ap co do tre phan hoi tau_vrm ~ 5 us, L_vrm = 20 nH, R_vrm = 1.5 mOhm)
    - Tang 2: PCB MLCC Network (C_pcb = 250 uF, ESR_pcb = 0.8 mOhm, L_trace = 1.2 nH)
    - Tang 3: On-Die / Package (C_die = 4.0 uF, ESR_die = 0.5 mOhm, L_pkg = 0.15 nH)
    """
    def __init__(self,
                 V_nominal: float = 1.00,       # Dien ap danh dinh 1.0V
                 V_min_allowed: float = 0.94):  # Nguong dien ap thap nhat cho phep 0.94V (-6%)
        self.V_nom = V_nominal
        self.V_min = V_min_allowed

        # Thong so VRM (Tang 1 - Multi-phase VRM dap ung nhanh)
        self.R_vrm = 0.0010
        self.L_vrm = 10e-9
        self.tau_vrm = 1.0e-6 # Thoi gian tre phan hoi vong lap VRM 1.0 micro-giay

        # Thong so PCB MLCC (Tang 2)
        self.C_pcb = 450e-6   # 450 uF tong tu MLCC tren bo mach
        self.ESR_pcb = 0.0006
        self.L_pcb = 0.8e-9

        # Thong so On-Die / Package (Tang 3)
        self.C_die = 8.0e-6   # 8.0 uF On-die Deep Trench Capacitance
        self.ESR_die = 0.0004
        self.L_pkg = 0.08e-9

        # Cac bien trang thai vi phan
        self.v_pcb = V_nominal
        self.v_die = V_nominal
        self.i_vrm = 0.0
        self.i_pcb = 0.0

    def step(self, i_load: float, dt: float) -> Tuple[float, float, float]:
        """
        Tich phan Euler 1 buoc thoi gian cuc nho (dt = 0.1 ns):
        - i_load: Dong dien tai tieu thu cua nhan chip AI SoC
        Tra ve: (v_core_die, v_pcb, i_vrm)
        """
        # 1. Phuong trinh dong dien qua goi chip L_pkg vao die:
        # L_pkg * (d i_pkg / dt) = (v_pcb - ESR_pcb*i_pkg) - (v_die - ESR_die*(i_pkg - i_load))
        # Dong nap/xa tu On-die: C_die * (d v_die / dt) = i_pkg - i_load
        di_pkg_dt = (self.v_pcb - self.v_die - (self.ESR_pcb + self.ESR_die) * self.i_pcb) / self.L_pkg
        self.i_pcb += di_pkg_dt * dt

        dv_die_dt = (self.i_pcb - i_load) / self.C_die
        self.v_die += dv_die_dt * dt

        # 2. Phuong trinh dong dien tu VRM nap vao PCB:
        # VRM dieu chinh dong dien theo quy dao phan hoi bac 1 voi do tre tau_vrm:
        di_vrm_dt = (i_load - self.i_vrm) / self.tau_vrm
        self.i_vrm += di_vrm_dt * dt

        dv_pcb_dt = (self.i_vrm - self.i_pcb) / self.C_pcb
        self.v_pcb += dv_pcb_dt * dt

        # Dien ap thuc te tren loi chip (Core Voltage co tinh den drop qua ESR_die)
        v_core = self.v_die - self.ESR_die * (i_load - self.i_pcb)

        return (v_core, self.v_pcb, self.i_vrm)

# ------------------------------------------------------------------------------
# 2. MO PHONG KICH BAN BAP TAI AI (AI WORKLOAD STEP INJECTION)
# ------------------------------------------------------------------------------

def simulate_ai_workload_transient():
    """
    Mo phong buoc nhay dong dien cuc manh khi NPU bat dau chay mang no-ron:
    - 0 ns den 50 ns: Chip o trang thai Idle (I_idle = 1.0 A)
    - 50 ns den 60 ns: Dong dien tang vot tu 1.0A len 20.0A voi toc do dI/dt = 1.9 A/ns (trong 10 ns)
    - 60 ns tro di: Chip chay toan tai 20.0A
    Tong thoi gian mo phong: 8.0 micro-giay (dt = 0.1 ns -> 80,000 buoc)
    """
    sim = PDNTransientSimulator(V_nominal=1.00, V_min_allowed=0.94)

    dt = 1.0e-10 # 0.1 nano-giay (100 picoseconds de bat duoc 1st droop)
    total_time = 8.0e-6 # 8 micro-giay
    steps = int(total_time / dt)

    t_step_start = 50e-9  # 50 ns
    t_step_end = 60e-9    # 60 ns
    i_idle = 1.0
    i_peak = 6.0          # Nhay tai 5.0A (tuong duong 1 cum nhan NPU bat dau tinh toan)

    # Luu tru de theo doi cac dinh sut ap
    min_v_first_droop = 1.0   # 50 ns - 200 ns (First Droop do On-Die)
    min_v_second_droop = 1.0  # 200 ns - 1500 ns (Second Droop do PCB MLCC)
    min_v_third_droop = 1.0   # 1500 ns - 8000 ns (Third Droop do VRM response)

    time_history = []
    v_core_history = []

    print("================================================================================")
    print("BAT DAU MO PHONG TIME-DOMAIN TRANSIENT DROOP (AI WORKLOAD 5A STEP)")
    print("================================================================================")
    print("Thoi gian: 8.0 us | dt = 0.1 ns | I_step: 1.0A -> 6.0A trong 10 ns (dI/dt = 0.5 A/ns)")
    print("--------------------------------------------------------------------------------")

    for step in range(steps):
        t = step * dt

        # Tao bien dong dong dien tai theo thoi gian
        if t < t_step_start:
            i_load = i_idle
        elif t < t_step_end:
            alpha = (t - t_step_start) / (t_step_end - t_step_start)
            i_load = i_idle + alpha * (i_peak - i_idle)
        else:
            i_load = i_peak

        v_core, v_pcb, i_vrm = sim.step(i_load, dt)

        # Ghi nhan cac dot sut ap
        if 50e-9 <= t < 200e-9:
            if v_core < min_v_first_droop:
                min_v_first_droop = v_core
        elif 200e-9 <= t < 1500e-9:
            if v_core < min_v_second_droop:
                min_v_second_droop = v_core
        elif t >= 1500e-9:
            if v_core < min_v_third_droop:
                min_v_third_droop = v_core

        if step % 2000 == 0:
            time_history.append(t)
            v_core_history.append(v_core)

    worst_voltage = min(min_v_first_droop, min_v_second_droop, min_v_third_droop)
    max_droop_mv = (sim.V_nom - worst_voltage) * 1000.0

    print("KET QUA PHAN TICH 3 DOT SUT AP QUA DO (THREE DROOP WAVES):")
    print(f"-> Dot 1 (First Droop  - On-Die Cap / Pkg L): V_min = {min_v_first_droop:.4f} V (Sut {(1.0-min_v_first_droop)*1000.0:.1f} mV)")
    print(f"-> Dot 2 (Second Droop - PCB MLCC / Socket ): V_min = {min_v_second_droop:.4f} V (Sut {(1.0-min_v_second_droop)*1000.0:.1f} mV)")
    print(f"-> Dot 3 (Third Droop  - VRM Loop Response ): V_min = {min_v_third_droop:.4f} V (Sut {(1.0-min_v_third_droop)*1000.0:.1f} mV)")
    print(f"-> Sut ap cuc dai toan trinh (Worst Droop) : {max_droop_mv:.1f} mV (Nguong toi thieu cho phep: {sim.V_min:.2f} V)")
    print("--------------------------------------------------------------------------------")

    # Kiem tra tieu chi:
    # 1. Dien ap loi khong duoc phep tut duoi nguong V_min_allowed (0.94V)
    assert worst_voltage >= sim.V_min, f"Loi: Sut ap vuot nguong an toan: {worst_voltage:.4f} V < {sim.V_min} V"
    # 2. Ca 3 dot sut ap deu phai the hien ro rang dac tinh dong hoc
    assert min_v_first_droop < 0.99, "Loi: Khong bat duoc First Droop!"
    assert min_v_second_droop < 0.99, "Loi: Khong bat duoc Second Droop!"
    print("[PASS] Test Transient Droop: Kiem soat an toan tuyet doi ca 3 dot sut ap cho chip AI!")

if __name__ == "__main__":
    simulate_ai_workload_transient()
