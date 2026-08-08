"""
================================================================================
          MODULE B: MACHINE LEARNING & NUMPY MATRIX OPERATIONS
              MILESTONE B.2: SLICING MA TRẬN & TÁCH FEATURE / LABEL
================================================================================

Trong Machine Learning, dữ liệu luôn được phân làm 2 phần:
1. Tập Thuộc Tính - Features (Ký hiệu X): Các con số đầu vào cho AI học.
2. Tập Nhãn Target - Labels (Ký hiệu y): Kết quả mong muốn AI dự đoán.

Ví dụ Ma trận Dữ liệu Drone Telemetry (4 mẫu bay):
 Cột 0: Temp (°C)  |  Cột 1: Roll (gốc)  |  Cột 2: Label (0 = An toàn, 1 = Cảnh báo)
─────────────────────────────────────────────────────────────────────────────
    25.0                 2.0                        0
    52.0                45.0                        1  (Gió mạnh lật nghiêng)
    24.5                 1.5                        0
    12.0                90.0                        1  (Lật nguy hiểm)

Cú pháp Slicing NumPy: `matrix[hàng, cột]`
- `:` nghĩa là "Lấy tất cả các hàng"
- `0:2` nghĩa là "Lấy từ cột 0 tới trước cột 2" (tức cột 0 và cột 1)
- `2` nghĩa là "Chỉ lấy duy nhất cột 2"

Nhiệm vụ của trò:
1. Hoàn thành TODO 1: Cắt lấy tập Features X (Cột 0 và Cột 1).
2. Hoàn thành TODO 2: Cắt lấy tập Label y (Cột 2).
"""

import numpy as np

# Ma trận dữ liệu 4x3
telemetry_dataset = np.array([
    [25.0,  2.0, 0],
    [52.0, 45.0, 1],
    [24.5,  1.5, 0],
    [12.0, 90.0, 1]
])

def split_features_and_labels(data):
    """
    TODO 1: Cắt lấy X (Features) gồm tất cả các hàng và 2 cột đầu (Cột 0 & 1).
    Cú pháp gợi ý: X = data[:, 0:2]
    TODO 2: Cắt lấy y (Labels) gồm tất cả các hàng và cột cuối cùng (Cột 2).
    Cú pháp gợi ý: y = data[:, 2]
    Trả về: X, y
    """
    # Gõ code của trò vào đây:
    X = data[:, 0:2]
    y = data[:, 2]
    return X, y


if __name__ == "__main__":
    print("=== MACHINE LEARNING B.2: SLICING MA TRẬN X & Y ===")
    
    X, y = split_features_and_labels(telemetry_dataset)
    
    print("\n1. Tập Đầu Vào - Features (X):")
    print(X)
    print(f"   -> Kích thước X (Shape): {X.shape} (4 hàng, 2 thuộc tính)")
    
    print("\n2. Tập Nhãn Kết Quả - Labels (y):")
    print(y)
    print(f"   -> Kích thước y (Shape): {y.shape} (4 nhãn target)")
    
    # Lọc tự động (Boolean Masking) của AI: Tìm tất cả các mẫu bị Cảnh báo (y == 1)
    danger_samples = X[y == 1]
    print(f"\n3. Các mẫu Drone bị cảnh báo lật nghiêng (y == 1) được AI lọc tự động:\n{danger_samples}")
    
    print("\n[THÀNH CÔNG] TRÒ ĐÃ THÀNH THẠO KỸ THUẬT TÁCH DATA CHO AI!")
