"""
================================================================================
          MODULE S: EMBEDDED DIGITAL POWER ELECTRONICS & FOC MOTOR CONTROL
    MILESTONE S.3: DIEU CHE VECTOR KHONG GIAN (SPACE VECTOR PWM - SVPWM)
================================================================================

1. NGUYEN LY VAT LY & CAU H INVERTER (POWER ELECTRONICS & SVPWM FOUNDATION):
   - Bo nghich luu 3 pha (3-Phase Inverter Bridge) co 6 van Mosfet / IGBT:
     + 3 van nhanh tren (Upper: Sa, Sb, Sc).
     + 3 van nhanh duoi (Lower: luon dao pha voi van tren).
   - Co tong cong 2^3 = 8 trang thai dong ngat:
     + 6 vector dien ap hoat dong (Active Vectors: V1 den V6) tao thanh hinh luc giac deu.
     + 2 vector dien ap khong (Zero Vectors: V0=000 va V7=111) nam tai tam toa do.
   - Tai sao tat ca cac he thong xe dien va Drone deu dung SVPWM thay vi SPWM sin truyen thong?
     + SPWM thong thuong chi tan dung duoc: V_max = 0.5 * V_dc.
     + SVPWM dieu che vector tan dung duoc: V_max = V_dc / sqrt(3) = 0.577 * V_dc.
     + TANG THEM 15.5% DIEN AP CUA PIN LIPO / PACK PIN XE DIEN!
     + Giup dong co dat toc do cao hon va giam thieu ton hao dong ngat nhiet Mosfet.

2. SO DO KHONG GIAN & HOP CONG CU TOAN HOC (ASCII MATH BLOCKS):

   So do hinh luc giac 6 Sector cua Space Vector PWM (SVPWM Hexagon):

                    Beta
                     ▲
               V3(010)│   V2(110)
                \     │     /
                 \    │    /
                  \ S2│S1 /
            S3     \  │  /
   V4(011)───────────┼───────────► V1(100) Alpha
            S4     / │ \
                  /  │  \     S6
                 / S5│   \
                /    │    \
               V5(001)│   V6(101)
                     ▼

   Phan chia 6 Sector goc quay hinh quat (60 do moi Sector):
   Sector 1 :   0 do  den  60 do  (Giua V1 va V2)
   Sector 2 :  60 do  den 120 do  (Giua V2 va V3)
   Sector 3 : 120 do  den 180 do  (Giua V3 va V4)
   Sector 4 : 180 do  den 240 do  (Giua V4 va V5)
   Sector 5 : 240 do  den 300 do  (Giua V5 va V6)
   Sector 6 : 300 do  den 360 do  (Giua V6 va V1)

   Cong thuc xac dinh Sector theo goc dien theta (do):

   Sector = int( (theta_deg mod 360) / 60 ) + 1
"""

from typing import Tuple, Dict
import numpy as np


class SpaceVectorPWM:
    """
    Bo tao xung dieu che Vector khong gian SVPWM cho cau H 3 pha.
    """
    def __init__(self, v_bus: float = 24.0, pwm_period_us: float = 50.0):
        self.v_bus = float(v_bus)              # Dien ap nguon DC Bus Pin (V)
        self.pwm_period_us = float(pwm_period_us)  # Chu ky PWM (us) - vi du 20 kHz = 50us

    def get_sector(self, theta_rad: float) -> int:
        """
        Xac dinh Sector hinh quat (1 den 6) dua vao goc vector dien ap theta (rad):
        Sector = int((deg % 360) / 60) + 1
        """
        deg = float(np.rad2deg(theta_rad)) % 360.0
        sector = int(deg / 60.0) + 1
        if sector > 6:
            sector = 6
        return sector

    def compute_duty_cycles(self, v_ref: float, theta_rad: float) -> Dict[str, float]:
        """
        Tinh thoi gian dong ngat T1, T2, T0 trong mot chu ky PWM:
        - T1: Thoi gian kich vector co so 1
        - T2: Thoi gian kich vector co so 2
        - T0: Thoi gian vector 0 (nghi)
        """
        sector = self.get_sector(theta_rad)
        deg = float(np.rad2deg(theta_rad)) % 360.0
        angle_in_sector = np.deg2rad(deg - (sector - 1) * 60.0)

        # He so dieu che ma tran
        m = (np.sqrt(3.0) * v_ref) / self.v_bus
        t1 = self.pwm_period_us * m * np.sin(np.pi / 3.0 - angle_in_sector)
        t2 = self.pwm_period_us * m * np.sin(angle_in_sector)
        t0 = max(0.0, self.pwm_period_us - t1 - t2)

        return {
            "sector": sector,
            "T1_us": float(t1),
            "T2_us": float(t2),
            "T0_us": float(t0),
            "duty_percent": float(((t1 + t2) / self.pwm_period_us) * 100.0)
        }


def determine_svpwm_sector(theta_rad: float) -> int:
    """
    Ham backward-compatible giu nguyen signature cua Milestone S.3.
    """
    svpwm = SpaceVectorPWM()
    return svpwm.get_sector(theta_rad)


if __name__ == "__main__":
    print("=========================================================")
    print("   DIGITAL POWER ELECTRONICS: SVPWM SECTOR CALCULATOR")
    print("=========================================================\n")

    svpwm = SpaceVectorPWM(v_bus=24.0, pwm_period_us=50.0)

    # Goc 30 do thuoc Sector 1 (0..60 deg), Goc 90 do thuoc Sector 2 (60..120 deg)
    sec1 = svpwm.get_sector(np.deg2rad(30.0))
    sec2 = svpwm.get_sector(np.deg2rad(90.0))

    print("1. KET QUA PHAN LOAI SECTOR KHONG GIAN SVPWM:")
    print(f"   -> Goc 30 do : Sector {sec1} (0..60 deg)")
    print(f"   -> Goc 90 do : Sector {sec2} (60..120 deg)")

    assert sec1 == 1 and sec2 == 2, "Loi SVPWM Sector!"

    # 2. Thu nghiem tinh thoi gian dong ngat Duty Cycle Mosfet tai 30 do
    # V_ref = 10V tren nguon Pin V_bus = 24V
    pwm_timing = svpwm.compute_duty_cycles(v_ref=10.0, theta_rad=np.deg2rad(30.0))
    print("\n2. THOI GIAN DONG NGAT MOSFET TAI GOC 30 DO (CHU KY 50us):")
    print(f"   -> Thoi gian Vector T1 : {pwm_timing['T1_us']:.2f} us")
    print(f"   -> Thoi gian Vector T2 : {pwm_timing['T2_us']:.2f} us")
    print(f"   -> Thoi gian Nghi   T0 : {pwm_timing['T0_us']:.2f} us")
    print(f"   -> Tong Duty Cycle     : {pwm_timing['duty_percent']:.1f} %")

    assert pwm_timing['sector'] == 1
    assert abs(pwm_timing['T1_us'] - pwm_timing['T2_us']) < 1e-3  # Tai 30 do nam giua Sector, T1 = T2!

    print("\n[THANH CONG] DA HOAN THANH BO DINH HUONG VECTOR KHONG GIAN SVPWM CHO MOSFET CAU H!")
