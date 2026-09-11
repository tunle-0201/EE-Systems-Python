"""
================================================================================
          MODULE AE: SATELLITE ATTITUDE DETERMINATION & CONTROL (ADCS)
              MILESTONE AE.3: THẢO ĐÀ BÁNH ĐÀ PHẢN LỰC (REACTION WHEEL DESATURATION)
================================================================================

TẠI SAO BÁNH ĐÀ PHẢN LỰC (REACTION WHEELS) BỊ BÃO HÒA (SATURATION)?
Bánh đà quay ở tốc độ cực cao (5000 - 8000 RPM) để xoay chỉnh góc chụp ảnh:
- Nhiễu trường ngoài (Áp suất photon mặt trời, trọng trường) liên tục tích tụ động lượng.
- Khi bánh đà quay đạt kịch trần tốc độ tối đa (Max RPM) -> Bị bão hòa, mất khả năng điều khiển!
- Thuật toán **Desaturation (Magnetic Dumping)**:
  + Dùng cuộn dây Magnetorquer tương tác với từ trường Trái Đất B tạo ra mô-men ngoài:
    Tau_ext = M x B
  + Làm chậm bánh đà về lại dải tốc độ danh định an toàn (RPM = 0)!
"""

import numpy as np

def compute_magnetic_desaturation_torque(wheel_momentum_h: np.ndarray, B_field: np.ndarray, k_dump: float = 0.05):
    """
    Trò đóng vai Kỹ sư Xả Động lượng Bánh đà:
    - Mô-men cần triệt tiêu: Tau_desat = -k_dump * wheel_momentum_h
    - Mô-men từ cần sinh ra: M = (B x Tau_desat) / ||B||^2
    - Mô-men ngoại lực thực tế tác dụng lên vệ tinh: Tau_ext = np.cross(M, B_field)
    - Trả về: (M, Tau_ext)
    """
    tau_desat = -k_dump * wheel_momentum_h
    B_norm_sq = float(np.dot(B_field, B_field))
    
    M = np.cross(B_field, tau_desat) / B_norm_sq
    tau_ext = np.cross(M, B_field)
    return M, tau_ext


if __name__ == "__main__":
    print("=========================================================")
    print("   SATELLITE ADCS: REACTION WHEEL DESATURATION")
    print("=========================================================\n")

    # Bánh đà đang bị tích tụ động lượng cao theo trục Z: H = [0, 0, 0.5] N.m.s
    H_wheel = np.array([0.0, 0.0, 0.5], dtype=np.float32)
    B_earth = np.array([0.0, 30e-6, 0.0], dtype=np.float32) # Từ trường theo trục Y

    dipole_M, applied_tau = compute_magnetic_desaturation_torque(H_wheel, B_earth, k_dump=0.1)

    print("1. KET QUA DIEU KHIEN XA MO-MEN DONG LUONG BANH DA:")
    print(f"   -> Dong luong banh da H (Nms)  : {H_wheel}")
    print(f"   -> Mo-men tu Magnetorquer M     : {dipole_M}")
    print(f"   -> Mo-men ngoai luc ha toc do   : {applied_tau}")

    # Mô-men hãm theo trục Z phải ngược chiều với động lượng bánh đà (Tau_z < 0)
    assert applied_tau[2] < 0, "Loi Wheel Desaturation!"
    print("\n[THANH CONG] DA HOAN THANH CO CHE XA DONG LUONG BANH DA CHONG BAO HOA CHO VE TINH!")
