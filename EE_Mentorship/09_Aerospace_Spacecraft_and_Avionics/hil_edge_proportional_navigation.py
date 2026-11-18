"""
================================================================================
          MODULE AG: HARDWARE-IN-THE-LOOP (HIL) & FLIGHT SIMULATION
              MILESTONE AG.3: ĐIỀU KHIỂN DẪN ĐƯỜNG DẪN BẮT (PROPORTIONAL NAVIGATION)
================================================================================

TẠI SAO LUẬT DẪN ĐƯỜNG PRO-NAV LÀ TIÊU CHUẨN SỐ 1 CỦA TÊN LỬA VÀ DRONE ĐÁNH CHẶN?
Thuật toán Proportional Navigation (PN / Pro-Nav):
- Mục tiêu: Bắn chặn một vật thể bay di động trong không gian.
- Đo tốc độ xoay của đường ngắm (Line-Of-Sight Rate - omega_LOS).
- Lệnh gia tốc dẫn đường (Acceleration Command a_cmd):
  a_cmd = N * V_closing * omega_LOS
  (N: Hệ số dẫn đường Navigation Ratio, thường chọn từ 3 đến 5; V_closing: Vận tốc tiếp cận).
- Triệt tiêu hoàn toàn góc lệch, ép Drone lao thẳng tới điểm hẹn va chạm đón đầu!
"""

import numpy as np

def compute_proportional_navigation_accel(r_rel: np.ndarray, v_rel: np.ndarray, N_gain: float = 3.0) -> np.ndarray:
    """
    Trò đóng vai Kỹ sư Dẫn đường Tên lửa Đánh chặn:
    - r_rel: Vector vị trí tương đối từ Drone tới mục tiêu [rx, ry]
    - v_rel: Vector vận tốc tương đối [vx, vy]
    - Khoảng cách: R = np.linalg.norm(r_rel)
    - Tốc độ xoay đường ngắm omega_LOS = (rx*vy - ry*vx) / R^2
    - Vận tốc tiếp cận: V_closing = -np.dot(r_rel, v_rel) / R
    - Gia tốc đánh chặn: a_cmd = N_gain * V_closing * omega_LOS (vuông góc với đường ngắm)
    """
    R = float(np.linalg.norm(r_rel))
    if R < 1.0:
        return np.array([0.0, 0.0], dtype=np.float32)

    # Tích có hướng 2D xác định tốc độ xoay đường ngắm
    omega_los = (r_rel[0] * v_rel[1] - r_rel[1] * v_rel[0]) / (R * R)
    v_closing = -float(np.dot(r_rel, v_rel)) / R

    a_mag = N_gain * v_closing * omega_los
    # Hướng gia tốc vuông góc với vector vị trí tương đối
    u_perp = np.array([-r_rel[1], r_rel[0]], dtype=np.float32) / R
    return a_mag * u_perp


if __name__ == "__main__":
    print("=========================================================")
    print("   AEROSPACE HIL: PROPORTIONAL NAVIGATION (PRO-NAV) LAW")
    print("=========================================================\n")

    # Mục tiêu cách Drone 1000m phía trước, 100m bên phải: r_rel = [1000, 100]
    # Mục tiêu đang bay tạt ngang sang phải với vận tốc tương đối: v_rel = [-200, 30]
    r = np.array([1000.0, 100.0], dtype=np.float32)
    v = np.array([-200.0, 30.0], dtype=np.float32)

    a_cmd = compute_proportional_navigation_accel(r, v, N_gain=4.0)

    print("1. KET QUA TINH TOAN GIA TOC DAN DUONG DON DAU PRO-NAV:")
    print(f"   -> Cu ly toi muc tieu      : {np.linalg.norm(r):.1f} m")
    print(f"   -> Vector gia toc danh chan: [{a_cmd[0]:.2f}, {a_cmd[1]:.2f}] m/s2")
    print(f"   -> Do lon gia toc be lai   : {np.linalg.norm(a_cmd):.2f} m/s2 (~{np.linalg.norm(a_cmd)/9.81:.1f}G)")

    assert np.linalg.norm(a_cmd) > 0.0, "Loi Pro-Nav Guidance!"
    print("\n[THANH CONG] DA HOAN THANH LUAT DAN DUONG DON DAU PRO-NAV CHO HE THONG DAN DUONG!")
