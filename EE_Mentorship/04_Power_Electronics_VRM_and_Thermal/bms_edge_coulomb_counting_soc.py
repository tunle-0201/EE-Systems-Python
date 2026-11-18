"""
================================================================================
          MODULE V: EMBEDDED BATTERY MANAGEMENT SYSTEMS (BMS)
              MILESTONE V.1: COULOMB COUNTING & OCV RECALIBRATION
================================================================================

VAI TRO THIET YEU CUA THUAT TOAN TINH DUNG LUONG PIN (SOC) TREN XE DIEN TESLA / DRONE:
Pin Lithium-ion (NMC / LFP / 4680) la trai tim nang luong cua xe dien va thiet bi bay:
- State of Charge (SOC %): Ty le dung luong con lai (tuong duong kim xang so).
- Phuong phap Dem Coulomb (Coulomb Counting):
  Tich phan dong dien do qua dien tro Shunt ADC theo thoi gian thuc:

                                      1
             SOC[t] = SOC[0] + ─────────────── * integral( I(t) * dt )
                                Q_nominal_As

  (Quy uoc ky thuat: I > 0 la dong nap vao pin, I < 0 la dong xa cap cho dong co,
   Q_nominal_As = Dung luong danh dinh tinh bang Ampe-giay).

HIEN TUONG TROI SAI SO TRUC TIEP TREN PHAN CUNG NHUNG (ZERO-DRIFT OFFSET):
- Cảm bien ADC hoac khuech dai do dong Shunt (INA240 / LTC2944) luon ton tai sai lech
  dien ap lech diem khong (Offset Voltage Drift tu 0.5% den 2%).
- Khi tich phan lien tuc nhieu gio, sai so nay tich luy khien dong ho bao pin lech
  tu 5% den 15%, dan den hien tuong chet may dot ngot du dong ho van bao con pin!

GIAI PHAP HYBRID BMS: TAI HIEU CHUAN BANG DIEN AP HO MACH (OCV RECALIBRATION):
Khi xe dung do hoac may bay tat dong co (|I| < 0.05A trong thoi gian du dai):
- Dien ap cuc pin hoi phuc ve trang thai can bang hoa hoc OCV (Open-Circuit Voltage).
- BMS tra bang OCV-SOC Look-Up Table de "Reset" triet tieu toan bo sai so tich phan!

SO DO NGUYEN LY THUAT TOAN COULOMB COUNTING VA OCV RESET (ASCII BLOCK):

   [ Shunt Resistor ] ---> [ ADC Current Sense ] ---> [ Coulomb Integrator ]
                                                             |
                                                             v
                                                      Raw Drifted SOC
                                                             |
   [ OCV Voltage ADC ] ---> [ Rest Detector ] ------------> [ Recalibration Engine ]
                            (|I| < 0.05A, > 10m)             |
                                                             v
                                                      True Calibrated SOC
"""

from typing import Tuple, List, Dict, Any, Optional
import numpy as np


class CoulombCountingBMS:
    """
    Bo uoc luong dung luong pin State of Charge (SOC) ket hop hai phuong phap:
    1. Coulomb Counting lien tuc toc do cao (Fast Real-time Current Integration).
    2. OCV Recalibration tai thoi diem nghi (Rest-State OCV Reset) chong troi sai so.
    """
    def __init__(self, nominal_capacity_ah: float = 5.0, initial_soc: float = 1.0):
        """
        - nominal_capacity_ah: Dung luong danh dinh cell pin (5.0 Ah chuan cell 21700 Tesla)
        - initial_soc: Muc pin ban dau (1.0 = 100%)
        """
        self.nominal_capacity_ah = nominal_capacity_ah
        self.q_nominal_as = nominal_capacity_ah * 3600.0  # Chuyen sang Coulombs (A*s)
        self.soc = float(initial_soc)
        self.rest_timer_sec = 0.0

        # Bang tra cuu thuc nghiem OCV - SOC cua cell Li-ion NMC (Dien ap V -> SOC ti le)
        self.ocv_table_v = [3.00, 3.30, 3.50, 3.65, 3.75, 3.85, 3.95, 4.05, 4.15, 4.20]
        self.soc_table   = [0.00, 0.05, 0.15, 0.30, 0.50, 0.65, 0.80, 0.90, 0.98, 1.00]

    def update_coulomb_count(self, current_amps: float, dt_sec: float) -> float:
        """
        Tich phan dong dien theo chu ky thoi gian roi rac:
        current_amps: Dong dien do qua dien tro Shunt (A), Duong (+) = Nap, Am (-) = Xa
        dt_sec: Chu ky lay mau ADC (giay)
        """
        coulombs = current_amps * dt_sec
        delta_soc = coulombs / self.q_nominal_as
        self.soc += delta_soc
        self.soc = max(0.0, min(1.0, self.soc))
        return float(self.soc)

    def ocv_lookup(self, measured_v: float) -> float:
        """
        Tra cuu SOC tu dien ap ho mach OCV bang noi suy tuyen tinh tung doan
        """
        if measured_v <= self.ocv_table_v[0]:
            return float(self.soc_table[0])
        if measured_v >= self.ocv_table_v[-1]:
            return float(self.soc_table[-1])

        for i in range(len(self.ocv_table_v) - 1):
            v0, v1 = self.ocv_table_v[i], self.ocv_table_v[i + 1]
            if v0 <= measured_v <= v1:
                s0, s1 = self.soc_table[i], self.soc_table[i + 1]
                slope = (s1 - s0) / (v1 - v0)
                return float(s0 + slope * (measured_v - v0))
        return float(self.soc)

    def check_and_recalibrate(
        self,
        measured_voltage: float,
        current_amps: float,
        dt_sec: float,
        rest_threshold_sec: float = 600.0
    ) -> bool:
        """
        Kiem tra trang thai nghi de tai hieu chuan OCV:
        Neu dong dien gan nhu bang 0 (|I| < 0.05A) trong it nhat rest_threshold_sec:
        -> Cap nhat lai SOC tu bang OCV, triet tieu hoan toan sai so troi ADC!
        """
        if abs(current_amps) < 0.05:
            self.rest_timer_sec += dt_sec
            if self.rest_timer_sec >= rest_threshold_sec:
                corrected_soc = self.ocv_lookup(measured_voltage)
                self.soc = corrected_soc
                self.rest_timer_sec = 0.0
                return True
        else:
            self.rest_timer_sec = 0.0
        return False


if __name__ == "__main__":
    print("=========================================================")
    print("   EMBEDDED BMS: COULOMB COUNTING & OCV RECALIBRATION")
    print("=========================================================\n")

    bms = CoulombCountingBMS(nominal_capacity_ah=5.0, initial_soc=1.0)

    # 1. Kich ban xa pin dong co: Dong xa 2.5A (0.5C) trong 1 gio (3600 giay)
    # Gia lap cam bien ADC co nhieu troi lech nhe +0.1A lam tich phan bi sai
    print("1. QUA TRINH XA PIN VA HIEN TUONG TROI SAI SO (DRIFT):")
    actual_i = -2.5       # Dong xa thuc te 2.5A
    sensor_drift = 0.1    # Offset troi dong khien cam bien do thanh -2.4A
    measured_i = actual_i + sensor_drift

    for step in range(3600):
        bms.update_coulomb_count(current_amps=measured_i, dt_sec=1.0)

    # Sau 1 gio xa 2.5A tu cell 5.0Ah: Dung luong mat thuc te = 2.5Ah / 5.0Ah = 50%
    # Do cam bien bi troi +0.1A nen BMS do -2.4A va bao sai thanh 52.0%
    drift_soc = bms.soc
    print(f"   -> SOC tinh boi Coulomb Counting (bi troi) : {drift_soc * 100:.2f}%")
    print(f"   -> SOC thuc te cua cell pin                : 50.00% (Sai lech {abs(drift_soc - 0.50) * 100:.2f}%)\n")

    # 2. Kich ban xe dung do nghi ngoi: Dong = 0A, Dien ap hoi phuc ve OCV = 3.75V (50% SOC)
    print("2. QUA TRINH DUNG DO NGHI NGOI VA TAI HIEU CHUAN OCV (RESET DRIFT):")
    v_cell_rest = 3.75  # 3.75V tuong ung muc pin 50% theo bang chuan NMC
    recalibrated = False

    # Xe do nghi trong 15 phut (900 giay)
    for step in range(900):
        if bms.check_and_recalibrate(measured_voltage=v_cell_rest, current_amps=0.0, dt_sec=1.0, rest_threshold_sec=600.0):
            recalibrated = True
            break

    print(f"   -> Trang thai kich hoat tai hieu chuan    : {'THANH CONG' if recalibrated else 'CHUA DU THOI GIAN'}")
    print(f"   -> SOC sau khi duoc hieu chinh bang OCV   : {bms.soc * 100:.2f}% (Da reset chuan xac ve 50.0%)")

    # Kiem tra Assertions
    assert recalibrated is True, "Qua trinh tai hieu chuan OCV phai kich hoat thanh cong sau 10 phut nghi!"
    assert abs(bms.soc - 0.50) < 1e-4, "SOC sau khi reset bang OCV phai khop dung 50.0%!"

    print("\n[THANH CONG] THUAT TOAN COULOMB COUNTING VA OCV RESET TRIET TIEU 100% SAI SO TROI ADC!")
