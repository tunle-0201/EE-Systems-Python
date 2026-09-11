"""
================================================================================
          MODULE AE: SATELLITE ATTITUDE DETERMINATION & CONTROL (ADCS)
              MILESTONE AE.1: THUẬT TOÁN HÃM QUAY B-DOT (MAGNETORQUER DETUMBLING)
================================================================================

TẠI SAO MỌI VỆ TINH CUBESAT SAU KHI PHÓNG ĐỀU CẦN THUẬT TOÁN B-DOT?
Khi vệ tinh vừa tách khỏi tên lửa đẩy:
- Vệ tinh bị xoay lộn nhào dữ dội trong không gian (Tumbler Rate > 50 deg/s).
- Không thể mở pin mặt trời hay bắt sóng liên lạc với mặt đất!
- Thuật toán **B-Dot Law**:
  + Đo đạo hàm biến thiên từ trường Trái Đất theo thời gian: dB / dt = (B_now - B_prev) / dt
  + Kích hoạt cuộn dây từ trường Magnetorquer sinh mô-men từ M ngược hướng:
    M = -k * (dB / dt)
  + Hãm triệt tiêu 100% vận tốc xoay, đưa vệ tinh về trạng thái tĩnh ổn định!
"""

import numpy as np

def compute_bdot_magnetic_dipole(B_curr: np.ndarray, B_prev: np.ndarray, dt: float, k_gain: float = 1000.0) -> np.ndarray:
    """
    Trò đóng vai Kỹ sư Điều khiển Tư thế Vệ tinh:
    - B_curr, B_prev: Vector từ trường Trái Đất 3 trục (Tesla)
    - dB_dt = (B_curr - B_prev) / dt
    - Vector mô-men từ kích hoạt: M = -k_gain * dB_dt
    - Kẹp giới hạn dòng điện cuộn dây [-0.2, +0.2] A.m^2
    """
    dB_dt = (B_curr - B_prev) / dt
    M = -k_gain * dB_dt
    return np.clip(M, -0.2, 0.2)


if __name__ == "__main__":
    print("=========================================================")
    print("   SATELLITE ADCS: B-DOT MAGNETORQUER DETUMBLING")
    print("=========================================================\n")

    # Từ trường đo bởi Magnetometer: B_prev = [20uT, 0uT, -30uT], sau 0.1s B_curr = [25uT, -2uT, -28uT]
    B_t0 = np.array([20e-6, 0.0, -30e-6], dtype=np.float32)
    B_t1 = np.array([25e-6, -2e-6, -28e-6], dtype=np.float32)
    dt_step = 0.1

    dipole_M = compute_bdot_magnetic_dipole(B_t1, B_t0, dt=dt_step, k_gain=2000.0)

    print("1. KET QUA KICH HOAT CUON DAY MAGNETORQUER HAM QUAY:")
    print(f"   -> Do bien thien dB/dt (uT/s): {(B_t1 - B_t0) / dt_step * 1e6}")
    print(f"   -> Mo-men tu sinh ra M (A.m2) : {dipole_M}")

    # dB_x/dt > 0 nên M_x phải mang dấu âm để hãm quay
    assert dipole_M[0] < 0 and dipole_M[1] > 0, "Loi B-Dot Detumbling!"
    print("\n[THANH CONG] DA HOAN THANH THUAT TOAN HAM QUAY B-DOT CUU NGUY VE TINH TRUOC GIO LUA!")
