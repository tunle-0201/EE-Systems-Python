"""
================================================================================
          MODULE S: EMBEDDED DIGITAL POWER ELECTRONICS & FOC MOTOR CONTROL
              MILESTONE S.2: BIẾN ĐỔI PARK SANG HỆ TỌA ĐỘ ROTOR (PARK TRANSFORM)
================================================================================

TẠI SAO CẦN BIẾN ĐỔI PARK (D-Q ROTOR FRAME)?
Dòng điện xoay chiều biến thiên liên tục theo góc quay của rotor:
- Phép biến đổi **Park Transform** xoay hệ trục Alpha-Beta theo góc từ trường rotor theta:
  + I_d (Direct Current): Thành phần dòng từ hóa sinh từ thông (mong muốn = 0).
  + I_q (Quadrature Current): Thành phần dòng điện vuông góc TRỰC TIẾP SINH MÔ-MEN XOẮN (Torque)!
- Biến dòng điện xoay chiều phức tạp thành số một chiều (DC) cực kỳ dễ điều khiển PID!
"""

import numpy as np

def compute_park_transform(i_alpha: float, i_beta: float, theta_rad: float):
    """
    Trò đóng vai Kỹ sư FOC điều khiển động cơ:
    - i_d =  i_alpha * np.cos(theta_rad) + i_beta * np.sin(theta_rad)
    - i_q = -i_alpha * np.sin(theta_rad) + i_beta * np.cos(theta_rad)
    - Trả về: (i_d, i_q)
    """
    i_d = i_alpha * np.cos(theta_rad) + i_beta * np.sin(theta_rad)
    i_q = -i_alpha * np.sin(theta_rad) + i_beta * np.cos(theta_rad)
    return i_d, i_q


if __name__ == "__main__":
    print("=========================================================")
    print("   DIGITAL POWER ELECTRONICS: ROTOR PARK TRANSFORM")
    print("=========================================================\n")
    
    # Rotor đang ở góc 0 rad, I_alpha = 10A, I_beta = 0A
    i_d_val, i_q_val = compute_park_transform(i_alpha=10.0, i_beta=0.0, theta_rad=0.0)
    
    print("1. KET QUA BIEN DOI PARK SANG HE TRUC D-Q ROTOR:")
    print(f"   -> Dong Tu hoa I_d (Flux)   : {i_d_val:.2f} A")
    print(f"   -> Dong Mo-men I_q (Torque) : {i_q_val:.2f} A")
    
    assert abs(i_d_val - 10.0) < 1e-5 and abs(i_q_val - 0.0) < 1e-5, "Loi Park Transform!"
    print("\n[THANH CONG] DA HOAN THANH BIEN DOI PARK CHO PHEP DIEU KHIEN MO-MEN DONG CO NHU DONG DIEN MOT CHIEU!")
