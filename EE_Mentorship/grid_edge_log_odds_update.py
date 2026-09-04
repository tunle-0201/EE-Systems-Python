"""
================================================================================
          MODULE X: HARDWARE-ACCELERATED OCCUPANCY GRID & RAY-TRACING
              MILESTONE X.2: CẬP NHẬT XÁC SUẤT BẢN ĐỒ (LOG-ODDS BAYES FILTER)
================================================================================

TẠI SAO PHẢI DÙNG LOG-ODDS THAY VÌ XÁC SUẤT % THÔNG THƯỜNG TRONG ROBOTICS?
Xác suất p(m) nằm trong khoảng [0.0..1.0]:
- Nhân xác suất liên tục nhiều lần sẽ dẫn đến tràn số dưới (Floating-point Underflow).
- Thang đo **Log-Odds**: l = log(p / (1 - p))
  + Ô rỗng (Free): Cộng thêm giá trị âm (l_free = -0.4).
  + Ô có vật cản (Occupied): Cộng thêm giá trị dương (l_occ = +0.85).
  + Phép nhân xác suất Bayes phức tạp biến thành **PHÉP CỘNG ĐẠI SỐ ĐƠN GIẢN (ADDITION)**!
"""

import numpy as np

def update_cell_log_odds(current_log_odds: float, is_occupied_observation: bool, l_occ=0.85, l_free=-0.4):
    """
    Trò đóng vai Kỹ sư Lập bản đồ SLAM:
    - Nếu phát hiện ô có vật cản: new_l = current_log_odds + l_occ
    - Nếu ô là vùng trống: new_l = current_log_odds + l_free
    - Kẹp giá trị (Clamp) trong dải an toàn [-5.0, +5.0] tránh bão hòa
    """
    delta = l_occ if is_occupied_observation else l_free
    new_l = current_log_odds + delta
    return np.clip(new_l, -5.0, 5.0)

def log_odds_to_probability(l: float) -> float:
    """Đổi từ thang Log-Odds về xác suất p = 1 / (1 + exp(-l))."""
    return 1.0 / (1.0 + np.exp(-l))


if __name__ == "__main__":
    print("=========================================================")
    print("   OCCUPANCY MAPPING: LOG-ODDS BAYES FILTER UPDATE")
    print("=========================================================\n")

    # Ô ban đầu chưa rõ (p = 0.5 -> log_odds = 0.0)
    l_val = 0.0
    
    # 3 lần LiDAR quét trúng cùng một điểm này
    for _ in range(3):
        l_val = update_cell_log_odds(l_val, is_occupied_observation=True)

    prob = log_odds_to_probability(l_val)

    print("1. KET QUA CAP NHAT XAC SUAT O LUOI SAU 3 LAN QUET TRUNG:")
    print(f"   -> Gia tri Log-Odds tich luy : {l_val:.2f}")
    print(f"   -> Xac suat chac chan Co vat : {prob * 100:.1f}%")

    assert prob > 0.9 and l_val == 0.85 * 3, "Loi Log-Odds Update!"
    print("\n[THANH CONG] DA HOAN THANH BO CAP NHAT BAN DO XAC SUAT LOG-ODDS CHO ROBOT!")
