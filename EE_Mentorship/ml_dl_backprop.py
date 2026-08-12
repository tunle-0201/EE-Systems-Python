"""
================================================================================
          MODULE D: DEEP LEARNING & NEURAL NETWORKS (PYTORCH)
              MILESTONE D.3: BACKPROPAGATION & GRADIENT DESCENT
================================================================================

BƯỚC 1: TRANG BỊ HỘP CÔNG CỤ BACKPROPAGATION (TOOLBOX MASTERY)

Quy trình 1 Bước học (Training Step) của AI:
1. Dự đoán y_pred = X * W
2. Tính Loss = (y_pred - y) ** 2
3. Tính Đạo hàm dL_dW = 2 * (y_pred - y) * X
4. Cập nhật W_new = W - lr * dL_dW

BÀI TOÁN THỰC TẾ:
Tín hiệu cảm biến X = 2.0, Đáp án thực tế y = 10.0.
Trọng số ban đầu W = 1.0 (Dự đoán y_pred = 2.0 -> Sai lệch rất to!).
Learning rate lr = 0.01.

Nhiệm vụ của Kỹ sư trưởng trong hàm `train_single_step_gradient_descent(X, y, W, lr)`:
1. Tính y_pred = X * W
2. Tính loss = (y_pred - y) ** 2
3. Tính dL_dW = 2 * (y_pred - y) * X
4. Tính W_new = W - lr * dL_dW
5. Trả về: W_new, loss
"""

import numpy as np

def train_single_step_gradient_descent(X, y, W, lr=0.01):
    """
    Trò đóng vai Kỹ sư trưởng tự chọn công cụ Backprop từ Hộp Công Cụ để lập trình hàm này từ con số 0:
    - Tính y_pred = X * W
    - Tính loss = (y_pred - y) ** 2
    - Tính dL_dW = 2 * (y_pred - y) * X
    - Tính W_new = W - lr * dL_dW
    - Trả về: W_new, loss
    """
    y_pred = X * W
    loss = (y_pred - y) ** 2
    dL_dW = 2 * (y_pred - y) * X
    W_new = W - lr * dL_dW
    return W_new, loss
    


if __name__ == "__main__":
    print("=========================================================")
    print("   DEEP LEARNING: BACKPROPAGATION & GRADIENT DESCENT")
    print("=========================================================\n")
    
    X_val = 2.0
    y_true = 10.0
    W_current = 1.0
    learning_rate = 0.01
    
    print(f"Ban đầu: W = {W_current:.2f}, Dự đoán y_pred = {X_val * W_current:.2f} (Đáp án đúng là 10.0)")
    
    W_new, loss = train_single_step_gradient_descent(X_val, y_true, W_current, learning_rate)
    
    if W_new is not None:
        print(f"\n1. KẾT QUẢ CẬP NHẬT TRỌNG SỐ SAU 1 BƯỚC HỌC (BACKPROP):")
        print(f"   -> Sai số Loss                     : {loss:.2f}")
        print(f"   -> Trọng số W mới (W_new)          : {W_new:.2f} (Đã tăng từ 1.00 lên sát hơn!)")
        print(f"   -> Dự đoán mới sau khi học         : {X_val * W_new:.2f}")
        
        # Kiểm tra tính chính xác (Trọng số W phải tăng lên để kéo 2.0 lên sát 10.0)
        assert W_new > W_current, "Lỗi thuật toán Gradient Descent!"
        
        print("\n[THÀNH CÔNG] THUẬT TOÁN HỌC BACKPROPAGATION ĐÃ CẬP NHẬT TRỌNG SỐ AI TỰ ĐỘNG!")
