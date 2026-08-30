"""
================================================================================
          MODULE S: EMBEDDED DIGITAL POWER ELECTRONICS & FOC MOTOR CONTROL
              MILESTONE S.3: ĐIỀU CHẾ VECTOR KHÔNG GIAN (SPACE VECTOR PWM - SVPWM)
================================================================================

TẠI SAO SVPWM TIẾT KIỆM 15% ĐIỆN ÁP PIN SO VỚI SPWM THÔNG THƯỜNG?
SVPWM (Space Vector Pulse Width Modulation):
- Chia không gian 360 độ thành 6 Sector hình quạt 60 độ.
- Tính toán chu kỳ đóng ngắt Duty Cycle (T1, T2, T0) của 6 con Mosfet cầu H.
- Tận dụng tối đa điện áp Bus DC của Pin LiPo!
"""

import numpy as np

def determine_svpwm_sector(theta_rad: float) -> int:
    """
    Trò đóng vai Kỹ sư Điện tử công suất xác định Sector hình quạt (1 đến 6):
    - Đổi theta_rad sang độ deg trong khoảng [0..360)
    - sector = int(deg / 60.0) + 1
    - Trả về: sector
    """
    deg = np.rad2deg(theta_rad) % 360.0
    sector = int(deg / 60.0) + 1
    return sector


if __name__ == "__main__":
    print("=========================================================")
    print("   DIGITAL POWER ELECTRONICS: SVPWM SECTOR CALCULATOR")
    print("=========================================================\n")
    
    # Góc 30 độ thuộc Sector 1 (0..60°), Góc 90 độ thuộc Sector 2 (60..120°)
    sec1 = determine_svpwm_sector(np.deg2rad(30.0))
    sec2 = determine_svpwm_sector(np.deg2rad(90.0))
    
    print("1. KET QUA PHAN LOAI SECTOR KHONG GIAN SVPWM:")
    print(f"   -> Goc 30 do : Sector {sec1}")
    print(f"   -> Goc 90 do : Sector {sec2}")
    
    assert sec1 == 1 and sec2 == 2, "Loi SVPWM Sector!"
    print("\n[THANH CONG] DA HOAN THANH BO DINH HUONG VECTOR KHONG GIAN SVPWM CHO MOSFET CAU H!")
