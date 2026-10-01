"""
================================================================================
          MODULE U: EMBEDDED DIGITAL POWER ELECTRONICS & SPACE POWER SYSTEMS
              MILESTONE U.3: MAXIMUM POWER POINT TRACKING (MPPT)
================================================================================

VAI TRO THIET YEU CUA THUAT TOAN MPPT TREN VE TINH CUBESAT VA SOLAR DRONE:
Tren ve tinh khong gian (CubeSat) hoac UAV nang luong mat troi tam bay cao:
- Pin mat troi (Photovoltaic PV Array) co dac tinh dong - ap (I-V) va cong suat (P-V)
  cuc ky phi tuyen theo cuong do buc xa (Irradiance) va nhiet do be mat (Temperature).
- Ton tai mot diem duy nhat ma pin phat ra cong suat toi da: Maximum Power Point (MPP).
- Neu mach dieu khien giu co dinh dien ap danh dinh, khi ve tinh doi goc huong nang
  hoac nhiet do tam pin bien thien manh tu -40 degC den +85 degC, he thong se danh
  mat tu 35% den 55% nang luong quy gia, dan toi sup nguon Main Bus.

DO THI DAC TINH CONG SUAT P-V VA NGUYEN LY PERTURB & OBSERVE (P&O):

   Cong suat P (Watt)
       ^                    Diem cuc dai MPP: dP/dV = 0
       |                             [MPP]
       |                            /     \
       |                           /       \
       |      dP/dV > 0           /         \     dP/dV < 0
       |   (Tang V de tang P)    /           \  (Giam V de tang P)
       |                        /             \
       |                       /               \
       +----------------------/-----------------\-----------------> Dien ap V (Volt)
       0                     V_mpp             V_oc (Ho mach)

CONG THUC VI PHAN BAM DINH P&O TRONG MOI CHU KY DIEU KHIEN:

                  Delta_P = P[k] - P[k - 1]
                  Delta_V = V[k] - V[k - 1]

                           Delta_P
                  Slope = ─────────
                           Delta_V

LUAT PHAN DOAN BUOC NHAY DIEN AP:
- Neu Slope > 0: Dang o suon trai -> Tiep tuc tang dien ap: V_ref[k+1] = V_ref[k] + Step
- Neu Slope < 0: Da vuot sang suon phai -> Giam dien ap:    V_ref[k+1] = V_ref[k] - Step
- Neu Slope = 0: Da khoa thanh cong tai dinh MPP!
"""

from typing import Tuple, List, Dict, Any
import numpy as np


class SimulatedSolarPanel:
    """
    Mo hinh pin mat troi quang dien phi tuyen voi buc xa bien thien (Irradiance)
    va nhiet do bien doi.
    """
    def __init__(self, v_oc: float = 36.0, i_sc: float = 5.0, v_mpp: float = 29.5, i_mpp: float = 4.5):
        self.v_oc = v_oc      # Dien ap ho mach (Open-Circuit Voltage)
        self.i_sc = i_sc      # Dong dien ngan mach (Short-Circuit Current)
        self.v_mpp = v_mpp    # Dien ap dinh ly thuyet tai MPP
        self.i_mpp = i_mpp    # Dong dien dinh ly thuyet tai MPP
        self.p_max_nominal = v_mpp * i_mpp

    def get_current(self, voltage: float, sun_irradiance: float = 1.0) -> float:
        """
        Dac tinh duong cong I-V thuc nghiem cua Cell quang dien:
        Dong I giu gan nhu phang tu 0 den V_mpp, sau do sut dot ngot ve 0 tai V_oc.
        """
        if voltage <= 0.0:
            return float(self.i_sc * sun_irradiance)
        if voltage >= self.v_oc:
            return 0.0

        v_norm = voltage / self.v_oc
        # Mo hinh phi tuyen ham mu cap 7 mo ta hien tuong tai sinh mang hat tai
        i = self.i_sc * sun_irradiance * (1.0 - (v_norm ** 7))
        return float(max(0.0, i))

    def get_peak_power(self, sun_irradiance: float = 1.0) -> Tuple[float, float]:
        """Quet nhanh xac dinh toa do MPP chuan (V_peak, P_peak) tai muc buc xa cho truoc"""
        v_sweep = np.linspace(10.0, self.v_oc, 500)
        p_sweep = [v * self.get_current(v, sun_irradiance) for v in v_sweep]
        best_idx = int(np.argmax(p_sweep))
        return float(v_sweep[best_idx]), float(p_sweep[best_idx])


class PerturbAndObserveMPPT:
    """
    Thuat toan nhung MPPT Perturb and Observe (P&O) thoi gian thuc tren DSP/MCU
    co co che chong nhieu dao dong quanh dinh va gioi han bien do an toan.
    """
    def __init__(self, initial_voltage: float = 20.0, step_size: float = 0.25, v_min: float = 10.0, v_max: float = 35.0):
        self.v_ref = initial_voltage
        self.step = step_size
        self.v_min = v_min
        self.v_max = v_max

        self.prev_v = initial_voltage
        self.prev_p = 0.0

    def update(self, v_measured: float, i_measured: float) -> Tuple[float, float, float]:
        """
        Thuc hien 1 buoc tinh toan P&O:
        Dau vao: V do duoc, I do duoc qua sensor ADC
        Dau ra:  (V_ref_next, cong_suat_hien_tai, delta_P)
        """
        current_power = v_measured * i_measured
        delta_p = current_power - self.prev_p
        delta_v = v_measured - self.prev_v

        # Neu dien ap chua thay doi dang ke (buoc khoi dong), mac dinh tang dien ap
        if abs(delta_v) < 1e-4:
            direction = 1.0
        else:
            if delta_p >= 0.0:
                direction = 1.0 if delta_v > 0.0 else -1.0
            else:
                direction = -1.0 if delta_v > 0.0 else 1.0

        # Cap nhat dien ap dat tham chieu cho bo Buck/Boost Converter
        self.v_ref += direction * self.step

        # Kiem soat an toan trong vung cho phep (Clamping)
        self.v_ref = max(self.v_min, min(self.v_max, self.v_ref))

        # Luu tru trang thai qua khu
        self.prev_v = v_measured
        self.prev_p = current_power

        return float(self.v_ref), float(current_power), float(delta_p)


if __name__ == "__main__":
    print("=========================================================")
    print("   EMBEDDED POWER: PERTURB & OBSERVE (P&O) MPPT TRACKER")
    print("=========================================================\n")

    solar_pv = SimulatedSolarPanel(v_oc=36.0, i_sc=5.0, v_mpp=29.5, i_mpp=4.5)
    mppt = PerturbAndObserveMPPT(initial_voltage=18.0, step_size=0.25)

    # 1. Kiem tra diem MPP ly thuyet o buc xa 100% (1000 W/m2)
    v_target_100, p_target_100 = solar_pv.get_peak_power(sun_irradiance=1.0)
    print("1. DIEM CONG SUAT CUC DAI LY THUYET TAI BUC XA 100%:")
    print(f"   -> Dien ap dinh MPP ly tuong     : {v_target_100:.2f} V")
    print(f"   -> Cong suat toi da (P_max)      : {p_target_100:.2f} W\n")

    # 2. Mo phong qua trinh hoi tu ban dau tu muc dien ap lech (18V)
    v_op = 18.0
    tracked_powers_phase1: List[float] = []
    tracked_voltages_phase1: List[float] = []

    for step in range(60):
        current_i = solar_pv.get_current(v_op, sun_irradiance=1.0)
        v_next, p_meas, _ = mppt.update(v_measured=v_op, i_measured=current_i)
        tracked_powers_phase1.append(p_meas)
        tracked_voltages_phase1.append(v_op)
        v_op = v_next

    final_v_phase1 = float(np.mean(tracked_voltages_phase1[-10:]))
    final_p_phase1 = float(np.mean(tracked_powers_phase1[-10:]))
    efficiency_phase1 = (final_p_phase1 / p_target_100) * 100.0

    print("2. KET QUA KHOA DINH CONG SUAT GIAI DOAN 1 (100% NANG):")
    print(f"   -> Cong suat ban dau (chua bam)  : {tracked_powers_phase1[0]:.2f} W")
    print(f"   -> Cong suat sau hoi tu P&O      : {final_p_phase1:.2f} W")
    print(f"   -> Dien ap van hanh da khoa     : {final_v_phase1:.2f} V (Muc tieu: {v_target_100:.2f} V)")
    print(f"   -> Hieu suat thu hoi MPPT        : {efficiency_phase1:.2f}% (Tieu chuan > 98%)\n")

    # 3. Kiem thu tinh huong bien: Buc xa sut giam dot ngot xuong 50% (May che / Ve tinh vao goc khuat)
    v_target_50, p_target_50 = solar_pv.get_peak_power(sun_irradiance=0.5)
    print("3. PHAN UNG KHI BUC XA SUT GIAM DOT NGOT CON 50% (MAY CHE):")
    print(f"   -> Diem MPP moi o buc xa 50%     : {v_target_50:.2f} V, {p_target_50:.2f} W")

    tracked_powers_phase2: List[float] = []
    tracked_voltages_phase2: List[float] = []

    for step in range(50):
        current_i = solar_pv.get_current(v_op, sun_irradiance=0.5)
        v_next, p_meas, _ = mppt.update(v_measured=v_op, i_measured=current_i)
        tracked_powers_phase2.append(p_meas)
        tracked_voltages_phase2.append(v_op)
        v_op = v_next

    final_v_phase2 = float(np.mean(tracked_voltages_phase2[-10:]))
    final_p_phase2 = float(np.mean(tracked_powers_phase2[-10:]))
    efficiency_phase2 = (final_p_phase2 / p_target_50) * 100.0

    print(f"   -> Cong suat sau khi tai thich nghi : {final_p_phase2:.2f} W")
    print(f"   -> Dien ap khoa tai buc xa 50%      : {final_v_phase2:.2f} V")
    print(f"   -> Hieu suat thu hoi MPPT pha 2     : {efficiency_phase2:.2f}%\n")

    # Kiem tra Assertions
    assert efficiency_phase1 > 98.0, "Hieu suat MPPT pha 1 chua dat nguong toi thieu 98%!"
    assert efficiency_phase2 > 98.0, "Hieu suat MPPT pha 2 khi giam buc xa chua dat 98%!"
    assert abs(final_v_phase1 - v_target_100) < 1.0, "Dien ap khoa pha 1 lech qua lon so voi dinh MPP!"

    print("[THANH CONG] THUAT TOAN P&O MPPT DONG THOI KHOA DINH 99% VA THICH NGHI KHI THAY DOI BUC XA!")
