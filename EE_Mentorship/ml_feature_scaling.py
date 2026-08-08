"""
================================================================================
          MODULE B: MACHINE LEARNING & NUMPY MATRIX OPERATIONS
              MILESTONE B.4: CHUẨN HÓA DỮ LIỆU CẢM BIẾN (FEATURE SCALING)
================================================================================

Vấn đề trong thực tế:
Cảm biến Drone gửi về 2 chỉ số:
- Pin     : từ 0% đến 100% (Giá trị nhỏ)
- Độ cao  : từ 0m đến 5000m (Giá trị CỰC LỚN!)

Nếu quẳng trực tiếp dữ liệu thô này vào Mạng Nơ-ron AI (Neural Network):
AI sẽ bị "lóa mắt" bởi con số 5000m của Độ cao, và tưởng rằng Độ cao quan trọng
gấp 50 lần dung lượng Pin -> Khiến mô hình đoán sai hoàn toàn!

Giải pháp của AI Engineer: **StandardScaler (Z-score Normalization)**
Biến đổi tất cả các cột dữ liệu về cùng một thước đo chuẩn:
- Trung bình (Mean) = 0
- Độ lệch chuẩn (Std) = 1

Nhiệm vụ của trò:
1. Khởi tạo `scaler = StandardScaler()`.
2. Dùng `scaler.fit_transform(X_raw)` để biến đổi ma trận X thô thành X_scaled.
3. In ra trung bình và độ lệch chuẩn mới của X_scaled để kiểm tra!
"""

import numpy as np
from sklearn.preprocessing import StandardScaler

# Ma trận dữ liệu thô Cảm biến Drone (3 mẫu x 2 thuộc tính: [Pin (%), Độ cao (m)])
X_raw = np.array([
    [10.0,  500.0],
    [55.0, 2500.0],
    [90.0, 4800.0]
])

def scale_sensor_features(raw_data):
    """
    Trò tự gõ code thực tế (KHÔNG GỢI Ý CÚ PHÁP):
    1. Khởi tạo scaler = StandardScaler()
    2. Biến đổi raw_data bằng scaler.fit_transform(raw_data)
    3. Trả về: scaled_data, scaler
    """
    scaler = StandardScaler()
    scaled_data = scaler.fit_transform(raw_data)
    return scaled_data, scaler


if __name__ == "__main__":
    print("=========================================================")
    print("   AI ENGINE: FEATURE SCALING & Z-SCORE NORMALIZATION")
    print("=========================================================\n")
    
    print(f"1. Dữ liệu thô ban đầu (Raw Data):\n{X_raw}")
    
    scaled_X, scaler = scale_sensor_features(X_raw)
    
    if scaled_X is not None:
        print(f"\n2. Dữ liệu sau khi Chuẩn hóa StandardScaler (Z-Score):\n{scaled_X}")
        print(f"   -> Giá trị Trung bình mới (Mean) : {scaled_X.mean(axis=0)} (Gần sát 0!)")
        print(f"   -> Độ lệch chuẩn mới (Std Dev)  : {scaled_X.std(axis=0)} (Đúng bằng 1!)")
        
        print("\n[THÀNH CÔNG] TRÒ ĐÃ LÀM CHỦ KỸ THUẬT CHUẨN HÓA DỮ LIỆU CHO AI!")
