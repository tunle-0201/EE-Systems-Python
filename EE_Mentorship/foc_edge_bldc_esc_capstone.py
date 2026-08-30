"""
================================================================================
          MODULE S CAPSTONE FINALE: BỘ ĐIỀU TỐC ĐỘNG CƠ FOC BLDC MOTOR ESC
================================================================================

TÍCH HỢP TOÀN BỘ FOC PIPELINE: CLARKE TRANSFORM + PARK TRANSFORM + SVPWM SECTOR
"""

from foc_edge_clarke_transform import compute_clarke_transform
from foc_edge_park_transform import compute_park_transform
from foc_edge_svpwm_generator import determine_svpwm_sector
import numpy as np

def run_foc_motor_controller_loop(ia, ib, ic, rotor_angle_rad):
    # 1. Clarke Transform (3 pha -> Alpha-Beta)
    i_alpha, i_beta = compute_clarke_transform(ia, ib, ic)
    
    # 2. Park Transform (Alpha-Beta -> d-q)
    i_d, i_q = compute_park_transform(i_alpha, i_beta, rotor_angle_rad)
    
    # 3. Tính Sector điều chế SVPWM
    sec = determine_svpwm_sector(rotor_angle_rad)
    
    return i_d, i_q, sec


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE S CAPSTONE: REAL-TIME FOC MOTOR ESC ENGINE")
    print("=========================================================\n")
    
    Ia, Ib, Ic = 10.0, -5.0, -5.0
    theta = np.deg2rad(45.0)
    
    id_out, iq_out, sector = run_foc_motor_controller_loop(Ia, Ib, Ic, theta)
    
    print("1. KET QUA HOAT DONG TOAN CHUOI FOC MOTOR ESC:")
    print(f"   -> Dong Tu hoa I_d     : {id_out:.2f} A")
    print(f"   -> Dong Mo-men I_q     : {iq_out:.2f} A")
    print(f"   -> Sector Dieu che PWM : Sector {sector}")
    
    assert abs(id_out - 7.071) < 1e-2 and abs(iq_out - (-7.071)) < 1e-2 and sector == 1, "Loi Capstone FOC!"
    print("\n=========================================================")
    print("CHUC MUNG TRO DA TOT NGHIEP TOAN BO KHOA HOC MODULE S: FOC MOTOR CONTROL!")
    print("=========================================================")
