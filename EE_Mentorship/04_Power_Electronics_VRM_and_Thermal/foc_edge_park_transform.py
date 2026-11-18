"""
================================================================================
          MODULE S: EMBEDDED DIGITAL POWER ELECTRONICS & FOC MOTOR CONTROL
    MILESTONE S.2: BIEN DOI PARK SANG HE TOA DO ROTOR (D-Q ROTOR FRAME)
================================================================================

1. NGUYEN LY VAT LY & DIEN TU CONG SUAT (FIELD-ORIENTED CONTROL FOUNDATION):
   - Sau khi bien doi Clarke, ta co 2 dong I_alpha va I_beta vuong goc nhau.
     Tuy nhien, 2 dong dien nay van la dong XOAY CHIEU (AC) dao dong voi tan so
     cao theo toc do quay cua dong co.
   - Bo dieu khien PID thong thuong luon bi tre pha (Phase Lag) va sai so xac lap
     khi phai bam theo tin hieu sin xoay chieu tan so hang tram Hertz.
   - Phep bien doi Park Transform (Bien doi sang he toa do quay d-q):
     + Gan he truc toa do xoay truc tiep len nam cham vinh cuu cua Rotor!
     + Truc d (Direct Axis): Nam trung theo chieu tu thong nam cham Rotor.
       Dong I_d la dong tu hoa sinh tu truong (O che do thuong, ta dat I_d_ref = 0 de tiet kiem pin).
     + Truc q (Quadrature Axis): Vuong goc 90 do dien so voi truc d.
       Dong I_q la dong vuong goc TRUC TIEP SINH MO-MEN XOAN (Torque)!
     + Mo-men dong co = 1.5 * P * Psi * I_q (Tuyen tinh tuyet doi voi I_q)!
     + Bien bai toan dieu khien dong co 3 pha phuc tap thanh dieu khien dong 1 chieu DC!

2. SO DO KHONG GIAN & HOP CONG CU TOAN HOC (ASCII MATH BLOCKS):

   So do hinh hoc phep bien doi Park Transform tu he tinh sang he truc quay:

               Beta                       q (Truc tao Mo-men Torque)
                ▲                        ▲
                │                       /
                │      d (Truc tu hoa) /
                │       ▲             /
                │      /             /
                │     / theta       /
                │    /             /
   ─────────────┼───/─────────────/──────► Alpha
                │

   Cong thuc bien doi thuan Park (Forward Park Transform):

   I_d =  I_alpha * cos(theta) + I_beta * sin(theta)
   I_q = -I_alpha * sin(theta) + I_beta * cos(theta)

   Cong thuc bien doi nguoc Park (Inverse Park Transform):
   Ap dung cho dien ap dieu khien (V_d, V_q) tu bo PID tro lai he truc tinh:

   V_alpha = V_d * cos(theta) - V_q * sin(theta)
   V_beta  = V_d * sin(theta) + V_q * cos(theta)
"""

from typing import Tuple
import numpy as np


class ParkTransform:
    """
    Bo bien doi he toa do Park thuan va nghich cho he thong dieu khien tua tu thong FOC.
    """
    def __init__(self):
        pass

    def forward(self, i_alpha: float, i_beta: float, theta_rad: float) -> Tuple[float, float]:
        """
        Bien doi Park thuan: (I_alpha, I_beta, theta) -> (I_d, I_q)
        """
        cos_th = np.cos(theta_rad)
        sin_th = np.sin(theta_rad)

        i_d = float(i_alpha * cos_th + i_beta * sin_th)
        i_q = float(-i_alpha * sin_th + i_beta * cos_th)
        return i_d, i_q

    def inverse(self, v_d: float, v_q: float, theta_rad: float) -> Tuple[float, float]:
        """
        Bien doi Park nguoc: (V_d, V_q, theta) -> (V_alpha, V_beta)
        """
        cos_th = np.cos(theta_rad)
        sin_th = np.sin(theta_rad)

        v_alpha = float(v_d * cos_th - v_q * sin_th)
        v_beta = float(v_d * sin_th + v_q * cos_th)
        return v_alpha, v_beta


def compute_park_transform(i_alpha: float, i_beta: float, theta_rad: float) -> Tuple[float, float]:
    """
    Ham backward-compatible giu nguyen signature cua Milestone S.2.
    """
    engine = ParkTransform()
    return engine.forward(i_alpha, i_beta, theta_rad)


if __name__ == "__main__":
    print("=========================================================")
    print("   DIGITAL POWER ELECTRONICS: ROTOR PARK TRANSFORM")
    print("=========================================================\n")

    # Rotor dang o goc 0 rad, I_alpha = 10A, I_beta = 0A
    park = ParkTransform()
    i_d_val, i_q_val = park.forward(i_alpha=10.0, i_beta=0.0, theta_rad=0.0)

    print("1. KET QUA BIEN DOI PARK SANG HE TRUC D-Q ROTOR:")
    print(f"   -> Goc Rotor theta dien     : 0.00 rad")
    print(f"   -> Dong Tu hoa I_d (Flux)   : {i_d_val:.2f} A")
    print(f"   -> Dong Mo-men I_q (Torque) : {i_q_val:.2f} A")

    assert abs(i_d_val - 10.0) < 1e-5 and abs(i_q_val - 0.0) < 1e-5, "Loi Park Transform!"

    # 2. Thu nghiem khi Rotor xoay 90 do dien (pi/2 rad)
    # Toan bo dong I_alpha = 10A se chuyen thang thanh dong tao mo-men am I_q = -10A
    i_d_90, i_q_90 = park.forward(i_alpha=10.0, i_beta=0.0, theta_rad=np.pi / 2.0)
    print("\n2. KHI ROTOR XOAY 90 DO DIEN (theta = pi/2 rad):")
    print(f"   -> Dong I_d : {i_d_90:.2f} A")
    print(f"   -> Dong I_q : {i_q_90:.2f} A (Chuyen toan bo sang truc mo-men!)")

    assert abs(i_d_90 - 0.0) < 1e-5 and abs(i_q_90 - (-10.0)) < 1e-5

    # 3. Kiem tra bien doi nguoc Inverse Park Transform
    v_alpha, v_beta = park.inverse(v_d=i_d_val, v_q=i_q_val, theta_rad=0.0)
    print("\n3. KIEM TRA BIEN DOI NGUOC (INVERSE PARK TRANSFORM):")
    print(f"   -> Phuc hoi V_alpha : {v_alpha:.2f} V")
    print(f"   -> Phuc hoi V_beta  : {v_beta:.2f} V")

    assert abs(v_alpha - 10.0) < 1e-5 and abs(v_beta - 0.0) < 1e-5

    print("\n[THANH CONG] DA HOAN THANH BIEN DOI PARK CHO PHEP DIEU KHIEN MO-MEN DONG CO NHU DONG DIEN MOT CHIEU!")
