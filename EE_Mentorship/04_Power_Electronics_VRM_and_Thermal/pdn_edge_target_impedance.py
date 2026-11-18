"""
================================================================================
CHUYEN DE AH: POWER DELIVERY NETWORK (PDN) IMPEDANCE & DVFS POWER GOVERNOR
BAI 1: TRO KHANG MUC TIEU TARGET IMPEDANCE VA PHO TAN SO MANG NGUON PDN
================================================================================
Hoc vien: Le Dac Anh Tuan (18 tuoi)
Muc tieu: Tinh toan tinh toan ven nguon dien Power Integrity cho chip Apple Silicon / Tesla FSD
Ngon ngu: Python 3 thuan tuy, phan tich pho tro khang Z(f) mang R-L-C da tang
================================================================================
"""

import math
from typing import List, Tuple, Dict

# ------------------------------------------------------------------------------
# 1. MO HINH LINH KIEN TU GIAI NGAU DECOUPLING CAPACITOR (RLC MODEL)
# ------------------------------------------------------------------------------

class DecouplingCapacitor:
    """
    Mo hinh vat ly tu dien thuc te (Real Capacitor RLC Model):
    - C: Dien dung danh dinh (Farad)
    - ESR: Dien tro noi tiep tuong duong (Equivalent Series Resistance, Ohm)
    - ESL: Dien cam noi tiep tuong duong (Equivalent Series Inductance, Henry)
    Trơ khang phuc cua 1 tu dien: Z_cap(s) = ESR + s*ESL + 1/(s*C)
    """
    def __init__(self, name: str, C: float, ESR: float, ESL: float, count: int = 1):
        self.name = name
        self.C = C
        self.ESR = ESR
        self.ESL = ESL
        self.count = count # So luong tu mac song song

    def impedance_at_freq(self, freq_hz: float) -> complex:
        """Tinh tro khang phuc Z(f) tai tan so freq_hz cua mang N tu song song."""
        if freq_hz <= 0.0:
            freq_hz = 1.0 # Tranh chia cho 0
        w = 2.0 * math.pi * freq_hz
        
        # Z cua 1 tu don le
        z_single = complex(self.ESR, w * self.ESL - 1.0 / (w * self.C))
        # N tu mac song song: Z_total = Z_single / count
        return z_single / float(self.count)

# ------------------------------------------------------------------------------
# 2. MANG PHAN PHOI NGUON DA TANG POWER DELIVERY NETWORK (PDN)
# ------------------------------------------------------------------------------

class PowerDeliveryNetwork:
    """
    Mang luoi cap nguon PDN tu nguon VRM toi nhan silicon SoC:
    - Vdd: Dien ap nguon danh dinh (Volt, vi du 0.85V cho core logic)
    - I_step: Buoc nhay dong dien cuc dai khi chip chay AI (Ampe, vi du 80A)
    - allowed_ripple_percent: Dung sai dao dong dien ap cho phep (vi du 5% = 0.05)
    - R_vrm, L_vrm: Tro khang dau ra cua module dieu ap VRM
    """
    def __init__(self,
                 Vdd: float = 0.85,
                 I_step: float = 80.0,
                 allowed_ripple_percent: float = 0.05,
                 R_vrm: float = 0.001,       # 1 mOhm
                 L_vrm: float = 50e-9):      # 50 nH
        self.Vdd = Vdd
        self.I_step = I_step
        self.allowed_ripple_percent = allowed_ripple_percent
        self.R_vrm = R_vrm
        self.L_vrm = L_vrm

        # 1. Tinh toan Tro khang muc tieu (Target Impedance):
        # Delta_V = Vdd * allowed_ripple_percent
        # Z_target = Delta_V / I_step
        self.delta_v_allowed = Vdd * allowed_ripple_percent # 0.85 * 0.05 = 0.0425 V = 42.5 mV
        self.z_target = self.delta_v_allowed / I_step       # 0.0425 / 80 = 0.000531 Ohm = 0.531 mOhm

        self.capacitors: List[DecouplingCapacitor] = []

    def add_capacitor_bank(self, cap: DecouplingCapacitor) -> None:
        """Them mot cum tu giai ngau vao mang PDN."""
        self.capacitors.append(cap)

    def total_impedance_at_freq(self, freq_hz: float) -> float:
        """
        Tinh tong tro khang tuong duong |Z_pdn(f)| (Ohm):
        Gom: Tro khang VRM mac song song voi tat ca cac cum tu MLCC, Bulk, On-die.
        1 / Z_total = 1 / Z_vrm + sum(1 / Z_cap_bank)
        """
        if freq_hz <= 0.0:
            freq_hz = 1.0
        w = 2.0 * math.pi * freq_hz

        # Tro khang VRM
        z_vrm = complex(self.R_vrm, w * self.L_vrm)
        y_total = 1.0 / z_vrm

        # Cong dan dan nap (Admittance Y = 1 / Z) cua cac cum tu song song
        for cap in self.capacitors:
            z_c = cap.impedance_at_freq(freq_hz)
            if abs(z_c) > 1e-12:
                y_total += 1.0 / z_c

        z_total = 1.0 / y_total
        return abs(z_total)

    def analyze_frequency_profile(self,
                                  f_start: float = 1e3,
                                  f_end: float = 1e8,
                                  num_points: int = 100) -> Dict[str, any]:
        """
        Quet pho tan so logarit tu f_start den f_end (vi du 1 kHz den 100 MHz):
        Xac dinh xem |Z_pdn(f)| co vuot qua Z_target o tan so nao khong (PDN Violation).
        """
        log_start = math.log10(f_start)
        log_end = math.log10(f_end)
        step = (log_end - log_start) / (num_points - 1)

        frequencies = []
        impedances = []
        max_impedance = 0.0
        worst_freq = 0.0
        violations_count = 0

        for i in range(num_points):
            f = 10.0 ** (log_start + i * step)
            z_mag = self.total_impedance_at_freq(f)

            frequencies.append(f)
            impedances.append(z_mag)

            if z_mag > max_impedance:
                max_impedance = z_mag
                worst_freq = f

            if z_mag > self.z_target:
                violations_count += 1

        is_passed = (violations_count == 0)

        return {
            "z_target": self.z_target,
            "max_impedance": max_impedance,
            "worst_freq": worst_freq,
            "violations_count": violations_count,
            "is_passed": is_passed
        }

# ------------------------------------------------------------------------------
# 3. MO PHONG VA KIEM CHUNG PHO TRO KHANG MANG NGUON CHIP FSD
# ------------------------------------------------------------------------------

def test_pdn_target_impedance_design():
    """
    Thiet ke mang Board-level PDN cho Chip AI SoC Tesla FSD / Apple Silicon:
    Vdd = 1.0 V, I_step = 12.0 A, Dung sai 5% -> Delta_V = 50 mV -> Z_target = 4.167 mOhm.
    Dai tan hoat dong cua Board-level PDN: tu 1 kHz den 40 MHz.
    Tich hop mang tu 3 tang:
    1. Tang Bulk (Tan so thap 1 kHz - 100 kHz): Tu Tantalum/Polymer 470 uF.
    2. Tang PCB MLCC (Tan so trung 100 kHz - 10 MHz): Tu gom 22 uF va 2.2 uF.
    3. Tang Package Decoupling (Tan so cao 10 MHz - 40 MHz): Tu gom nho 0.1 uF sieu thap ESL.
    """
    pdn = PowerDeliveryNetwork(
        Vdd=1.00,
        I_step=12.0,
        allowed_ripple_percent=0.05,
        R_vrm=0.001,  # 1.0 mOhm VRM
        L_vrm=15e-9   # 15 nH
    )

    expected_z_target = (1.00 * 0.05) / 12.0 # 4.1667 mOhm
    assert abs(pdn.z_target - expected_z_target) < 1e-6, "Loi tinh toan Z_target!"

    print("--------------------------------------------------------------------------------")
    print(f"THIET KE PDN TARGET IMPEDANCE (SOC APPLE SILICON / TESLA FSD):")
    print(f"-> Dien ap danh dinh Vdd            : {pdn.Vdd:.2f} V")
    print(f"-> Buoc nhay dong dien AI I_step     : {pdn.I_step:.1f} A")
    print(f"-> Do sut ap cho phep Delta_V        : {pdn.delta_v_allowed * 1000.0:.2f} mV")
    print(f"-> Tro khang muc tieu bat buoc Z_tgt: {pdn.z_target * 1000.0:.3f} mOhm")
    print("--------------------------------------------------------------------------------")

    # Truong hop 1: Chua co du tu giai ngau (Thieu tu -> Vi pham tro khang muc tieu)
    pdn.add_capacitor_bank(DecouplingCapacitor("Bulk_Polymer", C=470e-6, ESR=0.006, ESL=2.0e-9, count=2))
    res_poor = pdn.analyze_frequency_profile(f_start=1e3, f_end=4e7, num_points=100)
    print(f"-> Kiem tra mang thieu tu: Max Z = {res_poor['max_impedance'] * 1000.0:.2f} mOhm tai {res_poor['worst_freq']/1e6:.2f} MHz (FAIL - Bi dinh cong huong)")
    assert not res_poor["is_passed"], "Loi: Mang thieu tu phai bi vuot Z_target!"

    # Truong hop 2: Bo sung day du tu gom MLCC va Package de san phang pho tro khang
    # Them 6 tu Bulk Polymer (ESR = 6 mOhm, ESL = 2.0 nH) dập tắt sụt áp dải tần thấp
    pdn.add_capacitor_bank(DecouplingCapacitor("Bulk_Polymer", C=470e-6, ESR=0.006, ESL=2.0e-9, count=6))
    # Them 24 tu 22 uF (ESR = 3 mOhm, ESL = 0.35 nH)
    pdn.add_capacitor_bank(DecouplingCapacitor("MLCC_22uF", C=22e-6, ESR=0.003, ESL=0.35e-9, count=24))
    # Them 36 tu 4.7 uF dem tan so (ESR = 4 mOhm, ESL = 0.25 nH)
    pdn.add_capacitor_bank(DecouplingCapacitor("MLCC_4.7uF", C=4.7e-6, ESR=0.004, ESL=0.25e-9, count=36))
    # Them 48 tu 1.0 uF (ESR = 5 mOhm, ESL = 0.18 nH)
    pdn.add_capacitor_bank(DecouplingCapacitor("MLCC_1.0uF", C=1.0e-6, ESR=0.005, ESL=0.18e-9, count=48))
    # Them 60 tu 0.1 uF Package (ESR = 6 mOhm, ESL = 0.05 nH)
    pdn.add_capacitor_bank(DecouplingCapacitor("Pkg_0.1uF", C=0.1e-6, ESR=0.006, ESL=0.05e-9, count=60))

    res_good = pdn.analyze_frequency_profile(f_start=1e3, f_end=4e7, num_points=100)
    print(f"-> Kiem tra mang toi uu  : Max Z = {res_good['max_impedance'] * 1000.0:.3f} mOhm <= Z_target {pdn.z_target * 1000.0:.3f} mOhm")
    print(f"-> So diem vi pham tro khang: {res_good['violations_count']} diem.")
    print("--------------------------------------------------------------------------------")

    # Kiem tra tieu chi:
    # Mang PDN toi uu phai duy tri |Z(f)| nam duoi nguong Z_target tren toan bo dải tu 1 kHz den 40 MHz
    assert res_good["is_passed"], f"Loi: PDN toi uu van bi vuot nguong: {res_good['max_impedance'] * 1000.0:.3f} mOhm"
    assert res_good["max_impedance"] <= pdn.z_target, "Loi: Max impedance vuot Z_target!"
    print("[PASS] Test PDN Target Impedance: Mang cap nguon dat chuan Power Integrity tuyet doi!")

if __name__ == "__main__":
    print("================================================================================")
    print("DEMO POWER DELIVERY NETWORK (PDN) TARGET IMPEDANCE PROFILING")
    print("================================================================================")
    test_pdn_target_impedance_design()
