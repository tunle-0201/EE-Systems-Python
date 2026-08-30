"""
================================================================================
          MODULE S: EMBEDDED DIGITAL POWER ELECTRONICS & FOC MOTOR CONTROL
              MILESTONE S.1: BIẾN ĐỔI CLARKE DÒNG ĐIỆN 3 PHA (CLARKE TRANSFORM)
================================================================================

TẠI SAO CÁC XE TESLA VÀ DRONE HIỆN ĐẠI DÙNG FIELD-ORIENTED CONTROL (FOC)?
Động cơ không chổi than 3 pha (BLDC/PMSM) có 3 dòng xoay chiều Ia, Ib, Ic:
- Rất khó điều khiển trực tiếp trên không gian 3 pha 120 độ.
- Phép biến đổi **Clarke Transform** chuyển 3 dòng điện 3 pha sang hệ tọa độ tĩnh 2 trục 90 độ (I_alpha, I_beta):
  + I_alpha = Ia
  + I_beta  = (Ia + 2*Ib) / sqrt(3)
"""

import numpy as np

def compute_clarke_transform(ia: float, ib: float, ic: float):
    """
    Trò đóng vai Kỹ sư Điện tử công suất thiết kế biến đổi Clarke:
    - Giả thiết hệ cân bằng: Ia + Ib + Ic = 0
    - i_alpha = ia
    - i_beta = (ia + 2.0*ib) / np.sqrt(3.0)
    - Trả về: (i_alpha, i_beta)
    """
    i_alpha = ia
    i_beta = (ia + 2.0 * ib) / np.sqrt(3.0)
    return i_alpha, i_beta


if __name__ == "__main__":
    print("=========================================================")
    print("   DIGITAL POWER ELECTRONICS: 3-PHASE CLARKE TRANSFORM")
    print("=========================================================\n")
    
    # 3 pha dòng điện động cơ lệch nhau 120 độ: Ia = 10.0A, Ib = -5.0A, Ic = -5.0A
    Ia = 10.0
    Ib = -5.0
    Ic = -5.0
    
    i_a, i_b = compute_clarke_transform(Ia, Ib, Ic)
    
    print("1. KET QUA BIEN DOI DONG DIEN 3 PHA SANG HE TRUC ALPHA-BETA:")
    print(f"   -> Dong I_alpha : {i_a:.2f} A")
    print(f"   -> Dong I_beta  : {i_b:.2f} A")
    
    assert abs(i_a - 10.0) < 1e-5 and abs(i_b - 0.0) < 1e-5, "Loi Clarke Transform!"
    print("\n[THANH CONG] DA HOAN THANH BIEN DOI CLARKE DIEU KHIEN DONG CO BLDC CHO DRONE!")
