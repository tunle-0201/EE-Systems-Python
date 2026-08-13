"""
================================================================================
          MODULE D: DEEP LEARNING & NEURAL NETWORKS (PYTORCH)
              MILESTONE D.7: THUẬT TOÁN HỌC MINI-BATCH GRADIENT DESCENT
================================================================================

BƯỚC 1: TRANG BỊ HỘP CÔNG CỤ MINI-BATCH (TOOLBOX MASTERY)

Tại sao Kỹ sư AI không nạp toàn bộ 1,000,000 bức ảnh vào RAM cùng lúc?
- Nạp tất cả cùng lúc -> Cháy bộ nhớ RAM/GPU!
- Nạp từng bức ảnh một -> Quá chậm, không tận dụng được sức mạnh đa nhân GPU!

GIẢI PHÁP: Chia dữ liệu thành từng Lô nhỏ (Mini-Batches - Ví dụ 32 hoặc 64 mẫu):
1. Vòng lặp chia Lô: `for i in range(0, N, batch_size):`
2. Cắt Lô: `X_batch = X[i : i + batch_size]` và `y_batch = y[i : i + batch_size]`
3. Dự đoán Lô: `y_pred = np.dot(X_batch, W) + b`
4. Đạo hàm Lô: `dL_dW = (2 / B) * np.dot(X_batch.T, (y_pred - y_batch))`
5. Cập nhật Trọng số: `W = W - lr * dL_dW`

BÀI TOÁN THỰC TẾ:
Cho 100 mẫu cảm biến Drone (X shape 100x2, y shape 100x1).
Huấn luyện AI bằng thuật toán Mini-Batch với `batch_size = 20`.

Nhiệm vụ của Kỹ sư trưởng trong hàm `train_minibatch_gd(X, y, W, b, batch_size=20, lr=0.01)`:
1. Lấy số lượng mẫu N = len(X)
2. Vòng lặp i từ 0 đến N nhảy từng bước batch_size:
   - X_batch = X[i : i + batch_size]
   - y_batch = y[i : i + batch_size]
   - y_pred = np.dot(X_batch, W) + b
   - B = len(X_batch)
   - dL_dW = (2 / B) * np.dot(X_batch.T, (y_pred - y_batch))
   - dL_db = (2 / B) * np.sum(y_pred - y_batch)
   - W = W - lr * dL_dW
   - b = b - lr * dL_db
3. Trả về: W, b
"""

import numpy as np

def train_minibatch_gd(X, y, W, b, batch_size=20, lr=0.01):
    """
    Trò đóng vai Kỹ sư trưởng tự chọn công cụ Mini-Batch từ Hộp Công Cụ để lập trình hàm này từ con số 0:
    - N = len(X)
    - Lặp i qua range(0, N, batch_size):
      + Cắt X_batch, y_batch
      + Dự đoán y_pred = np.dot(X_batch, W) + b
      + B = len(X_batch)
      + dL_dW = (2 / B) * np.dot(X_batch.T, (y_pred - y_batch))
      + dL_db = (2 / B) * np.sum(y_pred - y_batch)
      + W = W - lr * dL_dW
      + b = b - lr * dL_db
    - Trả về: W, b
    """
    N = len(X)
    for i in range(0, N, batch_size):
        X_batch = X[i : i + batch_size]
        y_batch = y[i : i + batch_size]
        y_pred = np.dot(X_batch, W) + b
        B = len(X_batch)
        dL_dW = (2 / B) * np.dot(X_batch.T, (y_pred - y_batch))
        dL_db = (2 / B) * np.sum(y_pred - y_batch)
        W = W - lr * dL_dW
        b = b - lr * dL_db
    return W, b


if __name__ == "__main__":
    print("=========================================================")
    print("   DEEP LEARNING: MINI-BATCH GRADIENT DESCENT OPTIMIZER")
    print("=========================================================\n")
    
    np.random.seed(42)
    N_samples = 100
    X_data = np.random.randn(N_samples, 2)
    # Đáp án thực tế: y = 3.0*X1 - 2.0*X2 + 1.5
    W_true = np.array([[3.0], [-2.0]])
    b_true = 1.5
    y_data = np.dot(X_data, W_true) + b_true
    
    # Khởi tạo trọng số ban đầu bằng 0
    W_init = np.zeros((2, 1))
    b_init = 0.0
    
    # Huấn luyện 50 vòng lặp Mini-Batch
    W_curr, b_curr = W_init.copy(), b_init
    for epoch in range(50):
        W_curr, b_curr = train_minibatch_gd(X_data, y_data, W_curr, b_curr, batch_size=20, lr=0.05)
    
    if W_curr is not None:
        print(f"1. KẾT QUẢ HUẤN LUYỆN BẰNG THUẬT TOÁN MINI-BATCH GRADIENT DESCENT:")
        print(f"   -> Trọng số W1 học được : {W_curr[0, 0]:.2f} (Sát mốc chuẩn 3.00!)")
        print(f"   -> Trọng số W2 học được : {W_curr[1, 0]:.2f} (Sát mốc chuẩn -2.00!)")
        print(f"   -> Bias b học được      : {b_curr:.2f} (Sát mốc chuẩn 1.50!)")
        
        # Kiểm tra tính chính xác
        assert abs(W_curr[0, 0] - 3.0) < 0.2 and abs(W_curr[1, 0] - (-2.0)) < 0.2, "Lỗi huấn luyện Mini-Batch!"
        
        print("\n[THÀNH CÔNG] TRÒ ĐÃ LÀM CHỦ KỸ THUẬT HUẤN LUYỆN CỦA CÁC SIÊU MÁY CHỦ AI KHI XỬ LÝ DỮ LIỆU LỚN!")
