"""
================================================================================
          MODULE P: ADVANCED ROBOTICS KINEMATICS & TRAJECTORY PLANNING
              MILESTONE P.3: ĐỘNG HỌC THUẬN TAY ROBOT 2 KHỚP (2-LINK FORWARD KINEMATICS)
================================================================================

TẠI SAO CẦN ĐỘNG HỌC THUẬN (FORWARD KINEMATICS) TRONG ROBOTICS?
Từ góc xoay của 2 khớp nối động cơ (theta1, theta2) và chiều dài 2 cánh tay (L1, L2):
- Tính toán tọa độ đầu cuối End-Effector (x, y) trong không gian:
  x = L1 * cos(theta1) + L2 * cos(theta1 + theta2)
  y = L1 * sin(theta1) + L2 * sin(theta1 + theta2)
"""

import numpy as np

def compute_2link_forward_kinematics(L1: float, L2: float, theta1_rad: float, theta2_rad: float):
    """
    Trò đóng vai Kỹ sư Động học Robot:
    - x = L1 * np.cos(theta1_rad) + L2 * np.cos(theta1_rad + theta2_rad)
    - y = L1 * np.sin(theta1_rad) + L2 * np.sin(theta1_rad + theta2_rad)
    - Trả về: (x, y)
    """
    x = L1 * np.cos(theta1_rad) + L2 * np.cos(theta1_rad + theta2_rad)
    y = L1 * np.sin(theta1_rad) + L2 * np.sin(theta1_rad + theta2_rad)
    return x, y


if __name__ == "__main__":
    print("=========================================================")
    print("   ROBOTICS EE: 2-LINK FORWARD KINEMATICS ENGINE")
    print("=========================================================\n")
    
    # Tay robot có 2 cánh tay dài 1.0m (L1=1.0, L2=1.0)
    # Khớp 1 xoay 0 rad (duỗi thẳng), Khớp 2 gập 90 độ (pi/2 rad)
    # -> x = 1.0*cos(0) + 1.0*cos(pi/2) = 1.0 + 0.0 = 1.0
    # -> y = 1.0*sin(0) + 1.0*sin(pi/2) = 0.0 + 1.0 = 1.0
    x_end, y_end = compute_2link_forward_kinematics(L1=1.0, L2=1.0, theta1_rad=0.0, theta2_rad=np.pi/2)
    
    print("1. KET QUA TOA DO DAU TAY ROBOT END-EFFECTOR:")
    print(f"   -> Toa do X : {x_end:.2f} m")
    print(f"   -> Toa do Y : {y_end:.2f} m")
    
    assert abs(x_end - 1.0) < 1e-5 and abs(y_end - 1.0) < 1e-5, "Loi Dong hoc thuan!"
    print("\n[THANH CONG] DA HOAN THANH TINH TOAN DONG HOC THUAN FORWARD KINEMATICS CHO ROBOT!")
