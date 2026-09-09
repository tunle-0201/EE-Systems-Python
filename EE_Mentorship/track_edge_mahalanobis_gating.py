"""
================================================================================
          MODULE AC: MULTI-TARGET KALMAN TRACKING & RADAR FUSION
              MILESTONE AC.2: CỬA SỔ PHÂN LOẠI KHOẢNG CÁCH MAHALANOBIS (SPATIAL GATING)
================================================================================

TẠI SAO PHẢI DÙNG KHOẢNG CÁCH MAHALANOBIS THAY VÌ EUCLIDEAN TRONG BÁM BẮT?
Khoảng cách Euclidean hình học: Chỉ đo cự ly hình học d = sqrt(dx^2 + dy^2).
- Không tính đến độ bất định (Covariance Ellipse) của cảm biến (ví dụ: radar đo góc kém hơn đo cự ly).
- Khoảng cách **Mahalanobis Distance**:
  d_M^2 = (z - z_pred)^T * S^(-1) * (z - z_pred)
  (với S là ma trận hiệp phương sai đổi mới Innovation Covariance)
- Thuật toán **Chi-Square Gating**:
  Nếu d_M^2 <= Threshold (ví dụ: 9.21 cho xác suất 99% 2D): Chấp nhận điểm đo!
  Nếu d_M^2 > Threshold: VỨT BỎ NGAY vì đây là NHIỄU GIẢ (Radar Clutter)!
"""

import numpy as np

def compute_mahalanobis_gating(measurement: np.ndarray, predicted_meas: np.ndarray, S_cov: np.ndarray, threshold: float = 9.21) -> bool:
    """
    Trò đóng vai Kỹ sư Lọc Nhiễu Radar:
    - Tính vector sai lệch innovation: diff = measurement - predicted_meas
    - Tính nghịch đảo S_inv = np.linalg.inv(S_cov)
    - Tính khoảng cách Mahalanobis bình phương: d_squared = diff.T @ S_inv @ diff
    - Trả về True nếu d_squared <= threshold (Điểm đo hợp lệ)
    - Trả về False nếu d_squared > threshold (Nhiễu giả)
    """
    diff = measurement - predicted_meas
    S_inv = np.linalg.inv(S_cov)
    d_sq = float(diff.T @ S_inv @ diff)
    return d_sq <= threshold


if __name__ == "__main__":
    print("=========================================================")
    print("   RADAR TRACKING: MAHALANOBIS CHI-SQUARE SPATIAL GATING")
    print("=========================================================\n")

    # Điểm dự đoán của quỹ đạo bay: (100.0, 50.0)
    z_pred = np.array([100.0, 50.0], dtype=np.float32)
    S_mat = np.array([[4.0, 0.0], [0.0, 4.0]], dtype=np.float32) # Độ bất định bán kính 2m

    # Điểm đo 1: (101.0, 50.5) -> Rất gần dự đoán
    meas_valid = np.array([101.0, 50.5], dtype=np.float32)
    # Điểm đo 2: (150.0, 90.0) -> Nhiễu đám mây / chim bay xa lắc
    meas_clutter = np.array([150.0, 90.0], dtype=np.float32)

    is_valid_1 = compute_mahalanobis_gating(meas_valid, z_pred, S_mat)
    is_valid_2 = compute_mahalanobis_gating(meas_clutter, z_pred, S_mat)

    print("1. KET QUA LOC NHIEU GIA RADAR BANG CUA SO MAHALANOBIS:")
    print(f"   -> Diem do 1 (Sat quy dao) : Hop le = {is_valid_1}")
    print(f"   -> Diem do 2 (Nhieu gia)   : Hop le = {is_valid_2} (Bi loai bo!)")

    assert is_valid_1 == True and is_valid_2 == False, "Loi Mahalanobis Gating!"
    print("\n[THANH CONG] DA HOAN THANH BO LOC NHIEU GIA KHONG GIAN MAHALANOBIS CHO RADAR!")
