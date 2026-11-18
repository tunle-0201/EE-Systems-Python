"""
================================================================================
          MODULE AC: MULTI-TARGET KALMAN TRACKING & RADAR FUSION
              MILESTONE AC.1: BƯỚC TIÊN ĐOÁN TRẠNG THÁI KALMAN (STATE PREDICTOR)
================================================================================

TẠI SAO BỘ LỌC KALMAN LÀ LINH HỒN CỦA HỆ THỐNG RADAR BÁM BẮT MỤC TIÊU?
Một vật thể bay (Drone/Tên lửa) có vector trạng thái:
  x = [vị_trí_x, vị_trí_y, vận_tốc_vx, vận_tốc_vy]^T
- Phương trình chuyển động vận tốc không đổi (Constant Velocity):
  x_mới = F * x_cũ
- Ma trận chuyển trạng thái F (với dt là chu kỳ quét cảm biến):
  F = [[1, 0, dt,  0],
       [0, 1,  0, dt],
       [0, 0,  1,  0],
       [0, 0,  0,  1]]
- Cập nhật ma trận hiệp phương sai sai số: P_pred = F * P * F^T + Q
"""

import numpy as np

def predict_kalman_state(x_state: np.ndarray, P_cov: np.ndarray, dt: float, q_noise: float = 0.1):
    """
    Trò đóng vai Kỹ sư Xử lý Radar Phòng không:
    - Xây dựng ma trận F bậc 4x4
    - x_pred = F @ x_state
    - Q = np.eye(4) * q_noise
    - P_pred = F @ P_cov @ F.T + Q
    - Trả về: (x_pred, P_pred)
    """
    F = np.array([
        [1.0, 0.0,  dt, 0.0],
        [0.0, 1.0, 0.0,  dt],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0]
    ], dtype=np.float32)

    Q = np.eye(4, dtype=np.float32) * q_noise
    x_pred = F @ x_state
    P_pred = F @ P_cov @ F.T + Q
    return x_pred, P_pred


if __name__ == "__main__":
    print("=========================================================")
    print("   RADAR TRACKING: KALMAN FILTER KINEMATIC PREDICTOR")
    print("=========================================================\n")

    # Drone ban đầu ở tọa độ (100m, 50m), bay với vận tốc (20m/s, 10m/s)
    x_init = np.array([100.0, 50.0, 20.0, 10.0], dtype=np.float32)
    P_init = np.eye(4, dtype=np.float32) * 1.0
    dt_scan = 0.5  # Chu kỳ quét 500ms

    x_next, P_next = predict_kalman_state(x_init, P_init, dt=dt_scan)

    print("1. KET QUA TIEN DOAN VI TRI DRONE SAU 0.5 GIAY:")
    print(f"   -> Vi tri X du doan  : {x_next[0]:.1f} m (100 + 20*0.5 = 110.0m)")
    print(f"   -> Vi tri Y du doan  : {x_next[1]:.1f} m (50 + 10*0.5 = 55.0m)")
    print(f"   -> Do bat dinh Cov P : Trace = {np.trace(P_next):.2f}")

    assert abs(x_next[0] - 110.0) < 1e-3 and abs(x_next[1] - 55.0) < 1e-3, "Loi Kalman Predictor!"
    print("\n[THANH CONG] DA HOAN THANH BUOC TIEN DOAN KALMAN 4D CONSTANT VELOCITY CHO RADAR!")
