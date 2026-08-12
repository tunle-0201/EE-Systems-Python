"""
================================================================================
          MODULE D: DEEP LEARNING & NEURAL NETWORKS (PYTORCH)
              MILESTONE D.2: MẠNG NƠ-RON MULTI-LAYER FORWARD PASS
================================================================================

BƯỚC 1: TRANG BỊ HỘP CÔNG CỤ FORWARD PASS (TOOLBOX MASTERY)

Mạng Nơ-ron 2 Lớp (2-Layer Feedforward Neural Network):
1. Lớp Ẩn (Hidden Layer):
   - Z1 = np.dot(X, W1) + b1
   - Kích hoạt ReLU: H = np.maximum(0, Z1)
2. Lớp Đầu Ra (Output Layer):
   - Z2 = np.dot(H, W2) + b2
   - Kích hoạt Sigmoid: output = 1.0 / (1.0 + np.exp(-Z2))

BÀI TOÁN THỰC TẾ:
Cho Ma trận 2 mẫu bay Drone X (shape 2x3: Pitch, Roll, Alt).
Cho W1 (shape 3x4), b1 (shape 1x4), W2 (shape 4x1), b2 (shape 1x1).

Nhiệm vụ của Kỹ sư trưởng trong hàm `forward_pass_neural_net(X, W1, b1, W2, b2)`:
1. Tính Z1 = np.dot(X, W1) + b1
2. Tính H = np.maximum(0, Z1)
3. Tính Z2 = np.dot(H, W2) + b2
4. Tính output = 1.0 / (1.0 + np.exp(-Z2))
5. Trả về: output
"""

import numpy as np

def forward_pass_neural_net(X, W1, b1, W2, b2):
    """
    Trò đóng vai Kỹ sư trưởng tự chọn công cụ Forward Pass từ Hộp Công Cụ để lập trình hàm này từ con số 0:
    - Tính Z1 = np.dot(X, W1) + b1
    - Kích hoạt ReLU: H = np.maximum(0, Z1)
    - Tính Z2 = np.dot(H, W2) + b2
    - Kích hoạt Sigmoid: output = 1.0 / (1.0 + np.exp(-Z2))
    - Trả về: output
    """
    Z1 = np.dot(X, W1) + b1
    H = np.maximum(0, Z1)
    Z2 = np.dot(H, W2) + b2
    output = 1.0 / (1.0 + np.exp(-Z2))
    return output


if __name__ == "__main__":
    print("=========================================================")
    print("   DEEP LEARNING: 2-LAYER NEURAL NETWORK FORWARD PASS")
    print("=========================================================\n")
    
    np.random.seed(42)
    X_input = np.array([[12.0, -5.0, 100.0], [45.0, 30.0, 5.0]]) # 2 chuyến bay
    
    W1 = np.random.randn(3, 4)
    b1 = np.zeros((1, 4))
    W2 = np.random.randn(4, 1)
    b2 = np.zeros((1, 1))
    
    predictions = forward_pass_neural_net(X_input, W1, b1, W2, b2)
    
    if predictions is not None:
        print(f"1. KẾT QUẢ FORWARD PASS CỦA MẠNG NƠ-RON 2 LỚP:")
        print(f"   -> Kích thước ma trận Dự đoán (Shape) : {predictions.shape}")
        print(f"   -> Xác suất Dự đoán Mẫu 1 (An toàn)  : {predictions[0, 0]*100:.1f}%")
        print(f"   -> Xác suất Dự đoán Mẫu 2 (Nguy hiểm): {predictions[1, 0]*100:.1f}%")
        
        # Kiểm tra tính chính xác
        assert predictions.shape == (2, 1), "Lỗi kích thước ma trận đầu ra!"
        assert 0.0 <= predictions[0, 0] <= 1.0, "Lỗi giá trị Sigmoid!"
        
        print("\n[THÀNH CÔNG] TRÒ ĐÃ TỰ TAY THIẾT KẾ DÒNG CHẢY DỮ LIỆU FORWARD PASS CHO MẠNG NƠ-RON!")
