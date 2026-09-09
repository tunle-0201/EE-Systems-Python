"""
================================================================================
          MODULE AC CAPSTONE FINALE: BỘ BÁM BẮT RADAR ĐA MỤC TIÊU CHO XE/DRONE
================================================================================

TÍCH HỢP TOÀN BỘ RADAR TRACKING PIPELINE: KALMAN PREDICT + MAHALANOBIS + DATA ASSOCIATION
"""

from track_edge_kalman_state_predictor import predict_kalman_state
from track_edge_mahalanobis_gating import compute_mahalanobis_gating
from track_edge_hungarian_associator import assign_tracks_to_detections
import numpy as np

def run_multi_target_radar_tracking_engine():
    # 1. Khởi tạo 1 Track đang bay
    x_state = np.array([10.0, 10.0, 2.0, 1.0], dtype=np.float32)
    P_cov = np.eye(4, dtype=np.float32)

    # 2. Tiên đoán vị trí tại chu kỳ quét tiếp theo (dt = 1.0s)
    x_pred, P_pred = predict_kalman_state(x_state, P_cov, dt=1.0)
    pred_pos = (float(x_pred[0]), float(x_pred[1]))

    # 3. Điểm đo mới gửi về: 1 điểm thật (12.1, 11.0) và 1 điểm nhiễu giả (99.0, 99.0)
    meas_real = np.array([12.1, 11.0], dtype=np.float32)
    meas_noise = np.array([99.0, 99.0], dtype=np.float32)

    # 4. Lọc cửa sổ không gian Mahalanobis loại bỏ điểm nhiễu
    S = np.eye(2, dtype=np.float32) * 2.0
    is_real_valid = compute_mahalanobis_gating(meas_real, x_pred[:2], S)
    is_noise_valid = compute_mahalanobis_gating(meas_noise, x_pred[:2], S)

    # 5. Ghép cặp điểm đo hợp lệ với Track
    valid_dets = [tuple(meas_real)] if is_real_valid else []
    matches = assign_tracks_to_detections([pred_pos], valid_dets)

    return pred_pos, is_noise_valid, matches


if __name__ == "__main__":
    print("=========================================================")
    print("   MODULE AC CAPSTONE: REAL-TIME RADAR TRACKER ENGINE")
    print("=========================================================\n")

    pos, noise_ok, pairs = run_multi_target_radar_tracking_engine()

    print("1. KET QUA HOAT DONG TOAN CHUOI RADAR MULTI-TARGET TRACKER:")
    print(f"   -> Vi tri tien doan Kalman (x, y) : {pos}")
    print(f"   -> Phat hien loc bo nhieu gia     : Noise Valid = {noise_ok} (Loai bo thanh cong!)")
    print(f"   -> Cap ghep quy dao va diem do    : {pairs}")

    assert abs(pos[0] - 12.0) < 1e-3 and noise_ok == False and len(pairs) == 1, "Loi Capstone Radar Tracker!"
    print("\n=========================================================")
    print("CHUC MUNG TRO DA TOT NGHIEP TOAN BO MODULE AC: RADAR MULTI-TARGET TRACKING!")
    print("=========================================================")
