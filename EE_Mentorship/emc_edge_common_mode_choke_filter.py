"""
Chuyen de AU: Tuong thich Dien tu EMC/EMI & Ky thuat Tiep dia PCB Toc do cao
Bai 133 (Milestone AU.2): Cuon cam chan dong pha (Common Mode Choke) va Bo loc nguon EMI X/Y

Author: Le Dac Anh Tuan (18 tuoi) - Electrical Engineering Student
Muc tieu: Lam chu nguyen ly triet tu thong vi sai va cong huong tu thong dong pha tren loi Ferit,
          tinh toan tan so tu cong huong Self-Resonant Frequency (SRF), do suy giam Insertion Loss
          va gioi han dong ro an toan nguoi (Leakage Current) cho tu Y theo chuan IEC 62368-1.

QUY TAC GIANG DAY CONSTRUCTIVIST BOTTOM-UP:
- KHONG dung ky hieu LaTeX hoac cap dau dollar.
- Toan bo bieu thuc toan hoc duoc bieu dien duoi dang khoi ASCII truc quan.
- Chuan hoa ma nguon tuong thich Windows cp1252.
"""

import math
from typing import List, Tuple, Dict


class CommonModeChokeModel:
    """
    Mo hinh cuon cam chan dong pha (Common-Mode Choke - CMC) voi ky sinh dien dung va dien tro loi.
    
    Phan tich toan hoc & mach tuong duong:
    ┌────────────────────────────────────────────────────────┐
    │                                                        │
    │   1. Tu thong vi sai (DM):                             │
    │      Phi_DM = Phi_1 - Phi_2 = 0                        │
    │      => Tro khang vi sai chi la L_leakage << L_CM      │
    │                                                        │
    │   2. Tu thong dong pha (CM):                           │
    │      Phi_CM = Phi_1 + Phi_2 = 2 * Phi                  │
    │      => Tao ra cam khang dong pha lon L_CM             │
    │                                                        │
    │   3. Tan so tu cong huong SRF (Self-Resonant Freq):   │
    │                          1                             │
    │      f_SRF = ────────────────────────────              │
    │              2 * pi * sqrt(L_CM * C_parasitic)         │
    │                                                        │
    │   4. Tro khang dong pha tong hop Z_CM(f):              │
    │                 1                                      │
    │      Y(f) = ───────── + j * 2 * pi * f * C_p           │
    │             R_p + jwL                                  │
    │      Z_CM(f) = 1 / |Y(f)|                              │
    │                                                        │
    │   5. Do suy giam xen vao (Insertion Loss):             │
    │      IL_CM (dB) = 20 * log10( 1 + Z_CM / (2 * Z_0) )   │
    │                                                        │
    └────────────────────────────────────────────────────────┘
    """
    def __init__(
        self,
        l_cm_henry: float = 4.7e-3,       # 4.7 mH
        c_parasitic_farad: float = 12e-12, # 12 pF
        r_core_loss_ohm: float = 3500.0,  # Tro ton hao loi Ferit tai cong huong
        l_leakage_henry: float = 47e-6,   # 47 uH (1% L_CM)
        r_dcr_ohm: float = 0.08           # 80 mOhm DC resistance
    ):
        self.l_cm = float(l_cm_henry)
        self.c_p = float(c_parasitic_farad)
        self.r_p = float(r_core_loss_ohm)
        self.l_leakage = float(l_leakage_henry)
        self.r_dcr = float(r_dcr_ohm)

        # Tan so tu cong huong
        self.f_srf = 1.0 / (2.0 * math.pi * math.sqrt(self.l_cm * self.c_p))

    def calculate_cm_impedance_ohm(self, f_hz: float) -> float:
        """
        Tinh do lon tro khang dong pha |Z_CM(f)| tai tan so f_hz.
        """
        if f_hz <= 0.0:
            return self.r_dcr

        omega = 2.0 * math.pi * f_hz
        # Nhanh cam khang: Z_L = r_dcr + j * omega * l_cm
        # Nhanh dien dung: Z_C = 1 / (j * omega * c_p)
        # Nhanh dien tro ton hao song song: R_p
        # Dan nap tong hop Y_total = 1 / (r_dcr + j*w*L) + 1 / R_p + j*w*C_p
        z_l_real = self.r_dcr
        z_l_imag = omega * self.l_cm
        denom_l = z_l_real ** 2 + z_l_imag ** 2

        g_branch = (z_l_real / denom_l) + (1.0 / self.r_p)
        b_branch = (-z_l_imag / denom_l) + (omega * self.c_p)

        y_mag = math.sqrt(g_branch ** 2 + b_branch ** 2)
        return 1.0 / max(1e-12, y_mag)

    def calculate_dm_impedance_ohm(self, f_hz: float) -> float:
        """
        Tinh tro khang vi sai (chi do L_leakage va R_dcr quyet dinh).
        """
        omega = 2.0 * math.pi * f_hz
        return math.sqrt(self.r_dcr ** 2 + (omega * self.l_leakage) ** 2)

    def calculate_insertion_loss_db(self, f_hz: float, z0_ohm: float = 50.0) -> float:
        """
        Tinh do suy giam xen vao Insertion Loss (don vi dB) tren he thong z0.
        """
        z_cm = self.calculate_cm_impedance_ohm(f_hz)
        ratio = 1.0 + (z_cm / (2.0 * z0_ohm))
        return 20.0 * math.log10(max(1.0, ratio))


class EMILineFilterSafety:
    """
    Tinh toan thiet ke tu loc X (vi sai) va tu loc Y (dong pha xuong Chassis Ground)
    kem theo rang buoc an toan dong dien ro (Leakage Current Safety Limit).
    
    Phan tich an toan IEC 62368-1 / UL 60950:
    ┌────────────────────────────────────────────────────────┐
    │                                                        │
    │   Dong ro qua tu Y xuong dat o tan so dien luoi:      │
    │                                                        │
    │   I_leakage = 2 * pi * f_line * V_line * (2 * C_Y)     │
    │                                                        │
    │   Gioi han an toan cho nguoi: I_leakage <= 0.75 mA     │
    │   (Doi voi thiet bi cam tay Apple / y te: <= 0.25 mA)  │
    │                                                        │
    │   Tu Y cuc dai cho phep:                               │
    │                         I_leak_max                     │
    │   C_Y_max = ─────────────────────────────────          │
    │              4 * pi * f_line * V_line                  │
    │                                                        │
    └────────────────────────────────────────────────────────┘
    """
    @staticmethod
    def calculate_leakage_current_ma(
        c_y_farad: float,
        v_line_volts: float = 230.0,
        f_line_hz: float = 50.0
    ) -> float:
        """
        Tinh dong ro xuong vo may (don vi mA). 2 tu Y cho ca Line va Neutral.
        """
        i_amps = 2.0 * math.pi * f_line_hz * v_line_volts * (2.0 * c_y_farad)
        return i_amps * 1000.0

    @staticmethod
    def calculate_max_safe_cy_farad(
        max_leakage_ma: float = 0.5,
        v_line_volts: float = 230.0,
        f_line_hz: float = 50.0
    ) -> float:
        """
        Tinh gia tri tu Y toi da cho phep de dam bao tieu chuan an toan.
        """
        i_max_amps = max_leakage_ma * 1e-3
        return i_max_amps / (4.0 * math.pi * f_line_hz * v_line_volts)


def test_common_mode_choke_and_filter():
    print("================================================================================")
    print("TEST SUITE: CUON CAM CHAN DONG PHA (CMC) VA BO LOC EMI X/Y AN TOAN DONG RO")
    print("================================================================================")

    # 1. Kiem tra cuon cam chan dong pha 4.7 mH, C_p = 12 pF
    cmc = CommonModeChokeModel(l_cm_henry=4.7e-3, c_parasitic_farad=12e-12, r_core_loss_ohm=4500.0)
    print(f"[1] Cuon cam chan CMC 4.7 mH | C_p = 12 pF:")
    print(f"    - Tan so tu cong huong ly thuyet f_SRF: {cmc.f_srf / 1e3:.2f} kHz")
    expected_srf_khz = (1.0 / (2.0 * math.pi * math.sqrt(4.7e-3 * 12e-12))) / 1e3
    assert abs(cmc.f_srf / 1e3 - expected_srf_khz) < 0.1, "Loi tinh f_SRF"

    # 2. Kiem tra tro khang dong pha Z_CM vs tro khang vi sai Z_DM tai 100 kHz
    f_test = 100e3  # 100 kHz
    z_cm_100k = cmc.calculate_cm_impedance_ohm(f_test)
    z_dm_100k = cmc.calculate_dm_impedance_ohm(f_test)
    il_cm_db = cmc.calculate_insertion_loss_db(f_test, z0_ohm=50.0)

    print(f"\n[2] Dap ung tai tan so chuyen mach 100 kHz:")
    print(f"    - Tro khang dong pha |Z_CM|: {z_cm_100k:.1f} Ohm")
    print(f"    - Tro khang vi sai    |Z_DM|: {z_dm_100k:.2f} Ohm")
    print(f"    - Do suy giam xen vao (Insertion Loss): {il_cm_db:.2f} dB")
    
    # Tro khang dong pha phai lon hon tro khang vi sai it nhat 50 lan!
    assert z_cm_100k > 50.0 * z_dm_100k, "Tro khang dong pha phai vuot troi vi sai"
    assert il_cm_db > 25.0, "Do suy giam dong pha phai vuot 25 dB tai 100 kHz"

    # 3. Kiem tra dac tinh qua tan so cong huong:
    # Truoc SRF (500 kHz): mang tinh cam khang
    # Sau SRF (5 MHz): mang tinh dung khang (tro khang giam)
    z_peak = cmc.calculate_cm_impedance_ohm(cmc.f_srf)
    z_high = cmc.calculate_cm_impedance_ohm(10e6)
    print(f"\n[3] Phan tich hanh vi quanh dinh cong huong:")
    print(f"    - Tai dinh cong huong f_SRF ({cmc.f_srf/1e3:.1f} kHz): |Z_CM| = {z_peak:.1f} Ohm")
    print(f"    - Tai tan so cao vuot nguong (10 MHz):          |Z_CM| = {z_high:.1f} Ohm")
    assert z_peak > z_high, "Tai SRF tro khang phai dat cuc dai"
    assert z_peak > 3000.0, "Tro khang dinh phai tren 3 kOhm do loi Ferit dam bao"

    # 4. Kiem tra gioi han dong ro an toan tu Y theo chuan IEC 62368-1
    # Voi dien luoi 230V / 50Hz, yeu cau dong ro <= 0.5 mA
    max_safe_cy = EMILineFilterSafety.calculate_max_safe_cy_farad(max_leakage_ma=0.5, v_line_volts=230.0, f_line_hz=50.0)
    print(f"\n[4] Kiem tra an toan dien giat tu Y (Chuan IEC 62368-1 tai 230V 50Hz):")
    print(f"    - Tu Y toi da cho phep de dong ro <= 0.5 mA: {max_safe_cy * 1e9:.2f} nF")
    assert max_safe_cy < 4.0e-9, "Tu Y khong duoc vuot qua 4 nF de tranh giat nguoi"

    # Xet bo loc thuc te voi tu Y = 2.2 nF
    cy_chosen = 2.2e-9  # 2.2 nF
    leakage_act = EMILineFilterSafety.calculate_leakage_current_ma(cy_chosen, v_line_volts=230.0, f_line_hz=50.0)
    print(f"    - Voi tu thuc te C_Y = 2.2 nF: Dong ro thuc te = {leakage_act:.3f} mA (Dat chuan an toan < 0.5 mA)")
    assert leakage_act < 0.5, "Dong ro tu Y 2.2 nF phai thoa man duoi 0.5 mA"

    print("\n--> TAT CA CAC KIEM TRA MILESTONE AU.2 DA THANH CONG 100%!")


if __name__ == "__main__":
    test_common_mode_choke_and_filter()
