"""
================================================================================
          MODULE V: EMBEDDED BATTERY MANAGEMENT SYSTEMS (BMS)
              MILESTONE V.2: THEVENIN 1-RC EQUIVALENT CIRCUIT MODEL (ECM)
================================================================================

TAI SAO DO DIEN AP TRUC TIEP KHONG THE BIET CHINH XAC MUC PIN KHI XE DANG CHAY?
Khi xe dien dap ga tang toc hoac drone doc luc bieu dien:
- Dong xa lon (vi du 30A - 100A) lam sut ap tuc thoi do noi tro thuan R0 (Ohmic Drop: I * R0).
- Sau do, phan ung hoa hoc khuyech tan ion Lithium trong chat dien phan cham hon nhieu
  (Polarization Overpotential R1-C1).
- Neu khong co mo hinh Thevenin giai ma tach biet hai thanh phan nay, vi dieu khien
  BMS se bao dong sai "Pin yeu gia" (False Low-Battery Warning) va ngat xe giua duong!

SO DO MACH TUONG DUONG THEVENIN 1-RC (ASCII TEXT BLOCK):

                   R0 (Ohmic)          R1 (Polarization)
       (+) ───────/\/\/\/\───────┬──────────/\/\/\/\──────────┬─────── (+)
                                 │                            │
                                === C1                       === C_bat (Voc)
                                 │  (Lop kep dien hoa)        │  (Nguon OCV)
       (-) ──────────────────────┴────────────────────────────┴─────── (-)

1. DIEN AP TAI HAI DAU CUC PIN (TERMINAL VOLTAGE V_t):
         V_t = Voc(SOC) - I_load * R0 - V_p

2. PHUONG TRINH VI PHAN DONG HOC PHAN CUC DIEN HOA:
         d(V_p)      -V_p           I_load
        ──────── = ───────────  +  ────────
           dt        R1 * C1          C1

   Voi tau = R1 * C1 la hang so thoi gian hoi phuc dong ion hoa hoc (thuong tu 10s - 30s).

3. DANG ROI RAC HOA CHINH XAC TRONG VI DIEU KHIEN NHUNG (MCU DISCRETIZATION):
         V_p[k + 1] = V_p[k] * exp(-dt / tau) + I_load * R1 * (1 - exp(-dt / tau))
"""

from typing import Tuple, List, Dict, Any, Optional
import numpy as np


class TheveninBatteryModel:
    """
    Mo hinh mach tuong duong Thevenin 1-RC (Equivalent Circuit Model)
    Mo ta chinh xac dong hoc sut ap Ohmic va phan cuc dien hoa cua cell Lithium-ion.
    """
    def __init__(self, r0_ohm: float = 0.025, r1_ohm: float = 0.015, c1_farad: float = 1200.0):
        """
        - r0_ohm: Noi tro thuan Ohmic (25 mOhm do dien cuc va dung dich dien phan)
        - r1_ohm: Tro khang chuyen dien tich phan cuc dien hoa (15 mOhm)
        - c1_farad: Dien dung phan cuc lop kep (1200 Farad -> tau = R1 * C1 = 18 giay)
        """
        self.r0 = r0_ohm
        self.r1 = r1_ohm
        self.c1 = c1_farad
        self.tau = r1_ohm * c1_farad
        self.v_p = 0.0  # Dien ap phan cuc ban dau

    def get_voc_from_soc(self, soc: float) -> float:
        """
        Dac tinh dien ap ho mach OCV phi tuyen theo trang thai dung luong SOC (3.0V -> 4.2V)
        """
        soc_clamped = max(0.0, min(1.0, soc))
        return float(3.2 + 0.9 * soc_clamped + 0.1 * (soc_clamped ** 3))

    def step(self, i_load: float, soc: float, dt_sec: float) -> Dict[str, float]:
        """
        Mo phong 1 buoc thoi gian roi rac tren MCU BMS:
        - i_load: Dong tai xa (A, gia tri duong = xa dong)
        - soc: Muc dung luong hien tai (0.0 -> 1.0)
        - dt_sec: Chu ky lay mau ADC (giay)
        Tra ve: dict chua V_terminal, V_ocv, V_p, V_ohmic
        """
        voc = self.get_voc_from_soc(soc)

        # 1. Cap nhat dien ap phan cuc V_p theo nghiem giai tich roi rac
        decay = float(np.exp(-dt_sec / self.tau))
        self.v_p = float(self.v_p * decay + i_load * self.r1 * (1.0 - decay))

        # 2. Sut ap thuan Ohmic tuc thoi
        v_ohmic = float(i_load * self.r0)

        # 3. Dien ap thuc te tai 2 dau cuc pin (Terminal Voltage)
        v_terminal = float(voc - v_ohmic - self.v_p)

        return {
            "v_terminal": v_terminal,
            "v_ocv": voc,
            "v_p": self.v_p,
            "v_ohmic": v_ohmic
        }


if __name__ == "__main__":
    print("=========================================================")
    print("   EMBEDDED BMS: THEVENIN 1-RC EQUIVALENT CIRCUIT MODEL")
    print("=========================================================\n")

    cell = TheveninBatteryModel(r0_ohm=0.030, r1_ohm=0.020, c1_farad=1000.0)

    # 1. Kiem tra trang thai khong tai (I = 0A) tai 80% SOC
    soc_test = 0.80
    idle_res = cell.step(i_load=0.0, soc=soc_test, dt_sec=1.0)
    print("1. DIEN AP KHI KHONG TAI (IDLE STATE AT 80% SOC):")
    print(f"   -> Dien ap ho mach (Voc)        : {idle_res['v_ocv']:.3f} V")
    print(f"   -> Dien ap tai cuc (V_terminal) : {idle_res['v_terminal']:.3f} V\n")
    assert abs(idle_res["v_terminal"] - idle_res["v_ocv"]) < 1e-4, "Khi I=0, V_terminal phai bang Voc!"

    # 2. Xe dot ngot dap ga tang toc: Xa dong 10A trong 30 giay
    # Quan sat: Sut ap tuc thoi (Ohmic) ngay tai giay 1, sau do sut tu tu do phan cuc hoa hoc (RC)
    print("2. DONG HOC SUT AP KHI DAP GA XA TAI NANG (10A DISCHARGE):")
    step1_res = cell.step(i_load=10.0, soc=soc_test, dt_sec=1.0)
    print(f"   -> Giay thu 1  : V_terminal = {step1_res['v_terminal']:.3f} V | Sut ap Ohmic tuc thoi: {step1_res['v_ohmic']:.3f} V")

    # Tiep tuc xa trong 29 giay tiep theo
    for step in range(29):
        step_res = cell.step(i_load=10.0, soc=soc_test, dt_sec=1.0)

    print(f"   -> Giay thu 30 : V_terminal = {step_res['v_terminal']:.3f} V | Dien ap phan cuc V_p: {step_res['v_p']:.3f} V\n")
    assert step_res["v_terminal"] < step1_res["v_terminal"], "Dien ap phai tiep tuc sut do phan cuc hoa hoc!"

    # 3. Xe nha chan ga (I = 0A): Dien ap hoi phuc tuc thoi phan Ohmic, roi hoi phuc cham phan RC
    print("3. QUA TRINH NHA GA HOI PHUC DIEN AP (RELAXATION DYNAMICS):")
    relax1 = cell.step(i_load=0.0, soc=soc_test, dt_sec=1.0)
    print(f"   -> Giay nghi dau tien : V_terminal bat tro lai len {relax1['v_terminal']:.3f} V (Hoi phuc Ohmic)")

    # Nghi them 60 giay de phan cuc hoa hoc xep xuong
    for step in range(60):
        relax_final = cell.step(i_load=0.0, soc=soc_test, dt_sec=1.0)

    print(f"   -> Sau 60 giay nghi   : V_terminal = {relax_final['v_terminal']:.3f} V (Hoi phuc ve sat Voc {idle_res['v_ocv']:.3f} V)")
    assert abs(relax_final["v_terminal"] - idle_res["v_ocv"]) < 0.05, "Pin phai hoi phuc ve gan Voc khi duoc nghi!"

    print("\n[THANH CONG] MO HINH THEVENIN 1-RC MO PHONG CHINH XAC DONG HOC PIN LITHIUM-ION!")
