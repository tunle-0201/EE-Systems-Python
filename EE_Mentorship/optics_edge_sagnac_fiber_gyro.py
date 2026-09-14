"""
================================================================================
          MODULE AH: EMBEDDED OPTICAL TRANSCEIVERS & PHOTONICS AVIONICS
              MILESTONE AH.2: CON QUAY QUANG SỢI SAGNAC (FIBER OPTIC GYROSCOPE)
================================================================================

TẠI SAO TÀU NGẦM HẠT NHÂN VÀ TÊN LỬA ĐẠN ĐẠO DÙNG FOG (FIBER OPTIC GYRO)?
Cảm biến IMU MEMS cơ học bị trôi (Drift) rất nhanh, không thể dẫn đường chính xác nhiều ngày:
- Con quay quang sợi FOG (Fiber Optic Gyroscope):
  + Sử dụng cuộn sợi quang dài hàng kilomet (L = 1000m) cuộn tròn bán kính R.
  + Bắn 2 chùm tia laser chạy ngược chiều nhau trong cuộn sợi (Clockwise & Counter-Clockwise).
- Hiệu ứng Sagnac: Khi tên lửa xoay với tốc độ góc Omega (rad/s):
  + Hai chùm tia đi quãng đường khác nhau sinh ra độ lệch pha quang học (Phase Shift delta_phi):
    delta_phi = (8 * pi * Area * N_turns * Omega) / (c * lambda)
  + Độ chính xác cực cao, độ trôi gần như bằng 0 (Navigation-Grade < 0.001 deg/hour)!
"""

import numpy as np

def compute_sagnac_phase_shift(omega_rad_s: float, fiber_length_m: float = 1000.0, coil_radius_m: float = 0.05, wavelength_nm: float = 1550.0):
    """
    Trò đóng vai Kỹ sư Dẫn đường Quang học Hàng không:
    - c_speed: Vận tốc ánh sáng = 3e8 m/s
    - Bước sóng: wl = wavelength_nm * 1e-9
    - Diện tích vòng cuộn: A = pi * R^2
    - Số vòng cuộn: N = fiber_length_m / (2 * pi * R)
    - Độ lệch pha Sagnac: delta_phi = (4 * pi * R * fiber_length_m * omega_rad_s) / (c_speed * wl)
    - Cường độ ánh sáng giao thoa: I = I_0 * (1 + cos(delta_phi))
    """
    c_speed = 3e8
    wl = wavelength_nm * 1e-9
    
    # delta_phi = (4 * pi * R * L * omega) / (c * lambda)
    delta_phi = (4.0 * np.pi * coil_radius_m * fiber_length_m * omega_rad_s) / (c_speed * wl)
    interference_intensity = 0.5 * (1.0 + np.cos(delta_phi))
    return float(delta_phi), float(interference_intensity)


if __name__ == "__main__":
    print("=========================================================")
    print("   PHOTONICS AVIONICS: FIBER OPTIC GYROSCOPE (FOG)")
    print("=========================================================\n")

    # Tên lửa đang quay với tốc độ góc 0.1 rad/s (~5.7 deg/s)
    # Cuộn sợi quang dài 1km (1000m), bán kính 5cm (0.05m), bước sóng laser viễn thông 1550nm
    phi_shift, intensity = compute_sagnac_phase_shift(omega_rad_s=0.1, fiber_length_m=1000.0, coil_radius_m=0.05)

    print("1. KET QUA HIEN TUONG GIAO THOA QUANG SAGNAC PHAN TICH GOC QUAY:")
    print(f"   -> Do lech pha quang Sagnac : {phi_shift:.6f} rad")
    print(f"   -> Cuong do anh sang giao thoa: {intensity:.6f}")

    assert phi_shift > 0.0 and 0.0 <= intensity <= 1.0, "Loi Fiber Optic Gyro!"
    print("\n[THANH CONG] DA HOAN THANH MO PHONG CON QUAY QUANG SOI FOG CHUAN DAN DUONG QUAN SU!")
